"""Product prices are stored rounded up to 100 so'm: Product.save(), the 1C price list, `round_prices` for the old
rows. Run: env/Scripts/python.exe manage.py test apps.service.tests_price_rounding"""
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.service.models import Product
from apps.service.tests import make_item_category, make_product
from utils.price import round_price_up


class RoundPriceUpTests(SimpleTestCase):
    def test_values(self):
        for value, expected in [(None, None), (0, 0), (100, 100), (12300, 12300), (12301, 12400), (12340, 12400),
                                (12399.99, 12400), (12300.01, 12400), (12300.0000001, 12300), (1, 100), ("35503.95", 35600)]:
            with self.subTest(value=value):
                self.assertEqual(round_price_up(value), expected)


class PriceRoundingTests(TestCase):
    def setUp(self):
        _, self.item_category = make_item_category("C")

    def test_save_rounds(self):
        product = make_product("P1", self.item_category, 12340, discount_price=11001.5)
        product.refresh_from_db()
        self.assertEqual((product.price, product.discount_price), (12400, 11100))

        product.price = 15050
        product.discount_price = None
        product.save(update_fields=["price", "discount_price", "updated_at"])
        product.refresh_from_db()
        self.assertEqual((product.price, product.discount_price), (15100, None))

    def test_1c_price_list_rounds(self):
        make_product("P1", self.item_category, 1000)
        with mock.patch("apps.integration.one_c.INTEGRATION_API_KEY", "key"):
            response = APIClient().post("/api/v1/integration/1c/price-list/create/", {
                "api_key": "key",
                "products": [{"product_code": "P1", "product_price": "35503,95", "discount_price": "30010"}],
            }, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        product = Product.objects.get(product_code="P1")
        self.assertEqual((product.price, product.discount_price), (35600, 30100))

    def test_round_prices_command(self):
        product = make_product("P1", self.item_category, 1000)
        rounded = make_product("P2", self.item_category, 2000)
        old = timezone.now() - timedelta(days=1)
        # rows written before the rounding: update() skips save()
        Product.objects.filter(pk=product.pk).update(price=12345.6, discount_price=9999, updated_at=old)
        Product.objects.filter(pk=rounded.pk).update(updated_at=old)

        call_command("round_prices", "--dry-run", stdout=StringIO())
        self.assertEqual(Product.objects.get(pk=product.pk).price, 12345.6)

        out = StringIO()
        call_command("round_prices", stdout=out)
        self.assertIn("products rounded: 1", out.getvalue())
        product.refresh_from_db()
        self.assertEqual((product.price, product.discount_price), (12400, 10000))
        self.assertGreater(product.updated_at, old)
        self.assertEqual(Product.objects.get(pk=rounded.pk).updated_at, old)

        out = StringIO()
        call_command("round_prices", stdout=out)
        self.assertIn("products rounded: 0", out.getvalue())
