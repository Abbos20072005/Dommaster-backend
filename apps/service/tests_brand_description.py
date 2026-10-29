"""Brand page text (BLD-248): admin keeps uz and ru apart, client brands/<id>/ returns the request language.

Run: env/Scripts/python.exe manage.py test apps.service.tests_brand_description
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.service.models import Brand

UZ_TEXT = "<p>Knauf - Germaniya brendi</p>"
RU_TEXT = "<p>Knauf - немецкий бренд</p>"


class BrandDescriptionTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name_ru="Knauf", name_uz="Knauf", image="brand/image/knauf.png")
        staff = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.admin = APIClient()
        self.admin.force_authenticate(staff)
        self.admin_url = f"/api/v1/admin/brands/{self.brand.id}/"
        self.client_url = f"/api/v1/brands/{self.brand.id}/"

    def patch(self, data, language):
        response = self.admin.patch(self.admin_url, data, format="json", HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def get(self, language):
        response = APIClient().get(self.client_url, HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["result"]

    def test_admin_keeps_uz_and_ru_apart(self):
        data = self.patch({"description_uz": UZ_TEXT, "description_ru": RU_TEXT}, language="uz")
        self.assertEqual((data["description_uz"], data["description_ru"]), (UZ_TEXT, RU_TEXT))
        # saving one language (whatever the panel's Accept-Language) leaves the other one as it is
        self.patch({"description_uz": "<p>Yangi</p>"}, language="ru")
        self.patch({"name_uz": "Knauf UZ"}, language="uz")
        self.brand.refresh_from_db()
        self.assertEqual((self.brand.description_uz, self.brand.description_ru), ("<p>Yangi</p>", RU_TEXT))
        self.assertEqual((self.brand.name_uz, self.brand.name_ru), ("Knauf UZ", "Knauf"))

    def test_client_returns_the_request_language(self):
        Brand.objects.filter(pk=self.brand.pk).update(description_uz=UZ_TEXT, description_ru=RU_TEXT)
        self.assertEqual(self.get("uz")["description"], UZ_TEXT)
        self.assertEqual(self.get("ru")["description"], RU_TEXT)
        self.assertEqual(self.get("en")["description"], RU_TEXT)

    def test_no_uz_text_means_no_block_in_uz(self):
        Brand.objects.filter(pk=self.brand.pk).update(description_ru=RU_TEXT)
        self.assertEqual(self.get("uz")["description"], "")
        self.assertEqual(self.get("ru")["description"], RU_TEXT)
