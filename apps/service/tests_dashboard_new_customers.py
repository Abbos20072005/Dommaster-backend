"""Admin dashboard new customers per month (`dashboard/new-customers/`).
Run: manage.py test apps.service.tests_dashboard_new_customers"""
from datetime import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authorization.models import Customer, FcmToken

URL = "/api/v1/admin/dashboard/new-customers/"
CUSTOMERS_URL = "/api/v1/admin/customers/"
NOW = datetime(2026, 11, 20, 12, 0)
phones = iter(range(100))


def make_customer(created, channel=None, verified=True, fcm=False, deleted=False):
    customer = Customer.objects.create(phone_number=f"+9989012345{next(phones):02d}", verified=verified,
                                       registration_channel=channel, is_deleted=deleted)
    Customer.objects.filter(pk=customer.pk).update(created_at=created)
    if fcm:
        FcmToken.objects.create(customer=customer, device_id=f"d{customer.pk}", fcm_token="t")
    return customer


@mock.patch("django.utils.timezone.now", return_value=NOW)
class NewCustomersTest(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(admin)
        # November: ios, android, site, unknown + push token (app), unknown without one (site)
        make_customer(datetime(2026, 11, 1), Customer.Platform.IOS)
        make_customer(datetime(2026, 11, 19, 23, 59), Customer.Platform.ANDROID)
        make_customer(datetime(2026, 11, 5), Customer.Platform.SITE, fcm=True)
        make_customer(datetime(2026, 11, 6), fcm=True)
        make_customer(datetime(2026, 11, 7))
        # left out: OTP never confirmed, deleted
        make_customer(datetime(2026, 11, 8), Customer.Platform.IOS, verified=False)
        make_customer(datetime(2026, 11, 9), Customer.Platform.IOS, deleted=True)
        # October last minute (site), June (app), 2025-01 (site) - outside 12 months
        make_customer(datetime(2026, 10, 31, 23, 59), Customer.Platform.SITE)
        make_customer(datetime(2026, 6, 1), Customer.Platform.ANDROID)
        make_customer(datetime(2025, 1, 15), Customer.Platform.SITE)

    def get(self, **params):
        response = self.client.get(URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_default_12_months(self, _):
        data = self.get()
        self.assertEqual((data["period"], data["date_from"], data["date_to"]), ("12_months", "2025-12-01", "2026-11-20"))
        self.assertEqual(len(data["months"]), 12)
        self.assertEqual((data["total"], data["app"], data["site"]), (7, 4, 3))
        by_month = {m["month"]: (m["total"], m["app"], m["site"]) for m in data["months"]}
        self.assertEqual(by_month["2026-11-01"], (5, 3, 2))
        self.assertEqual(by_month["2026-10-01"], (1, 0, 1))
        self.assertEqual(by_month["2026-06-01"], (1, 1, 0))
        self.assertEqual(by_month["2026-07-01"], (0, 0, 0))

    def test_6_months(self, _):
        data = self.get(period="6_months")
        self.assertEqual([m["month"] for m in data["months"]][0], "2026-06-01")
        self.assertEqual((data["total"], data["app"], data["site"]), (7, 4, 3))

    def test_all_time(self, _):
        data = self.get(period="all_time")
        self.assertEqual((data["date_from"], len(data["months"])), ("2025-01-01", 23))
        self.assertEqual((data["total"], data["site"]), (8, 4))

    def test_all_time_empty(self, _):
        Customer.objects.all().delete()
        data = self.get(period="all_time")
        self.assertEqual((data["date_from"], data["total"], len(data["months"])), ("2026-11-01", 0, 1))

    def test_bad_period(self, _):
        self.assertEqual(self.client.get(URL, {"period": "week"}).status_code, 400)

    def test_matches_customers_list(self, _):
        month = next(m for m in self.get()["months"] if m["month"] == "2026-11-01")
        response = self.client.get(CUSTOMERS_URL, {"from_created": "2026-11-01", "to_created": "2026-11-30",
                                                   "verified": "true"})
        self.assertEqual(response.json()["count"], month["total"])
