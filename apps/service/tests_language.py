"""The client API answers in the language of `Accept-Language` (LocaleMiddleware + modeltranslation).

Run: env/Scripts/python.exe manage.py test apps.service
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.service.models import Brand, Product
from apps.service.tests import ApiTestCase, make_item_category, make_product

BROWSER_HEADER = "uz-UZ,uz;q=0.9,ru;q=0.8"


class ClientLanguageTests(ApiTestCase):
    def setUp(self):
        self.category, self.item_category = make_item_category("Asboblar")
        self.category.name_uz, self.category.name_ru = "Asboblar", "Инструменты"
        self.category.save()
        self.brand = Brand.objects.create(name="Bosch", name_uz="Bosch uz", name_ru="Bosch ru")
        self.product = make_product("P1", self.item_category, 1000)
        self.product.name_uz, self.product.name_ru = "Perforator", "Перфоратор"
        self.product.description_uz, self.product.description_ru = "Uz matn", "Рус текст"
        self.product.brand = self.brand
        self.product.save()
        # no uz text at all -> the ru one is served in uz too
        self.only_ru = make_product("P2", self.item_category, 2000)
        self.only_ru.name_uz, self.only_ru.name_ru = "", "Молоток"
        self.only_ru.save()

    def get(self, url, language=None):
        headers = {"HTTP_ACCEPT_LANGUAGE": language} if language else {}
        response = APIClient().get(url, **headers)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["result"]

    def test_product_detail_in_uz(self):
        result = self.get(f"/api/v1/products/{self.product.id}/", "uz")
        self.assertEqual((result["name"], result["description"]), ("Perforator", "Uz matn"))
        self.assertEqual(result["brand"]["name"], "Bosch uz")

    def test_product_detail_in_ru(self):
        result = self.get(f"/api/v1/products/{self.product.id}/", "ru")
        self.assertEqual((result["name"], result["description"]), ("Перфоратор", "Рус текст"))
        self.assertEqual(result["brand"]["name"], "Bosch ru")

    def test_product_detail_without_a_header_is_ru(self):
        self.assertEqual(self.get(f"/api/v1/products/{self.product.id}/")["name"], "Перфоратор")

    def test_product_detail_with_a_browser_header_is_uz(self):
        self.assertEqual(self.get(f"/api/v1/products/{self.product.id}/", BROWSER_HEADER)["name"], "Perforator")

    def test_unknown_language_is_ru(self):
        self.assertEqual(self.get(f"/api/v1/products/{self.product.id}/", "en-US,en;q=0.9")["name"], "Перфоратор")

    def test_empty_uz_name_falls_back_to_ru(self):
        self.assertEqual(self.get(f"/api/v1/products/{self.only_ru.id}/", "uz")["name"], "Молоток")

    def test_product_slug_is_per_language(self):
        # the slug is generated from the name of each language when the product is created
        product = Product.objects.create(name="Shurupovert", name_uz="Shurupovert", name_ru="Шуруповёрт",
                                         description="", product_code="P3", price=1000, quantity=5,
                                         product_item_category=self.item_category)
        self.assertNotEqual(product.slug_uz, product.slug_ru)
        self.assertEqual(self.get(f"/api/v1/products/{product.id}/", "uz")["slug"], product.slug_uz)
        self.assertEqual(self.get(f"/api/v1/products/{product.id}/", "ru")["slug"], product.slug_ru)

    def test_category_detail_and_breadcrumbs(self):
        result = self.get(f"/api/v1/item/categories/{self.item_category.id}/", "uz")
        self.assertEqual([crumb["name"] for crumb in result["breadcrumbs"]][0], "Asboblar")
        result = self.get(f"/api/v1/item/categories/{self.item_category.id}/", "ru")
        self.assertEqual([crumb["name"] for crumb in result["breadcrumbs"]][0], "Инструменты")

    def test_brand_detail(self):
        self.assertEqual(self.get(f"/api/v1/brands/{self.brand.id}/", "uz")["name"], "Bosch uz")
        self.assertEqual(self.get(f"/api/v1/brands/{self.brand.id}/", "ru")["name"], "Bosch ru")

    def test_categories_menu(self):
        cache.delete("categories:lists:uz")
        cache.delete("categories:lists:ru")
        self.assertEqual(self.get("/api/v1/categories/", "uz")[0]["name"], "Asboblar")
        self.assertEqual(self.get("/api/v1/categories/", "ru")[0]["name"], "Инструменты")


class AdminLanguageTests(ApiTestCase):
    """The admin API keeps the default language: a plain `name` must not be read from or written to uz."""

    def setUp(self):
        _, self.item_category = make_item_category("Asboblar")
        self.product = make_product("P1", self.item_category, 1000)
        self.product.name_uz, self.product.name_ru = "Perforator", "Перфоратор"
        self.product.save()
        self.client_ = APIClient()
        self.client_.force_authenticate(get_user_model().objects.create_user("admin", password="x", is_staff=True))

    def test_list_stays_ru_with_a_uz_header(self):
        response = self.client_.get("/api/v1/admin/products/", HTTP_ACCEPT_LANGUAGE="uz")
        self.assertEqual(response.status_code, 200, response.data)
        row = next(row for row in response.data["results"] if row["id"] == self.product.id)
        self.assertEqual(row["name"], "Перфоратор")

    def test_write_with_a_uz_header_does_not_touch_the_uz_column(self):
        response = self.client_.patch(f"/api/v1/admin/products/{self.product.id}/",
                                      {"name_ru": "Перфоратор 2"}, format="json", HTTP_ACCEPT_LANGUAGE="uz")
        self.assertEqual(response.status_code, 200, response.data)
        product = Product.objects.get(pk=self.product.pk)
        self.assertEqual((product.name_ru, product.name_uz), ("Перфоратор 2", "Perforator"))
