"""Slug history of categories and brands: a slug changed in the admin panel is kept (SlugHistory) and
`seo/resolve` answers the old one with `moved` + the current slug.

Run: env/Scripts/python.exe manage.py test apps.service.tests_seo_slug_history
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.service.models import Brand
from apps.service.tests import make_item_category


class SlugHistoryTests(TestCase):
    def setUp(self):
        self.category, self.item_category = make_item_category("Электрика")
        self.url = f"/api/v1/admin/categories/{self.category.pk}/"
        staff = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.admin = APIClient()
        self.admin.force_authenticate(staff)

    def patch(self, url, data):
        response = self.admin.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def resolve(self, entity_type, slug, language="ru"):
        response = APIClient().get("/api/v1/seo/resolve/", {"type": entity_type, "slug": slug},
                                   HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["result"]

    def test_changed_slug_is_redirected(self):
        self.patch(self.url, {"slug_ru": "elektrotovary"})
        self.assertEqual(self.resolve("category", "elektrika"),
                         {"status": "moved", "type": "category", "id": self.category.pk, "slug": "elektrotovary",
                          "redirect": None})
        self.assertEqual(self.resolve("category", "elektrotovary")["status"], "current")
        # uz slug did not change
        self.assertEqual(self.resolve("category", "elektrika", "uz")["status"], "current")

    def test_every_old_slug_goes_to_the_current_one(self):
        self.patch(self.url, {"slug_ru": "elektrotovary"})
        self.patch(self.url, {"slug_ru": "elektrika-i-svet"})
        for old in ("elektrika", "elektrotovary"):
            self.assertEqual(self.resolve("category", old)["slug"], "elektrika-i-svet")

    def test_slug_used_again_is_current(self):
        self.patch(self.url, {"slug_ru": "elektrotovary"})
        self.patch(self.url, {"slug_ru": "elektrika"})
        self.assertEqual(self.resolve("category", "elektrika")["status"], "current")
        self.assertEqual(self.resolve("category", "elektrotovary")["slug"], "elektrika")

    def test_old_slug_of_a_hidden_category_is_not_found(self):
        self.patch(self.url, {"slug_ru": "elektrotovary", "is_active": False})
        self.assertEqual(self.resolve("category", "elektrika")["status"], "not_found")

    def test_freed_slug_taken_by_another_category_is_current(self):
        self.patch(self.url, {"slug_ru": "elektrotovary"})
        other, _ = make_item_category("Свет")
        self.patch(f"/api/v1/admin/categories/{other.pk}/", {"slug_ru": "elektrika"})
        self.assertEqual(self.resolve("category", "elektrika")["id"], other.pk)

    def test_item_category(self):
        self.patch(f"/api/v1/admin/item-categories/{self.item_category.pk}/", {"slug_uz": "elektr"})
        self.assertEqual(self.resolve("item_category", "elektrika", "uz")["slug"], "elektr")

    def test_brand(self):
        brand = Brand.objects.create(name="Weber", name_ru="Weber", name_uz="Weber", image="brand/image/w.png")
        self.patch(f"/api/v1/admin/brands/{brand.pk}/", {"slug_ru": "weber-vetonit"})
        self.assertEqual(self.resolve("brand", "weber")["slug"], "weber-vetonit")
