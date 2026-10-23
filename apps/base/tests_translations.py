"""The base content endpoints in the request language, and `backfill_empty_translations`.

Run: env/Scripts/python.exe manage.py test apps.base.tests_translations
"""
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.base.models import MarketBranch, News


def make_news(**fields):
    data = {"title_uz": "Yangilik", "title_ru": "Новость", "description_uz": "Uz matn",
            "description_ru": "Рус текст", "image": "news/x.png", **fields}
    return News.objects.create(**data)


class BaseContentLanguageTests(TestCase):
    def get(self, url, language=None):
        headers = {"HTTP_ACCEPT_LANGUAGE": language} if language else {}
        response = APIClient().get(url, **headers)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["result"]

    def test_news_list_in_both_languages(self):
        make_news()
        self.assertEqual(self.get("/api/v1/base/news/", "uz")["content"][0]["title"], "Yangilik")
        self.assertEqual(self.get("/api/v1/base/news/", "ru")["content"][0]["title"], "Новость")

    def test_news_list_with_a_browser_header_is_uz(self):
        make_news()
        result = self.get("/api/v1/base/news/", "uz-UZ,uz;q=0.9,ru;q=0.8")
        self.assertEqual(result["content"][0]["title"], "Yangilik")

    def test_news_detail_falls_back_to_ru(self):
        news = make_news(title_uz="", description_uz="")
        result = self.get(f"/api/v1/base/news/{news.id}/", "uz")
        self.assertEqual((result["title"], result["description"]), ("Новость", "Рус текст"))


class EmptyTranslationBackfillTests(TestCase):
    """`""` in a nullable column counts as a filled value for modeltranslation, so it blocks the fallback."""

    def setUp(self):
        self.branch = MarketBranch.objects.create(
            name="Chilonzor", name_ru="Чиланзар", name_uz="", branch_type=1,
            address_ru="Бунёдкор 1", address_uz="", landmark_ru="Metro", landmark_uz="",
        )

    def test_empty_strings_become_null_only_where_they_block_the_fallback(self):
        call_command("backfill_empty_translations")
        self.branch.refresh_from_db()
        # address is null=True -> "" had to become NULL
        self.assertIsNone(self.branch.address_uz)
        # name and landmark default to "" -> "" already means "not filled", the rows stay untouched
        self.assertEqual((self.branch.name_uz, self.branch.landmark_uz), ("", ""))

    def test_dry_run_changes_nothing(self):
        call_command("backfill_empty_translations", "--dry-run")
        self.branch.refresh_from_db()
        self.assertEqual(self.branch.address_uz, "")

    def test_running_it_again_does_nothing(self):
        call_command("backfill_empty_translations")
        call_command("backfill_empty_translations")
        self.branch.refresh_from_db()
        self.assertIsNone(self.branch.address_uz)

    def test_store_serves_the_ru_address_in_uz_after_the_backfill(self):
        response = APIClient().get(f"/api/v1/base/stores/{self.branch.id}/", HTTP_ACCEPT_LANGUAGE="uz")
        self.assertEqual(response.data["result"]["address"], "")

        call_command("backfill_empty_translations")
        response = APIClient().get(f"/api/v1/base/stores/{self.branch.id}/", HTTP_ACCEPT_LANGUAGE="uz")
        self.assertEqual(response.data["result"]["address"], "Бунёдкор 1")
