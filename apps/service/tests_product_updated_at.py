"""`Product.updated_at` moves with the price and the stock: the site sends it as the page's Last-Modified, so a
change it misses would answer 304 with the old price (BLD-451). Run: env/Scripts/python.exe manage.py test apps.service"""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.service.models import Order, Product
from apps.service.tests import make_customer, make_item_category, make_order, make_product


class ProductUpdatedAtTests(TestCase):
    def setUp(self):
        _, item_category = make_item_category("C")
        self.product = make_product("P1", item_category, 1000)
        self.old = timezone.now() - timedelta(days=1)
        Product.objects.filter(pk=self.product.pk).update(updated_at=self.old)

    def updated_at(self):
        return Product.objects.get(pk=self.product.pk).updated_at

    def test_stock_taken_and_given_back(self):
        order, _ = make_order(make_customer("+998900000451"), [(self.product, 10)], payment_type=1)
        Product.objects.filter(pk=self.product.pk).update(updated_at=self.old)
        order.status = Order.COLLECTING
        order.save(update_fields=["status", "updated_at"])
        self.assertGreater(self.updated_at(), self.old)

        Product.objects.filter(pk=self.product.pk).update(updated_at=self.old)
        order.status = Order.CANCELED
        order.save(update_fields=["status", "updated_at"])
        self.assertGreater(self.updated_at(), self.old)

    def test_1c_price_list(self):
        with mock.patch("apps.integration.one_c.INTEGRATION_API_KEY", "key"):
            response = APIClient().post("/api/v1/integration/1c/price-list/create/", {
                "api_key": "key", "products": [{"product_code": "P1", "product_price": "1200"}],
            }, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        product = Product.objects.get(pk=self.product.pk)
        self.assertEqual(product.price, 1200)
        self.assertGreater(product.updated_at, self.old)
