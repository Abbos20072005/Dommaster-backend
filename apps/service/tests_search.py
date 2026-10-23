"""Localized name lists of `most/search/` and `search/`. Run: env/Scripts/python.exe manage.py test apps.service"""
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.service.tests import ApiTestCase, make_customer, make_item_category, make_order, make_product

MOST_SEARCH = "/api/v1/most/search/"
SEARCH = "/api/v1/search/"
QUERY = "Перфоратор"


class LocalizedNameListTests(ApiTestCase):
    """`values_list` returns one column for a repeated field name, so ru used to raise a ValueError here."""

    def setUp(self):
        _, item_category = make_item_category("Asboblar")
        self.drill = make_product("P1", item_category, 1000)
        self.drill.name_ru, self.drill.name_uz = "Перфоратор", "Perforator"
        self.drill.save()
        # no uz name -> the ru one is shown in uz too
        self.hammer = make_product("P2", item_category, 2000)
        self.hammer.name_ru, self.hammer.name_uz = "Молоток", ""
        self.hammer.save()

        customer = make_customer("+998900000001")
        make_order(customer, [(self.drill, 5), (self.hammer, 3)])

        for language in ("ru", "uz"):
            cache.delete(f"products:most_search:{language}")
            cache.delete(f"search:v2:{QUERY.lower()}:{language}")

    def names(self, url, language=None, **params):
        headers = {"HTTP_ACCEPT_LANGUAGE": language} if language else {}
        response = APIClient().get(url, params, **headers)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["ok"])
        return response.data["result"]

    def test_most_search_in_ru(self):
        self.assertEqual(self.names(MOST_SEARCH, "ru"), ["Перфоратор", "Молоток"])

    def test_most_search_without_header_is_ru(self):
        self.assertEqual(self.names(MOST_SEARCH), ["Перфоратор", "Молоток"])

    def test_most_search_in_uz_falls_back_to_ru(self):
        self.assertEqual(self.names(MOST_SEARCH, "uz"), ["Perforator", "Молоток"])

    def test_most_search_parses_the_header(self):
        self.assertEqual(self.names(MOST_SEARCH, "uz-UZ,uz;q=0.9,ru;q=0.8"), ["Perforator", "Молоток"])

    def test_search_products_in_ru(self):
        self.assertEqual(self.names(SEARCH, "ru", q=QUERY)["products"], ["Перфоратор"])

    def test_search_products_in_uz(self):
        self.assertEqual(self.names(SEARCH, "uz", q=QUERY)["products"], ["Perforator"])
