"""Admin dashboard `all_time` KPI cards vs the period `summary` cards.
Run: manage.py test apps.service.tests_dashboard_all_time"""
from datetime import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authorization.models import Customer
from apps.service.models import Order

URL = "/api/v1/admin/dashboard/"
NOW = datetime(2026, 11, 2, 12, 0)


def make_order(created, status, total):
    order = Order.objects.create()
    Order.objects.filter(pk=order.pk).update(created_at=created, status=status, total_price=total)


def make_customer(phone, created):
    customer = Customer.objects.create(phone_number=phone, full_name=phone)
    Customer.objects.filter(pk=customer.pk).update(created_at=created)


@mock.patch("django.utils.timezone.now", return_value=NOW)
class DashboardAllTimeTest(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(admin)
        # inside the last 30 days: completed 100 + 300, canceled 1000, pending 50
        make_order(datetime(2026, 10, 20), Order.COMPLETED, 100)
        make_order(datetime(2026, 11, 1), Order.COMPLETED, 300)
        make_order(datetime(2026, 10, 25), Order.CANCELED, 1000)
        make_order(datetime(2026, 11, 2, 9), Order.PENDING, 50)
        # older: completed 800, canceled 700 (the first order)
        make_order(datetime(2026, 3, 5), Order.COMPLETED, 800)
        make_order(datetime(2025, 12, 31, 23), Order.CANCELED, 700)
        make_customer("998900000001", datetime(2026, 10, 30))
        make_customer("998900000002", datetime(2025, 6, 1))
        make_customer("998900000003", datetime(2024, 1, 1))

    def get(self, query=""):
        response = self.client.get(URL + query)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_all_time(self, _):
        self.assertEqual(self.get()["all_time"], {
            "date_from": "2025-12-31",
            "date_to": "2026-11-02",
            "orders": 6,  # every created order, canceled too
            "revenue": 1200.0,  # completed only: 100 + 300 + 800
            "average_check": 400.0,
            "new_customers": 3,
        })

    def test_same_rule_as_the_period_cards(self, _):
        data = self.get("?days=30")
        summary, total = data["summary"], data["all_time"]
        self.assertEqual(summary["orders"]["value"], 4)
        self.assertEqual(summary["revenue"]["value"], 400.0)
        self.assertEqual(summary["average_check"]["value"], 200.0)
        self.assertEqual(summary["new_customers"]["value"], 1)
        for key in ("orders", "revenue", "new_customers"):
            self.assertGreaterEqual(total[key], summary[key]["value"])

    def test_params_do_not_change_it(self, _):
        expected = self.get()["all_time"]
        for query in ("?days=7", "?date_from=2026-01-01&date_to=2026-01-31", "?period=year", "?months=3"):
            self.assertEqual(self.get(query)["all_time"], expected, query)

    def test_no_orders(self, _):
        Order.objects.all().delete()
        Customer.objects.all().delete()
        self.assertEqual(self.get()["all_time"], {
            "date_from": None, "date_to": "2026-11-02",
            "orders": 0, "revenue": 0.0, "average_check": 0.0, "new_customers": 0,
        })
