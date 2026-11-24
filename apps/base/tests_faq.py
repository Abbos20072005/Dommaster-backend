from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.base.faq import clean_answer
from apps.base.models import FaqItem, FaqTopic

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "faq-tests"}}


def make_topic(slug, position, **fields):
    return FaqTopic.objects.create(slug=slug, position=position, name_ru=f"{slug} ru", name_uz=f"{slug} uz",
                                   **fields)


def make_item(topic, position, page_keys=("faq",), **fields):
    data = {"question_ru": f"Вопрос {position}", "question_uz": f"Savol {position}",
            "answer_ru": f"<p>Ответ {position}</p>", "answer_uz": f"<p>Javob {position}</p>"}
    data.update(fields)
    return FaqItem.objects.create(topic=topic, position=position, page_keys=list(page_keys), **data)


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
        topic = make_topic("general", 1)
        item = make_item(topic, 1, answer_ru="<b>a</b><script>x</script>", answer_uz="<i>b</i>")
        item.refresh_from_db()
        self.assertEqual((item.answer_ru, item.answer_uz), ("<b>a</b>", "b"))


@override_settings(CACHES=LOCMEM)
class FaqClientTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.delivery = make_topic("delivery", 1)
        self.returns = make_topic("returns", 2)
        self.hidden_topic = make_topic("pro", 3, is_active=False)
        self.d2 = make_item(self.delivery, 2, page_keys=("faq", "courier-delivery"))
        self.d1 = make_item(self.delivery, 1)
        make_item(self.delivery, 3, is_active=False)
        self.r1 = make_item(self.returns, 1, page_keys=("faq", "returns"))
        make_item(self.hidden_topic, 1, page_keys=("faq", "returns"))

    def get(self, query="", language="ru"):
        response = self.client.get(f"/api/v1/faq/{query}", HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["result"]

    def test_active_topics_and_questions_in_order(self):
        result = self.get()
        self.assertEqual([t["slug"] for t in result], ["delivery", "returns"])
        self.assertEqual([q["id"] for q in result[0]["questions"]], [self.d1.id, self.d2.id])
        self.assertEqual(result[0]["name"], "delivery ru")
        self.assertEqual(result[0]["questions"][0]["answer"], "<p>Ответ 1</p>")
        self.assertIn("updated_at", result[0]["questions"][0])

    def test_uz(self):
        result = self.get(language="uz")
        self.assertEqual(result[0]["name"], "delivery uz")
        self.assertEqual(result[0]["questions"][0]["question"], "Savol 1")

    def test_page_filter(self):
        result = self.get("?page=returns")
        self.assertEqual([t["slug"] for t in result], ["returns"])
        self.assertEqual([q["id"] for q in result[0]["questions"]], [self.r1.id])
        result = self.get("?page=courier-delivery")
        self.assertEqual([[q["id"] for q in t["questions"]] for t in result], [[self.d2.id]])
        self.assertEqual(self.get("?page=pro"), [])

    def test_unknown_page_is_400(self):
        response = self.client.get("/api/v1/faq/?page=nope")
        self.assertEqual(response.status_code, 400)

    def test_admin_change_drops_the_cache(self):
        self.assertEqual(self.get()[0]["questions"][0]["question"], "Вопрос 1")
        admin = get_user_model().objects.create_user("faq-admin", password="x", is_staff=True)
        admin_client = APIClient()
        admin_client.force_authenticate(admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = admin_client.patch(f"/api/v1/admin/faq-items/{self.d1.id}/", {"question_ru": "Новый"},
                                          format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.get()[0]["questions"][0]["question"], "Новый")


@override_settings(CACHES=LOCMEM)
class FaqAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin = get_user_model().objects.create_user("faq-admin", password="x", is_staff=True)
        self.client.force_authenticate(admin)
        self.topic = make_topic("general", 1)

    def test_anonymous_cannot_write(self):
        # no token = 401 (as every admin endpoint), a non-admin token = 403
        anonymous = APIClient()
        for response in (
            anonymous.post("/api/v1/admin/faq-topics/", {"slug": "x", "name_ru": "x", "name_uz": "x"}, format="json"),
            anonymous.post("/api/v1/admin/faq-items/", {}, format="json"),
            anonymous.delete(f"/api/v1/admin/faq-topics/{self.topic.id}/"),
        ):
            self.assertEqual(response.status_code, 401)

    def test_both_languages_required(self):
        response = self.client.post("/api/v1/admin/faq-topics/", {"slug": "pay", "name_ru": "Оплата"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name_uz", response.json())
        response = self.client.post("/api/v1/admin/faq-items/", {
            "topic": self.topic.id, "question_ru": "Вопрос", "question_uz": "",
            "answer_ru": "Ответ", "answer_uz": "<script>x</script>"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"question_uz", "answer_uz"})
        item = make_item(self.topic, 1)
        response = self.client.patch(f"/api/v1/admin/faq-items/{item.id}/", {"answer_ru": ""}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("answer_ru", response.json())

    def test_create_item(self):
        response = self.client.post("/api/v1/admin/faq-items/", {
            "topic": {"id": self.topic.id}, "question_ru": "Вопрос", "question_uz": "Savol",
            "answer_ru": '<p onclick="x()">Ответ</p>', "answer_uz": "Javob",
            "page_keys": ["returns", "faq", "returns"]}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["answer_ru"], "<p>Ответ</p>")
        self.assertEqual(data["page_keys"], ["returns", "faq"])
        self.assertEqual(data["topic"]["slug"], "general")
        self.assertEqual(data["position"], 1)
        response = self.client.post("/api/v1/admin/faq-items/", {
            "topic": self.topic.id, "question_ru": "В", "question_uz": "S", "answer_ru": "О", "answer_uz": "J",
            "page_keys": ["nope"]}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("page_keys", response.json())

    def test_reorder_and_page_filter(self):
        a, b, c = (make_item(self.topic, n, page_keys=("faq", "pickup") if n == 3 else ("faq",)) for n in (1, 2, 3))
        response = self.client.post("/api/v1/admin/faq-items/reorder/", {"ids": [c.id, a.id]}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        ids = [row["id"] for row in self.client.get("/api/v1/admin/faq-items/").json()["results"]]
        self.assertEqual(ids, [c.id, a.id, b.id])
        other = make_item(make_topic("pay", 2), 1)
        response = self.client.post("/api/v1/admin/faq-items/reorder/", {"ids": [a.id, other.id]}, format="json")
        self.assertEqual(response.status_code, 400)
        ids = [row["id"] for row in self.client.get("/api/v1/admin/faq-items/?page_key=pickup").json()["results"]]
        self.assertEqual(ids, [c.id])

    def test_topic_with_questions_is_not_deleted(self):
        make_item(self.topic, 1)
        self.assertEqual(self.client.delete(f"/api/v1/admin/faq-topics/{self.topic.id}/").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/admin/faq-topics/").json()["results"][0]["items_count"], 1)
