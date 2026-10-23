"""Category text under the product list (BLD-251): admin keeps uz and ru apart, client returns the request language.

Run: env/Scripts/python.exe manage.py test apps.service.tests_category_description
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.service.models import ProductItemCategory
from apps.service.tests import make_item_category

UZ_TEXT = "<h2>Qanday tanlash</h2><p>Uz matn</p>"
RU_TEXT = "<h2>Как выбрать</h2><p>Рус текст</p>"


class CategoryDescriptionTests(TestCase):
    def setUp(self):
        self.category, self.item_category = make_item_category("Asboblar")
        self.sub_category = self.item_category.product_sub_category
        staff = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.admin = APIClient()
        self.admin.force_authenticate(staff)

    def patch(self, url, data, language="uz"):
        response = self.admin.patch(url, data, format="json", HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def get(self, url, language):
        response = APIClient().get(url, HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["result"]

    def test_admin_keeps_uz_and_ru_apart(self):
        url = f"/api/v1/admin/item-categories/{self.item_category.id}/"
        data = self.patch(url, {"description_uz": UZ_TEXT, "description_ru": RU_TEXT})
        self.assertEqual((data["description_uz"], data["description_ru"]), (UZ_TEXT, RU_TEXT))
        # a later save of one language leaves the other one as it is
        self.patch(url, {"description_uz": "<p>Yangi</p>"}, language="ru")
        self.item_category.refresh_from_db()
        self.assertEqual((self.item_category.description_uz, self.item_category.description_ru),
                         ("<p>Yangi</p>", RU_TEXT))
        self.patch(url, {"name_uz": "Asboblar 2"})
        self.item_category.refresh_from_db()
        self.assertEqual(self.item_category.description_ru, RU_TEXT)

    def test_client_returns_the_request_language(self):
        ProductItemCategory.objects.filter(pk=self.item_category.pk).update(
            description_uz=UZ_TEXT, description_ru=RU_TEXT)
        url = f"/api/v1/item/categories/{self.item_category.id}/"
        self.assertEqual(self.get(url, "uz")["description"], UZ_TEXT)
        self.assertEqual(self.get(url, "ru")["description"], RU_TEXT)

    def test_no_uz_text_means_no_block_in_uz(self):
        ProductItemCategory.objects.filter(pk=self.item_category.pk).update(description_ru=RU_TEXT)
        url = f"/api/v1/item/categories/{self.item_category.id}/"
        self.assertEqual(self.get(url, "uz")["description"], "")
        self.assertEqual(self.get(url, "ru")["description"], RU_TEXT)

    def test_only_the_requested_category_carries_the_text(self):
        self.category.description_ru = "<p>Kategoriya</p>"
        self.category.save()
        ProductItemCategory.objects.filter(pk=self.item_category.pk).update(description_ru=RU_TEXT)
        result = self.get(f"/api/v1/categories/{self.category.id}/", "ru")
        self.assertEqual(result["description"], "<p>Kategoriya</p>")
        sub = result["sub_categories"][0]
        self.assertNotIn("description", sub)
        self.assertNotIn("description", sub["product_item_categories"][0])
        result = self.get(f"/api/v1/sub/categories/{self.sub_category.id}/", "ru")
        self.assertEqual(result["description"], "")
        self.assertNotIn("description", result["product_item_categories"][0])
