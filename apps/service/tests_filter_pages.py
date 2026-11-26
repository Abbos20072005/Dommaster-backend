"""Filter landing pages: brand x category / sub category pages next to the item category ones.

Run: env/Scripts/python.exe manage.py test apps.service.tests_filter_pages
"""
import hashlib
import io
import json
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.service import filter_pages
from apps.service.models import Brand, FilterPage, ProductItemCategory
from apps.service.tests import make_item_category, make_product

ADMIN_URL = "/api/v1/admin/filter-pages/"


class FilterPageLevelTests(TestCase):
    def setUp(self):
        # Сухие смеси (sub category) -> Штукатурка, Шпаклёвка (item categories)
        self.category, self.plaster = make_item_category("Сухие смеси")
        self.sub_category = self.plaster.product_sub_category
        self.putty = ProductItemCategory.objects.create(product_sub_category=self.sub_category, name="Шпаклёвка",
                                                        name_ru="Шпаклёвка", name_uz="Shpaklyovka")
        self.knauf = Brand.objects.create(name="Knauf", image="brand/knauf.png")
        self.other = Brand.objects.create(name="Ceresit", image="brand/ceresit.png")
        for code, item_category, brand in (("K1", self.plaster, self.knauf), ("K2", self.plaster, self.knauf),
                                           ("K3", self.putty, self.knauf), ("C1", self.putty, self.other)):
            product = make_product(code, item_category, 1000)
            product.brand = brand
            product.save()
        self.client = APIClient()
        self.admin = APIClient()
        self.admin.force_authenticate(get_user_model().objects.create_user("admin", password="x", is_staff=True))

    def make_page(self, **fields):
        page = FilterPage.objects.create(title_ru="Сухие смеси Knauf", keyword_ru="сухие смеси knauf", **fields)
        filter_pages.refresh_counts([page])
        return page

    def test_sub_category_page_counts_every_item_category_below(self):
        page = self.make_page(sub_category=self.sub_category, brand=self.knauf)
        self.assertEqual(page.level, "sub_category")
        self.assertEqual(page.products_count, 3)
        self.assertTrue(page.is_open)

    def test_category_page_counts_the_whole_category(self):
        page = self.make_page(category=self.category, brand=self.other)
        self.assertEqual(page.products_count, 1)
        self.assertFalse(page.is_open)

    def test_client_detail_of_a_sub_category_page(self):
        page = self.make_page(sub_category=self.sub_category, brand=self.knauf)
        result = self.client.get(f"/api/v1/filter-pages/{page.slug}/").json()["result"]
        self.assertEqual(result["level"], "sub_category")
        self.assertIsNone(result["item_category"])
        self.assertEqual([crumb["level"] for crumb in result["breadcrumbs"]],
                         ["product_category", "product_sub_category"])
        self.assertEqual(result["product_filter"],
                         {"sub_category": self.sub_category.id, "brand": self.knauf.id, "filters": {}})

    def test_client_list_by_level(self):
        sub_page = self.make_page(sub_category=self.sub_category, brand=self.knauf)
        item_page = FilterPage.objects.create(title_ru="Штукатурка Knauf", item_category=self.plaster,
                                              brand=self.knauf)
        filter_pages.refresh_counts([item_page])
        FilterPage.objects.filter(pk=item_page.pk).update(products_count=3)

        result = self.client.get("/api/v1/filter-pages/").json()["result"]
        self.assertEqual({row["slug"] for row in result}, {sub_page.slug, item_page.slug})
        row = next(row for row in result if row["slug"] == item_page.slug)
        self.assertEqual(row["level"], "item_category")
        self.assertEqual(row["item_category"]["id"], self.plaster.id)
        self.assertEqual(len(row["breadcrumbs"]), 3)

        result = self.client.get(f"/api/v1/filter-pages/?sub_category={self.sub_category.id}").json()["result"]
        self.assertEqual([row["slug"] for row in result], [sub_page.slug])

    def test_resolve_takes_the_most_specific_level(self):
        page = self.make_page(sub_category=self.sub_category, brand=self.knauf)
        resolve = lambda body: self.client.post("/api/v1/filter-pages/resolve/", body, format="json").json()

        body = {"category": self.category.id, "sub_category": self.sub_category.id, "brand": self.knauf.id}
        self.assertEqual(resolve(body)["result"]["slug"], page.slug)
        self.assertIsNone(resolve({**body, "item_category": self.plaster.id})["result"]["slug"])
        self.assertIsNone(resolve({**body, "brand": self.other.id})["result"]["slug"])
        self.assertIsNone(resolve({**body, "filters": {"price": {"min": 1}}})["result"]["slug"])
        self.assertFalse(resolve({"brand": self.knauf.id})["ok"])

    def test_item_category_page_keeps_its_old_hash(self):
        old = hashlib.md5(json.dumps([self.plaster.id, self.knauf.id, {}], sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()
        page = FilterPage.objects.create(title_ru="Штукатурка Knauf", item_category=self.plaster, brand=self.knauf)
        self.assertEqual(page.combination_hash, old)
        same_ids = self.make_page(sub_category=self.sub_category, brand=self.knauf)
        self.assertNotEqual(same_ids.combination_hash, old)

    def test_one_level_only_in_the_database(self):
        with self.assertRaises(IntegrityError):
            FilterPage.objects.create(title_ru="x", sub_category=self.sub_category, item_category=self.plaster,
                                      brand=self.knauf)

    def test_admin_create_rules(self):
        base = {"title_ru": "Сухие смеси Knauf"}
        response = self.admin.post(ADMIN_URL, {**base, "sub_category": self.sub_category.id}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("brand", response.data)

        response = self.admin.post(ADMIN_URL, {**base, "sub_category": self.sub_category.id, "brand": self.knauf.id,
                                               "filters": {"price": {"min": 1}}}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("filters", response.data)

        response = self.admin.post(ADMIN_URL, {**base, "category": self.category.id,
                                               "sub_category": self.sub_category.id, "brand": self.knauf.id},
                                   format="json")
        self.assertEqual(response.status_code, 400)

        response = self.admin.post(ADMIN_URL, {**base, "sub_category": self.sub_category.id, "brand": self.knauf.id},
                                   format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["level"], "sub_category")
        self.assertEqual(response.data["products_count"], 3)
        self.assertIsNone(response.data["item_category"])

        response = self.admin.post(ADMIN_URL, {**base, "sub_category": self.sub_category.id, "brand": self.knauf.id},
                                   format="json")
        self.assertEqual(response.status_code, 400)

    def test_admin_patch_moves_the_page_to_another_level(self):
        page = FilterPage.objects.create(title_ru="Штукатурка Knauf", item_category=self.plaster, brand=self.knauf)
        response = self.admin.patch(f"{ADMIN_URL}{page.id}/", {"sub_category": self.sub_category.id}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        page.refresh_from_db()
        self.assertEqual((page.level, page.item_category_id, page.products_count), ("sub_category", None, 3))

        response = self.admin.get(f"{ADMIN_URL}?level=sub_category")
        self.assertEqual([row["id"] for row in response.data["results"]], [page.id])

    def test_import_brand_x_sub_category_row(self):
        rows = [
            "keyword_ru,search_volume,category,sub_category,item_category,brand,filters",
            f"сухие смеси knauf,50,{self.category.id},{self.sub_category.slug_ru},,Knauf,",
            f"сухие смеси ceresit,50,,{self.sub_category.id},,Ceresit,Цвет = белый",
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "pages.csv")
            with open(path, "w", encoding="utf-8") as file:
                file.write("\n".join(rows))
            out = io.StringIO()
            call_command("import_filter_pages", path, stdout=out)

        page = FilterPage.objects.get()
        self.assertEqual((page.level, page.sub_category_id, page.brand_id, page.products_count),
                         ("sub_category", self.sub_category.id, self.knauf.id, 3))
        self.assertIn("filters are only for an item category page", out.getvalue())
