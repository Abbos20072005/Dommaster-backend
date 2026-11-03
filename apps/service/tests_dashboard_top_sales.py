"""Admin dashboard top categories / brands / customers (`dashboard/top-sales/`, `dashboard/top-customers/`).
Run: manage.py test apps.service.tests_dashboard_top_sales"""
from datetime import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authorization.models import Customer
from apps.service.models import Brand, Order, OrderItem, Product, ProductCategory, ProductItemCategory, \
    ProductSubCategory

SALES_URL = "/api/v1/admin/dashboard/top-sales/"
CUSTOMERS_URL = "/api/v1/admin/dashboard/top-customers/"
NOW = datetime(2026, 11, 20, 12, 0)


def make_item_category(name):
    category = ProductCategory.objects.create(name=name, name_ru=name, name_uz=name)
    sub = ProductSubCategory.objects.create(product_category=category, name=name, name_ru=name, name_uz=name)
    item = ProductItemCategory.objects.create(product_sub_category=sub, name=name, name_ru=name, name_uz=name)
    return category, item


def make_product(code, item_category, brand=None, price=0):
    return Product.objects.create(name=code, name_ru=code, name_uz=code, description="", product_code=code,
                                  product_item_category=item_category, brand=brand, price=price, quantity=100)


def make_order(created, status, total, lines=(), customer=None):
    """`lines` = [(product, quantity, unit_price)]; unit_price None = an item older than the field."""
    order = Order.objects.create(customer=customer)
    for product, quantity, unit_price in lines:
        OrderItem.objects.create(order=order, product=product, quantity=quantity, unit_price=unit_price)
    Order.objects.filter(pk=order.pk).update(created_at=created, status=status, total_price=total)
    return order


def rows(ranking):
    return [(row["name"], row["amount"], row["orders_count"], row["percent"]) for row in ranking["items"]]


