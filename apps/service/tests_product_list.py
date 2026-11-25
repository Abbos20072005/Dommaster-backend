"""GET /api/v1/products/ pagination stability (BLD launch audit A-14). Run: env/Scripts/python.exe manage.py test apps.service"""
from rest_framework.test import APIClient

from apps.service.tests import ApiTestCase, make_item_category, make_product

PRODUCTS = "/api/v1/products/"


class ProductListTests(ApiTestCase):
    def setUp(self):
        _, item_category = make_item_category("Asboblar")
        self.products = [make_product(f"PL{i}", item_category, 1000 + i) for i in range(5)]
        self.client_ = APIClient()

    def test_default_order_is_stable_across_repeated_calls(self):
        first = self.client_.get(PRODUCTS, {"page": 1, "page_size": 3}).data["result"]
        second = self.client_.get(PRODUCTS, {"page": 1, "page_size": 3}).data["result"]
        self.assertEqual([p["id"] for p in first["content"]], [p["id"] for p in second["content"]])
        self.assertIsNone(first["seed"])

    def test_default_order_has_no_overlap_between_pages(self):
        page1 = self.client_.get(PRODUCTS, {"page": 1, "page_size": 3}).data["result"]
        page2 = self.client_.get(PRODUCTS, {"page": 2, "page_size": 3}).data["result"]
        ids1 = {p["id"] for p in page1["content"]}
        ids2 = {p["id"] for p in page2["content"]}
        self.assertFalse(ids1 & ids2)
        self.assertEqual(ids1 | ids2, {p.id for p in self.products})

    def test_default_order_is_newest_first(self):
        result = self.client_.get(PRODUCTS, {"page": 1, "page_size": 5}).data["result"]
        self.assertEqual([p["id"] for p in result["content"]], [p.id for p in reversed(self.products)])

    def test_random_true_returns_a_seed_and_pages_with_it_dont_repeat(self):
        first = self.client_.get(PRODUCTS, {"page": 1, "page_size": 3, "random": "true"}).data["result"]
        seed = first["seed"]
        self.assertIsNotNone(seed)
        second = self.client_.get(PRODUCTS, {"page": 2, "page_size": 3, "seed": seed}).data["result"]
        ids1 = {p["id"] for p in first["content"]}
        ids2 = {p["id"] for p in second["content"]}
        self.assertFalse(ids1 & ids2)
        self.assertEqual(ids1 | ids2, {p.id for p in self.products})

    def test_sending_seed_implies_random_order(self):
        response = self.client_.get(PRODUCTS, {"page": 1, "page_size": 3, "seed": 42}).data["result"]
        self.assertEqual(response["seed"], 42)
