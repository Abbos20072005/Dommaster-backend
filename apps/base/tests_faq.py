from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.base.faq import clean_answer
from apps.base.models import FaqItem

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "faq-tests"}}


def make_item(category, position, page_keys=("faq",), **fields):
    data = {"question_ru": f"Вопрос {position}", "question_uz": f"Savol {position}",
            "answer_ru": f"<p>Ответ {position}</p>", "answer_uz": f"<p>Javob {position}</p>"}
    data.update(fields)
    return FaqItem.objects.create(category=category, position=position, page_keys=list(page_keys), **data)


class CleanAnswerTests(TestCase):
    def test_allowed_tags_stay(self):
        html = '<p>Bu <b>muhim</b>, <a href="https://buildex.uz/returns">batafsil</a></p><ul><li>bir</li></ul>'
        self.assertEqual(
            clean_answer(html),
            '<p>Bu <b>muhim</b>, <a href="https://buildex.uz/returns" rel="noopener noreferrer">batafsil</a></p>'
            '<ul><li>bir</li></ul>')

    def test_script_event_handlers_and_bad_links_are_dropped(self):
        html = ('<p onclick="alert(1)">Salom<script>alert(1)</script><img src=x onerror=alert(1)></p>'
                '<a href="javascript:alert(1)">x</a><a href=" jav&#x09;ascript:alert(1)">y</a>'
                '<a href="//evil.com">z</a><style>p{}</style><iframe src="x">ichida</iframe>')
        self.assertEqual(clean_answer(html), "<p>Salom</p><a>x</a><a>y</a><a>z</a>")

    def test_text_is_escaped_and_tags_closed(self):
        self.assertEqual(clean_answer("1 < 2 &amp; <b>qalin"), "1 &lt; 2 &amp; <b>qalin</b>")
        self.assertEqual(clean_answer(clean_answer("<ul><li>a<li>b</ul>")), clean_answer("<ul><li>a<li>b</ul>"))

    def test_site_path_mail_and_phone_links(self):
        self.assertIn('href="/pickup"', clean_answer('<a href="/pickup">x</a>'))
        self.assertIn('href="tel:+998712000000"', clean_answer('<a href="tel:+998712000000">x</a>'))
        self.assertIn('href="mailto:info@buildex.uz"', clean_answer('<a href="mailto:info@buildex.uz">x</a>'))

    def test_model_save_cleans(self):
        item = make_item("general", 1, answer_ru="<b>a</b><script>x</script>", answer_uz="<i>b</i>")
        item.refresh_from_db()
        self.assertEqual((item.answer_ru, item.answer_uz), ("<b>a</b>", "b"))