@mock.patch("django.utils.timezone.now", return_value=NOW)
class TopSalesTest(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(admin)
        self.cement, cement = make_item_category("Cement")
        self.paint, paint = make_item_category("Paint")
        knauf = Brand.objects.create(name="Knauf", name_ru="Knauf", name_uz="Knauf")
        tikkurila = Brand.objects.create(name="Tikkurila", name_ru="Tikkurila", name_uz="Tikkurila")
        self.mix = make_product("mix", cement, knauf, price=999)
        self.enamel = make_product("enamel", paint, tikkurila, price=400)
        self.ali = Customer.objects.create(phone_number="+998901234567", full_name="Ali")
        self.vali = Customer.objects.create(phone_number="+998935550011", full_name="Vali",
                                            role=Customer.Role.PRORAB)
        # November: 1100 = goods 600 + 400 and delivery 100 -> split 660 / 440
        make_order(datetime(2026, 11, 5), Order.COMPLETED, 1100,
                   [(self.mix, 2, 300), (self.enamel, 1, 400)], self.ali)
        # 1000 of goods less a promocode of 100
        make_order(datetime(2026, 11, 10), Order.COMPLETED, 900, [(self.mix, 10, 100)], self.vali)
        # canceled / not completed: not sold
        make_order(datetime(2026, 11, 12), Order.CANCELED, 5000, [(self.mix, 50, 100)], self.ali)
        make_order(datetime(2026, 11, 13), Order.DELIVERING, 7000, [(self.enamel, 7, 1000)], self.ali)
        # no customer, no items
        make_order(datetime(2026, 11, 15), Order.COMPLETED, 50)
        # October, item without unit_price -> the current price (400 × 5); the order total still decides
        make_order(datetime(2026, 10, 15), Order.COMPLETED, 2000, [(self.enamel, 5, None)], self.vali)

    def get(self, url, **params):
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_current_month(self, _):
        data = self.get(SALES_URL)
        self.assertEqual((data["period"], data["date_from"], data["date_to"]), ("current_month", "2026-11-01",
                                                                                 "2026-11-20"))
        self.assertEqual((data["total"], data["orders_count"]), (2050.0, 3))
        self.assertEqual(rows(data["categories"]), [("Cement", 1560.0, 2, 76.1), ("Paint", 440.0, 1, 21.5),
                                                    (None, 50.0, 1, 2.4)])
        self.assertEqual(data["categories"]["items"][0]["id"], self.cement.id)
        self.assertEqual(rows(data["brands"]), [("Knauf", 1560.0, 2, 76.1), ("Tikkurila", 440.0, 1, 21.5),
                                                (None, 50.0, 1, 2.4)])
        self.assertEqual(data["brands"]["others"], {"count": 0, "amount": 0.0, "orders_count": 0, "percent": 0.0})

    def test_total_is_the_revenue_card(self, _):
        data = self.get(SALES_URL, date_from="2026-10-01", date_to="2026-11-20")
        card = self.get("/api/v1/admin/dashboard/", date_from="2026-10-01", date_to="2026-11-20")
        self.assertEqual(data["period"], "custom")
        self.assertEqual(data["total"], card["summary"]["revenue"]["value"])
        self.assertEqual(data["total"], 4050.0)
        for ranking in (data["categories"], data["brands"]):
            self.assertEqual(sum(row["amount"] for row in ranking["items"]) + ranking["others"]["amount"], 4050.0)

    def test_periods(self, _):
        data = self.get(SALES_URL, period="last_3_months")
        self.assertEqual((data["date_from"], data["total"]), ("2026-09-01", 4050.0))
        self.assertEqual(rows(data["categories"])[0], ("Paint", 2440.0, 2, 60.2))
        data = self.get(SALES_URL, period="all_time")
        self.assertEqual((data["date_from"], data["total"]), ("2026-10-15", 4050.0))
        data = self.get(SALES_URL, period="year")
        self.assertEqual(data["date_from"], "2025-12-01")

    def test_others(self, _):
        Order.objects.all().delete()
        lines = []
        for i in range(1, 13):
            _, item = make_item_category(f"C{i:02d}")
            lines.append((make_product(f"p{i}", item), 1, i * 100))
        make_order(datetime(2026, 11, 2), Order.COMPLETED, 7800, lines)
        data = self.get(SALES_URL)
        categories = data["categories"]
        self.assertEqual([row["name"] for row in categories["items"]], [f"C{i:02d}" for i in range(12, 2, -1)])
        self.assertEqual(categories["others"], {"count": 2, "amount": 300.0, "orders_count": 1, "percent": 3.8})
        self.assertEqual(sum(row["amount"] for row in categories["items"]) + categories["others"]["amount"], 7800.0)

    def test_empty(self, _):
        Order.objects.all().delete()
        data = self.get(SALES_URL, period="all_time")
        self.assertEqual((data["date_from"], data["total"], data["categories"]["items"]), (None, 0.0, []))
        self.assertEqual(self.get(CUSTOMERS_URL, period="all_time")["customers"], [])

    def test_top_customers(self, _):
        data = self.get(CUSTOMERS_URL)
        self.assertEqual((data["total"], data["orders_count"]), (2050.0, 3))
        ali, vali = data["customers"]
        self.assertEqual(ali, {"id": self.ali.id, "full_name": "Ali", "phone_number": "+998 90 *** ** 67",
                               "role": "user", "is_pro": False, "is_deleted": False, "orders_count": 1,
                               "amount": 1100.0, "percent": 53.7, "last_order_at": "2026-11-05T00:00:00"})
        self.assertEqual((vali["is_pro"], vali["amount"], vali["phone_number"]), (True, 900.0, "+998 93 *** ** 11"))
        data = self.get(CUSTOMERS_URL, period="last_3_months")
        self.assertEqual([(row["full_name"], row["amount"], row["orders_count"], row["last_order_at"])
                          for row in data["customers"]],
                         [("Vali", 2900.0, 2, "2026-11-10T00:00:00"), ("Ali", 1100.0, 1, "2026-11-05T00:00:00")])

    def test_admin_only(self, _):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(CUSTOMERS_URL).status_code, (401, 403))
        self.assertIn(self.client.get(SALES_URL).status_code, (401, 403))

    def test_bad_params(self, _):
        self.assertEqual(self.client.get(SALES_URL, {"period": "last_month"}).status_code, 400)
        self.assertEqual(self.client.get(CUSTOMERS_URL, {"date_from": "2026-11-01"}).status_code, 400)
