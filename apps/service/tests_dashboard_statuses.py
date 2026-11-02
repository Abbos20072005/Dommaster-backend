"""Admin dashboard status breakdowns (`dashboard/order-statuses/`, `dashboard/product-statuses/`).
Run: manage.py test apps.service.tests_dashboard_statuses"""
from datetime import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.service.models import Order, Product

ORDERS_URL = "/api/v1/admin/dashboard/order-statuses/"
PRODUCTS_URL = "/api/v1/admin/dashboard/product-statuses/"
NOW = datetime(2026, 11, 20, 12, 0)


def make_order(created, status):
    order = Order.objects.create()
    Order.objects.filter(pk=order.pk).update(created_at=created, status=status)
    return order


def counts(data):
    return {row["status"]: (row["count"], row["percent"]) for row in data["statuses"] if row["count"]}


@mock.patch("django.utils.timezone.now", return_value=NOW)
class StatusesTest(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(admin)
        # November: 2 pending, 1 confirmed, 1 canceled (the last one on the 1st, 00:00)
        make_order(datetime(2026, 11, 3, 10), Order.PENDING)
        make_order(datetime(2026, 11, 19, 23, 59), Order.PENDING)
        make_order(datetime(2026, 11, 5), Order.CONFIRMED)
        make_order(datetime(2026, 11, 1), Order.CANCELED)
        # October: 1 completed (last minute of the month); September: 1 completed; 2025: 1 delivering
        make_order(datetime(2026, 10, 31, 23, 59), Order.COMPLETED)
        make_order(datetime(2026, 9, 15), Order.COMPLETED)
        make_order(datetime(2025, 11, 30), Order.DELIVERING)

    def get(self, **params):
        response = self.client.get(ORDERS_URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_current_month_default(self, _):
        data = self.get()
        self.assertEqual((data["period"], data["date_from"], data["date_to"]), ("current_month", "2026-11-01", "2026-11-20"))
        self.assertEqual(data["total"], 4)
        self.assertEqual(counts(data), {Order.PENDING: (2, 50.0), Order.CONFIRMED: (1, 25.0), Order.CANCELED: (1, 25.0)})
        self.assertEqual([row["status"] for row in data["statuses"]], list(range(7)))

    def test_periods(self, _):
        data = self.get(period="last_month")
        self.assertEqual((data["date_from"], data["date_to"], data["total"]), ("2026-10-01", "2026-10-31", 1))
        data = self.get(period="last_3_months")
        self.assertEqual((data["date_from"], data["total"]), ("2026-09-01", 6))
        self.assertEqual(counts(data)[Order.COMPLETED], (2, 33.3))
        data = self.get(period="year")
        self.assertEqual((data["date_from"], data["total"]), ("2025-12-01", 6))

    def test_custom_range_matches_orders_list(self, _):
        data = self.get(date_from="2025-11-30", date_to="2026-10-31", period="last_month")
        self.assertEqual((data["period"], data["total"]), ("custom", 3))
        listed = self.client.get("/api/v1/admin/orders/", {"from_created": "2025-11-30", "to_created": "2026-10-31"})
        self.assertEqual(listed.json()["count"], data["total"])

    def test_bad_range(self, _):
        self.assertEqual(self.client.get(ORDERS_URL, {"date_from": "2026-11-01"}).status_code, 400)
        self.assertEqual(self.client.get(ORDERS_URL, {"date_from": "2026-11-02", "date_to": "2026-11-01"}).status_code, 400)

    def test_empty(self, _):
        Order.objects.all().delete()
        data = self.get()
        self.assertEqual(data["total"], 0)
        self.assertTrue(all(row["count"] == 0 and row["percent"] == 0 for row in data["statuses"]))

    def test_products(self, _):
        for publish_status, is_active, n in (("draft", True, 3), ("draft", False, 1), ("review", True, 1),
                                             ("published", True, 2), ("published", False, 1)):
            for i in range(n):
                Product.objects.create(name=f"{publish_status} {is_active} {i}", publish_status=publish_status,
                                       is_active=is_active)
        response = self.client.get(PRODUCTS_URL)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["total"], 8)
        self.assertEqual([(r["publish_status"], r["count"], r["percent"]) for r in data["publish_statuses"]],
                         [("draft", 4, 50.0), ("review", 1, 12.5), ("published", 3, 37.5)])
        self.assertEqual([(r["is_active"], r["count"], r["percent"]) for r in data["activity"]],
                         [(True, 6, 75.0), (False, 2, 25.0)])
        listed = self.client.get("/api/v1/admin/products/", {"publish_status": "review"}).json()["count"]
        self.assertEqual(listed, 1)
