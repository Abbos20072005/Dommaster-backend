"""Admin dashboard order stage times (`dashboard/order-stages/`) and the order status log.
Run: manage.py test apps.service.tests_order_stages"""
from datetime import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.service.models import Order, OrderStatusChange

URL = "/api/v1/admin/dashboard/order-stages/"
NOW = datetime(2026, 11, 2, 12, 0)
HOUR, DAY = 3600, 86400


def make_order(created, steps, delivery_type=Order.DELIVERY):
    """Order created at `created` that went through `steps` = [(status, at), ...]; the log gets these times."""
    order = Order.objects.create(delivery_type=delivery_type)
    for status, _ in steps:
        order.status = status
        order.save(update_fields=["status"])
    Order.objects.filter(pk=order.pk).update(created_at=created)
    rows = list(OrderStatusChange.objects.filter(order=order).order_by("id"))
    for row, at in zip(rows, [created, *(at for _, at in steps)]):
        OrderStatusChange.objects.filter(pk=row.pk).update(created_at=at)
    return order


def empty():
    return {"avg_seconds": None, "median_seconds": None, "count": 0}


def stat(avg, med, count):
    return {"avg_seconds": avg, "median_seconds": med, "count": count}


@mock.patch("django.utils.timezone.now", return_value=NOW)
class OrderStagesTest(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(admin)
        C, P, D, CO, X = Order.CONFIRMED, Order.COLLECTING, Order.DELIVERING, Order.COMPLETED, Order.CANCELED
        # A courier: confirm 1 h, to preparing 2 h, delivery 2 days
        make_order(datetime(2026, 10, 1, 10), [(C, datetime(2026, 10, 1, 11)), (P, datetime(2026, 10, 1, 13)),
                                               (D, datetime(2026, 10, 2, 9)), (CO, datetime(2026, 10, 3, 10))])
        # B courier: 3 h, 1 h, 1 day
        make_order(datetime(2026, 10, 5), [(C, datetime(2026, 10, 5, 3)), (P, datetime(2026, 10, 5, 4)),
                                           (CO, datetime(2026, 10, 6))])
        # C pickup: confirmed in October (1 h), collecting + completed in November (12 days, 13 days)
        make_order(datetime(2026, 10, 20), [(C, datetime(2026, 10, 20, 1)), (P, datetime(2026, 11, 1, 1)),
                                            (CO, datetime(2026, 11, 2))], delivery_type=Order.PICKUP)
        # D courier: completed without the confirm / collecting stages -> delivery only (1 day, September)
        make_order(datetime(2026, 9, 10), [(CO, datetime(2026, 9, 11))])
        # E canceled -> nowhere
        make_order(datetime(2026, 10, 1), [(C, datetime(2026, 10, 1, 1)), (X, datetime(2026, 10, 1, 2))])
        # F confirmed twice -> the first time counts (2 h)
        make_order(datetime(2026, 10, 10), [(C, datetime(2026, 10, 10, 2)), (Order.PENDING, datetime(2026, 10, 10, 3)),
                                            (C, datetime(2026, 10, 10, 5))])
        # G confirmed in August (outside the quarter), collecting on 1 September -> to preparing 31 days
        make_order(datetime(2026, 8, 1), [(C, datetime(2026, 8, 1, 1)), (P, datetime(2026, 9, 1, 1))])

    def get(self, **params):
        response = self.client.get(URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        return {row["month"]: row for row in response.json()["months"]}

    def test_quarter_all(self, _):
        months = self.get()
        self.assertEqual(list(months), ["2026-09", "2026-10", "2026-11"])
        self.assertEqual(months["2026-09"]["confirm"], empty())
        self.assertEqual(months["2026-09"]["to_preparing"], stat(31 * DAY, 31 * DAY, 1))
        self.assertEqual(months["2026-09"]["delivery"], stat(DAY, DAY, 1))
        # A 1 h, B 3 h, C 1 h, F 2 h: avg 7 h / 4, median (1 h + 2 h) / 2
        self.assertEqual(months["2026-10"]["confirm"], stat(6300, 5400, 4))
        self.assertEqual(months["2026-10"]["to_preparing"], stat(5400, 5400, 2))  # A 2 h, B 1 h
        self.assertEqual(months["2026-10"]["delivery"], stat(129600, 129600, 2))  # A 2 days, B 1 day
        self.assertEqual(months["2026-11"]["confirm"], empty())
        self.assertEqual(months["2026-11"]["to_preparing"], stat(12 * DAY, 12 * DAY, 1))
        self.assertEqual(months["2026-11"]["delivery"], stat(13 * DAY, 13 * DAY, 1))

    def test_delivery_method(self, _):
        pickup = self.get(delivery_method="pickup")
        self.assertEqual(pickup["2026-09"], {"month": "2026-09", "confirm": empty(), "to_preparing": empty(),
                                             "delivery": empty()})
        self.assertEqual(pickup["2026-10"]["confirm"], stat(HOUR, HOUR, 1))
        self.assertEqual(pickup["2026-10"]["delivery"], empty())
        self.assertEqual(pickup["2026-11"]["delivery"], stat(13 * DAY, 13 * DAY, 1))
        courier = self.get(delivery_method="courier")
        self.assertEqual(courier["2026-10"]["confirm"], stat(7200, 7200, 3))  # A 1 h, B 3 h, F 2 h
        self.assertEqual(courier["2026-11"]["delivery"], empty())

    def test_year(self, _):
        months = self.get(period="year")
        self.assertEqual(len(months), 12)
        self.assertEqual(next(iter(months)), "2025-12")
        self.assertEqual(months["2026-08"]["confirm"], stat(HOUR, HOUR, 1))  # G

    def test_bad_params_and_auth(self, _):
        self.assertEqual(self.client.get(URL, {"period": "week"}).status_code, 400)
        self.assertEqual(self.client.get(URL, {"delivery_method": "car"}).status_code, 400)
        self.assertIn(APIClient().get(URL).status_code, (401, 403))

    def test_status_log(self, _):
        order = Order.objects.create()
        order.status = Order.CONFIRMED
        order.save()
        order.save()  # no change -> no row
        self.assertEqual(list(order.status_changes.values_list("from_status", "to_status")),
                         [(None, Order.PENDING), (Order.PENDING, Order.CONFIRMED)])
