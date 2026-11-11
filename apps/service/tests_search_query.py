"""Catalog search: transliteration, word order / dashes, lookalike letters, synonyms, typos; the not-found log
and the "leave a request" endpoint. Run: env/Scripts/python.exe manage.py test apps.service.tests_search_query"""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.service import search_log
from apps.service.models import Brand, NotFoundSearch, Product, SearchRequest, SearchSynonym
from apps.service.search import fold, query_variants, search_products
from apps.service.tests import ApiTestCase, make_customer, make_item_category, make_product

FILTER = "/api/v1/product/filter/"
SUGGEST = "/api/v1/search/"
REQUESTS = "/api/v1/search/requests/"


def make_named(code, item_category, name_ru, name_uz=None, articul=None, brand=None):
    product = make_product(code, item_category, 1000)
    product.name_ru, product.name_uz, product.articul_code, product.brand = name_ru, name_uz, articul, brand
    product.save()
    return product


class SearchCatalogMixin:
    def setUp(self):
        cache.clear()
        _, category = make_item_category("Podshipniklar")
        self.skf = Brand.objects.create(name="SKF", name_ru="SKF", name_uz="SKF")
        self.bearing = make_named("B1", category, "Подшипник 6203-2RS", articul="6203-2RS", brand=self.skf)
        self.bearing_open = make_named("B2", category, "Подшипник 6203 открытый")
        self.other_bearing = make_named("B3", category, "Подшипник 6000-2Z")
        self.screw = make_named("S1", category, "Винт DIN 912 M6х20 оцинкованный")  # Latin M, Cyrillic х
        self.screw8 = make_named("S2", category, "Винт DIN 912 М8х30")  # Cyrillic М
        self.cable = make_named("K1", category, "Кабель ВВГ 3×2,5", name_uz="Kabel VVG 3×2,5")
        make_named("X1", category, "Перфоратор", name_uz="Perforator")


class SearchProductsTests(SearchCatalogMixin, TestCase):
    def found(self, q):
        products = search_products(Product.objects.filter(is_active=True), q).order_by("-similarity", "id")
        return list(products.values_list("product_code", flat=True))

    def test_latin_and_cyrillic_give_the_same_result(self):
        self.assertEqual(self.found("podshipnik 6203"), ["B1", "B2"])
        self.assertEqual(self.found("подшипник 6203"), ["B1", "B2"])
        self.assertEqual(self.found("podshipnik"), ["B1", "B2", "B3"])

    def test_dash_space_and_case(self):
        self.assertEqual(self.found("6203 2rs"), ["B1"])
        self.assertEqual(self.found("6203-2RS"), ["B1"])
        self.assertEqual(self.found("2rs 6203"), ["B1"])

    def test_lookalike_letters(self):
        self.assertEqual(self.found("винт М6"), ["S1"])  # Cyrillic М in the query, Latin M in the name
        self.assertEqual(self.found("vint m6x20"), ["S1"])
        self.assertEqual(self.found("винт m8x30"), ["S2"])
        self.assertEqual(self.found("din 912"), ["S1", "S2"])

    def test_decimal_comma_and_times_sign(self):
        self.assertEqual(self.found("кабель ввг 3х2.5"), ["K1"])
        self.assertEqual(self.found("kabel vvg 3x2,5"), ["K1"])

    def test_typo(self):
        self.assertEqual(self.found("подшипнек"), ["B1", "B2", "B3"])
        self.assertEqual(self.found("perforatr"), ["X1"])
        # numbers and short codes are never fuzzy
        self.assertEqual(self.found("6204"), [])

    def test_brand_and_articul(self):
        self.assertEqual(self.found("skf 6203"), ["B1"])
        self.assertEqual(self.found("подшипник skf"), ["B1"])

    def test_synonyms(self):
        self.assertEqual(self.found("180203"), [])
        SearchSynonym.objects.create(terms=["6203 2RS", "6203-2RS", "180203"])
        self.assertEqual(self.found("180203"), ["B1"])
        self.assertEqual(self.found("подшипник 180203"), ["B1"])
        SearchSynonym.objects.update(is_active=False)  # update() skips save(): the cache stays
        cache.clear()
        self.assertEqual(self.found("180203"), [])

    def test_variants(self):
        self.assertEqual(query_variants("  Podshipnik   6203-2RS "), ["podshipnik 6203 2rs", fold("подшипник 6203 2rs")])
        self.assertEqual(query_variants("klemmniy"), ["klemmniy", fold("клеммный")])
        self.assertEqual(query_variants(" - "), [])