@override_settings(CACHES=LOCMEM)
class FaqClientTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.d2 = make_item("delivery", 2, page_keys=("faq", "courier-delivery"))
        self.d1 = make_item("delivery", 1)
        make_item("delivery", 3, is_active=False)
        self.r1 = make_item("general", 1, page_keys=("faq", "returns"))
        make_item("technical", 1, is_active=False)

    def get(self, query="", language="ru"):
        response = self.client.get(f"/api/v1/faq/{query}", HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["result"]

    def test_fixed_category_order_and_only_categories_with_active_questions(self):
        result = self.get()
        self.assertEqual([c["slug"] for c in result], ["general", "delivery"])
        self.assertEqual([q["id"] for q in result[1]["questions"]], [self.d1.id, self.d2.id])
        self.assertEqual(result[1]["name"], "Доставка")
        self.assertEqual(result[1]["questions"][0]["answer"], "<p>Ответ 1</p>")
        self.assertIn("updated_at", result[1]["questions"][0])

    def test_uz(self):
        result = self.get(language="uz")
        self.assertEqual([c["name"] for c in result], ["Umumiy", "Yetkazib berish"])
        self.assertEqual(result[1]["questions"][0]["question"], "Savol 1")

    def test_page_filter(self):
        result = self.get("?page=returns")
        self.assertEqual([c["slug"] for c in result], ["general"])
        self.assertEqual([q["id"] for q in result[0]["questions"]], [self.r1.id])
        result = self.get("?page=courier-delivery")
        self.assertEqual([[q["id"] for q in c["questions"]] for c in result], [[self.d2.id]])
        self.assertEqual(self.get("?page=pro"), [])

    def test_unknown_page_is_400(self):
        response = self.client.get("/api/v1/faq/?page=nope")
        self.assertEqual(response.status_code, 400)

    def test_admin_change_drops_the_cache(self):
        self.assertEqual(self.get()[1]["questions"][0]["question"], "Вопрос 1")
        admin = get_user_model().objects.create_user("faq-admin", password="x", is_staff=True)
        admin_client = APIClient()
        admin_client.force_authenticate(admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = admin_client.patch(f"/api/v1/admin/faq-items/{self.d1.id}/", {"question_ru": "Новый"},
                                          format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.get()[1]["questions"][0]["question"], "Новый")


@override_settings(CACHES=LOCMEM)
class FaqAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin = get_user_model().objects.create_user("faq-admin", password="x", is_staff=True)
        self.client.force_authenticate(admin)

    def test_anonymous_cannot_write(self):
        # no token = 401 (as every admin endpoint), a non-admin token = 403
        anonymous = APIClient()
        for response in (
            anonymous.post("/api/v1/admin/faq-items/", {}, format="json"),
            anonymous.delete("/api/v1/admin/faq-items/1/"),
        ):
            self.assertEqual(response.status_code, 401)

    def test_categories_are_not_an_endpoint(self):
        self.assertEqual(self.client.get("/api/v1/admin/faq-topics/").status_code, 404)

    def test_both_languages_required(self):
        response = self.client.post("/api/v1/admin/faq-items/", {
            "category": "general", "question_ru": "Вопрос", "question_uz": "",
            "answer_ru": "Ответ", "answer_uz": "<script>x</script>"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"question_uz", "answer_uz"})
        item = make_item("general", 1)
        response = self.client.patch(f"/api/v1/admin/faq-items/{item.id}/", {"answer_ru": ""}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("answer_ru", response.json())

    def test_create_item(self):
        response = self.client.post("/api/v1/admin/faq-items/", {
            "category": "payment", "question_ru": "Вопрос", "question_uz": "Savol",
            "answer_ru": '<p onclick="x()">Ответ</p>', "answer_uz": "Javob",
            "page_keys": ["returns", "faq", "returns"]}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["answer_ru"], "<p>Ответ</p>")
        self.assertEqual(data["page_keys"], ["returns", "faq"])
        self.assertEqual((data["category"], data["category_name"]), ("payment", "Оплата"))
        self.assertEqual(data["position"], 1)

    def test_bad_category_and_page_key(self):
        base = {"question_ru": "В", "question_uz": "S", "answer_ru": "О", "answer_uz": "J"}
        for extra, field in (({"category": "nope"}, "category"),
                             ({"page_keys": ["nope"], "category": "general"}, "page_keys"),
                             ({}, "category")):
            response = self.client.post("/api/v1/admin/faq-items/", {**base, **extra}, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.json())

    def test_moving_to_another_category_goes_to_its_end(self):
        make_item("orders", 4)
        item = make_item("general", 1)
        response = self.client.patch(f"/api/v1/admin/faq-items/{item.id}/", {"category": "orders"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["position"], 5)

    def test_list_in_category_order_and_filters(self):
        delivery = make_item("delivery", 1)
        general = make_item("general", 1, page_keys=("faq", "pickup"))
        orders = make_item("orders", 1)

        def ids(query):
            return [row["id"] for row in self.client.get(f"/api/v1/admin/faq-items/{query}").json()["results"]]

        self.assertEqual(ids(""), [general.id, orders.id, delivery.id])
        self.assertEqual(ids("?category=orders"), [orders.id])
        self.assertEqual(ids("?page_key=pickup"), [general.id])

    def test_reorder(self):
        a, b, c = (make_item("general", n) for n in (1, 2, 3))
        response = self.client.post("/api/v1/admin/faq-items/reorder/", {"ids": [c.id, a.id]}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        listing = self.client.get("/api/v1/admin/faq-items/?category=general").json()["results"]
        self.assertEqual([row["id"] for row in listing], [c.id, a.id, b.id])
        other = make_item("orders", 1)
        response = self.client.post("/api/v1/admin/faq-items/reorder/", {"ids": [a.id, other.id]}, format="json")
        self.assertEqual(response.status_code, 400)