class SearchEndpointTests(SearchCatalogMixin, ApiTestCase):
    def search(self, q, language="ru", client=None, **body):
        response = (client or APIClient()).post(FILTER, {"q": q, "page": 1, "page_size": 20, **body}, format="json",
                                                HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.data)
        return [product["id"] for product in response.data["result"]["content"]]

    def test_filter_endpoint(self):
        self.assertEqual(self.search("podshipnik 6203"), self.search("подшипник 6203"))
        self.assertEqual(self.search("6203 2rs"), [self.bearing.id])

    def test_suggestions(self):
        response = APIClient().get(SUGGEST, {"q": "podshipnik 6203"}, HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(response.data["result"]["products"], ["Подшипник 6203-2RS", "Подшипник 6203 открытый"])

    def test_not_found_is_logged(self):
        self.search("gidroizolyatsiya", language="uz", platform="ios")
        row = NotFoundSearch.objects.get()
        self.assertEqual((row.query, row.normalized, row.language, row.platform), (
            "gidroizolyatsiya", "gidroizolyatsiya", "uz", "ios"))

    def test_found_or_filtered_is_not_logged(self):
        self.search("podshipnik")
        self.search("gidroizolyatsiya", price_from=1)  # a filter may be the reason: not logged
        self.search("gidroizolyatsiya", page=2)
        self.assertFalse(NotFoundSearch.objects.exists())

    def test_typing_updates_one_row(self):
        client = APIClient(HTTP_X_DEVICE_ID="device-1")
        self.search("gidroizol", client=client)
        self.search("gidroizolyatsiya", client=client)
        self.search("gidroizolyatsiya", client=APIClient(HTTP_X_DEVICE_ID="device-2"))
        rows = NotFoundSearch.objects.order_by("id")
        self.assertEqual([(row.normalized, row.session_id) for row in rows],
                         [("gidroizolyatsiya", "device-1"), ("gidroizolyatsiya", "device-2")])

    def test_request(self):
        customer = make_customer("+998900000077")
        with mock.patch("apps.service.search_log.run_in_background") as background, \
                self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(customer).post(REQUESTS, {
                "query": "Подшипник 180203", "phone_number": "+998 90 123-45-67", "company": " Stroy LLC "},
                format="json", HTTP_ACCEPT_LANGUAGE="uz")
        self.assertEqual(response.status_code, 200, response.data)
        request = SearchRequest.objects.get()
        self.assertEqual((request.query, request.phone_number, request.company, request.customer, request.language,
                          request.status), ("Подшипник 180203", "+998901234567", "Stroy LLC", customer, "uz", "new"))
        background.assert_called_once()
        self.assertEqual(background.call_args.args[1], request.id)
        self.assertIn("Искали: Подшипник 180203", search_log.request_message(request))
        self.assertIn("🏢 Stroy LLC", search_log.request_message(request))

    def test_request_validation_and_limit(self):
        response = APIClient().post(REQUESTS, {"query": " ", "phone_number": "12345"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data["detail"]), {"query", "phone_number"})
        with mock.patch("apps.service.search_log.run_in_background"):
            codes = [APIClient().post(REQUESTS, {"query": "x", "phone_number": "998901234567"}, format="json")
                     .status_code for _ in range(search_log.REQUESTS_PER_HOUR + 1)]
        self.assertEqual(codes, [200] * search_log.REQUESTS_PER_HOUR + [429])
        self.assertEqual(SearchRequest.objects.count(), search_log.REQUESTS_PER_HOUR)


class SearchAdminTests(TestCase):
    def setUp(self):
        cache.clear()
        admin = get_user_model().objects.create_user("search-admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(admin)

    def test_synonyms_crud(self):
        response = self.client.post("/api/v1/admin/search/synonyms/",
                                    {"terms": ["6203 2RS", "6203-2rs", "180203"]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["terms"], ["6203 2RS", "180203"])  # 6203-2rs = 6203 2RS
        response = self.client.post("/api/v1/admin/search/synonyms/", {"terms": ["a b", "A-B"]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_not_found_report(self):
        now = timezone.now()
        rows = [("Gidroizolyatsiya", "gidroizolyatsiya", "uz", None, "d1", now),
                ("gidroizolyatsiya", "gidroizolyatsiya", "uz", None, "d2", now - timedelta(days=1)),
                ("gidroizolyatsiya", "gidroizolyatsiya", "ru", None, "d2", now - timedelta(days=2)),
                ("plitka", "plitka", "ru", None, "d1", now),
                ("old", "old", "ru", None, "d1", now - timedelta(days=40))]
        for query, normalized, language, customer, session, created_at in rows:
            row = NotFoundSearch.objects.create(query=query, normalized=normalized, language=language,
                                                customer=customer, session_id=session)
            NotFoundSearch.objects.filter(pk=row.pk).update(created_at=created_at)
        response = self.client.get("/api/v1/admin/search/not-found/")
        self.assertEqual(response.status_code, 200, response.data)
        result = [(r["query"], r["searches"], r["viewers"], sorted(r["languages"])) for r in response.data["results"]]
        self.assertEqual(result, [("gidroizolyatsiya", 3, 2, ["ru", "uz"]), ("plitka", 1, 1, ["ru"])])
        response = self.client.get("/api/v1/admin/search/not-found/", {"language": "uz"})
        self.assertEqual([(r["query"], r["searches"]) for r in response.data["results"]], [("gidroizolyatsiya", 2)])
        response = self.client.get("/api/v1/admin/search/not-found/export/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Disposition"].startswith("attachment"))

    def test_requests(self):
        request = SearchRequest.objects.create(query="x", phone_number="+998901234567", language="ru")
        response = self.client.patch(f"/api/v1/admin/search/requests/{request.id}/",
                                     {"status": "done", "manager_comment": "called", "query": "y"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        request.refresh_from_db()
        self.assertEqual((request.status, request.manager_comment, request.query), ("done", "called", "x"))
        response = self.client.get("/api/v1/admin/search/requests/stats/")
        self.assertEqual(response.data, {"total": 1, "new": 0, "in_progress": 0, "done": 1, "rejected": 0})
