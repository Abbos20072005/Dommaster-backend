"""Stores (pickup branches) and pickup orders. Run: env/Scripts/python.exe manage.py test apps.service"""
from datetime import datetime, timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authorization.api.v1.client.views import issue_customer_tokens
from apps.authorization.models import CustomerAddresses
from apps.base.models import MarketBranch
from apps.base.stores import clean_schedule, localized_snapshot, open_state
from apps.service.models import Cart, CartItem, Order, OrderOutboxEvent
from apps.service.models.choices import (
    ORDER_EVENT_CANCELED, ORDER_EVENT_PICKUP_DONE, ORDER_EVENT_PICKUP_EXPIRED, ORDER_EVENT_PICKUP_READY,
    ORDER_EVENT_PICKUP_SELECTED, OUTBOX_RECORDED,
)
from apps.service.pickup import expire_overdue_pickups
from apps.service.tests import ApiTestCase, make_customer, make_item_category, make_product, make_order
from apps.service.utils import build_order_caption, build_order_data

MONDAY = datetime(2026, 10, 19)


def week(open_time="09:00", close_time="20:00", closed=(6,)):
    return [{"day": day, "is_open": day not in closed,
             "open_time": None if day in closed else open_time,
             "close_time": None if day in closed else close_time} for day in range(7)]


def make_store(name="Chilonzor", **fields):
    data = {"name": name, "name_ru": name, "name_uz": name, "address_ru": "Бунёдкор 1",
            "address_uz": "Bunyodkor 1", "phone_number": "+998901234567",
            "latitude": 41.28, "longitude": 69.2, "schedule": week(), "branch_type": 1, **fields}
    return MarketBranch.objects.create(**data)


def store_payload(**fields):
    return {"name_uz": "Yunusobod", "name_ru": "Юнусабад", "address_uz": "Amir Temur 1",
            "address_ru": "Амир Темур 1",
            "phone_number": "+998901234567", "latitude": 41.36, "longitude": 69.29, "schedule": week(), **fields}


class ScheduleTests(TestCase):
    def test_clean_schedule(self):
        rows = clean_schedule(list(reversed(week(open_time="09:00:00"))))
        self.assertEqual([row["day"] for row in rows], list(range(7)))
        self.assertEqual(rows[0]["open_time"], "09:00")
        self.assertEqual(rows[6], {"day": 6, "is_open": False, "open_time": None, "close_time": None})

    def test_close_before_open_refused(self):
        with self.assertRaisesMessage(ValidationError, "Day 0: the closing time must be after the opening time"):
            clean_schedule(week(open_time="20:00", close_time="09:00"))
        with self.assertRaises(ValidationError):
            clean_schedule(week()[:6])
        with self.assertRaises(ValidationError):
            clean_schedule(week(open_time="9:00"))

    def test_open_state(self):
        schedule = week()
        self.assertEqual(open_state(schedule, MONDAY.replace(hour=10)),
                         {"is_open_now": True, "closes_at": "20:00", "next_open": None})
        self.assertEqual(open_state(schedule, MONDAY.replace(hour=20))["next_open"],
                         {"day": 1, "time": "09:00", "date": "2026-10-20"})
        self.assertEqual(open_state(schedule, MONDAY.replace(hour=8))["next_open"]["date"], "2026-10-19")
        sunday = MONDAY + timedelta(days=6, hours=12)
        self.assertEqual(open_state(schedule, sunday)["next_open"], {"day": 0, "time": "09:00", "date": "2026-10-26"})


class BranchAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_admin_only(self):
        self.assertIn(APIClient().get("/api/v1/admin/branches/").status_code, (401, 403))
        customer_client = APIClient()
        access, _ = issue_customer_tokens(make_customer("+998900000101"))
        customer_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertIn(customer_client.post("/api/v1/admin/branches/", store_payload(), format="json").status_code,
                      (401, 403))

    def test_create(self):
        response = self.client.post("/api/v1/admin/branches/",
                                    store_payload(schedule=list(reversed(week(open_time="09:00:00")))), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        store = MarketBranch.objects.get(id=response.data["id"])
        self.assertEqual((store.name, store.is_active, store.schedule[0]["open_time"]), ("Юнусабад", True, "09:00"))
        self.assertEqual(response.data["schedule"][6]["is_open"], False)

        # a branch of 1C sent without a schedule gets the default one
        response = self.client.post("/api/v1/admin/branches/", {"name_ru": "Склад", "branch_type": 2}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["schedule"]), 7)

    def test_validation(self):
        response = self.client.post("/api/v1/admin/branches/", store_payload(latitude=55.75, longitude=37.61),
                                    format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {"latitude", "longitude"})

        response = self.client.post("/api/v1/admin/branches/", store_payload(schedule=week("18:00", "09:00")),
                                    format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("closing time must be after", str(response.data["schedule"]))

        response = self.client.post("/api/v1/admin/branches/", store_payload(name_ru=""), format="json")
        self.assertEqual(response.status_code, 400)

    def test_store_with_orders_is_not_deleted(self):
        store = make_store()
        make_order(make_customer("+998900000102"), [], delivery_type=Order.PICKUP, pickup_branch=store)
        response = self.client.delete(f"/api/v1/admin/branches/{store.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(MarketBranch.objects.filter(id=store.id).exists())
        self.assertEqual(self.client.get(f"/api/v1/admin/branches/{store.id}/").data["orders_count"], 1)
        self.assertEqual(self.client.patch(f"/api/v1/admin/branches/{store.id}/", {"is_active": False},
                                           format="json").status_code, 200)

        empty = make_store("Bo'sh")
        self.assertEqual(self.client.delete(f"/api/v1/admin/branches/{empty.id}/").status_code, 204)


class StorePublicTests(TestCase):
    def test_list(self):
        second = make_store("B", position=2)
        first = make_store("A", position=1, name_uz="", address_uz="")
        make_store("Off", is_active=False)
        make_store("Warehouse", branch_type=2)
        with mock.patch("django.utils.timezone.now", return_value=MONDAY.replace(hour=10)):
            response = APIClient().get("/api/v1/base/stores/", HTTP_ACCEPT_LANGUAGE="uz")
        self.assertEqual(response.status_code, 200)
        result = response.data["result"]
        self.assertEqual([row["id"] for row in result], [first.id, second.id])
        # empty uz texts fall back to ru, a filled one is served in uz
        self.assertEqual((result[0]["name"], result[0]["address"]), ("A", "Бунёдкор 1"))
        self.assertEqual(result[1]["address"], "Bunyodkor 1")
        self.assertEqual((result[0]["is_open_now"], result[0]["closes_at"]), (True, "20:00"))
        self.assertEqual(len(result[0]["schedule"]), 7)

    def test_inactive_detail_is_404(self):
        store = make_store(is_active=False)
        self.assertEqual(APIClient().get(f"/api/v1/base/stores/{store.id}/").status_code, 404)


class PickupCheckoutTests(ApiTestCase):
    def setUp(self):
        self.customer = make_customer("+998900000103")
        _, item_category = make_item_category("C")
        self.product = make_product("P1", item_category, 100000)
        self.store = make_store()
        cart = Cart.objects.create(customer=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

    def checkout(self, **data):
        return self.client_for(self.customer).post("/api/v1/order/", {
            "payment_type": 1, "delivery_type": 1, "branch_id": self.store.id, "delivery_price": "30000", **data,
        }, format="json")

    def test_pickup_without_address(self):
        response = self.checkout()
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(id=response.data["order_id"])
        self.assertEqual((order.order_location, order.delivery_price, order.total_price), (None, 0, 200000.0))
        self.assertEqual(order.pickup_branch, self.store)
        self.assertEqual(order.pickup_store_snapshot["name_ru"], "Chilonzor")
        self.assertTrue(OrderOutboxEvent.objects.filter(order=order, event_type=ORDER_EVENT_PICKUP_SELECTED,
                                                        status=OUTBOX_RECORDED).exists())

        MarketBranch.objects.filter(id=self.store.id).update(name_ru="Renamed", phone_number="+998900000000",
                                                             is_active=False)
        detail = self.client_for(self.customer).get(f"/api/v1/order/{order.id}/").data["result"]
        self.assertEqual((detail["pickup_store"]["name"], detail["pickup_store"]["phone"]),
                         ("Chilonzor", "+998901234567"))

    def test_rules(self):
        response = self.checkout(payment_type=4, payment_method="cash")
        self.assertEqual(response.status_code, 400)
        self.assertIn("payment_type", str(response.data))

        self.assertEqual(self.checkout(branch_id=999999).status_code, 400)
        # a warehouse is not a store
        self.assertEqual(self.checkout(branch_id=make_store("Warehouse", branch_type=2).id).status_code, 400)
        MarketBranch.objects.filter(id=self.store.id).update(is_active=False)
        self.assertEqual(self.checkout().status_code, 400)
        self.assertFalse(Order.objects.exists())


class PickupStatusTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.customer = make_customer("+998900000104")
        _, item_category = make_item_category("C")
        self.product = make_product("P1", item_category, 100000)
        self.store = make_store()
        self.order, _ = make_order(self.customer, [(self.product, 1)], delivery_type=Order.PICKUP,
                                   pickup_branch=self.store, payment_type=1)

    def set_status(self, status, order=None):
        return self.client.patch(f"/api/v1/admin/orders/{(order or self.order).id}/", {"status": status},
                                 format="json")

    def test_ready_needs_collecting_pickup_order(self):
        self.assertEqual(self.set_status(Order.READY_FOR_PICKUP).status_code, 400)
        address = CustomerAddresses.objects.create(customer=self.customer, name="Uy")
        delivery, _ = make_order(self.customer, [(self.product, 1)], order_location=address)
        self.assertEqual(self.set_status(Order.COLLECTING, delivery).status_code, 200)
        self.assertEqual(self.set_status(Order.READY_FOR_PICKUP, delivery).status_code, 400)

    @mock.patch("apps.service.order_push.send_push_to_customer", return_value=1)
    @mock.patch("apps.service.order_push.run_in_background", side_effect=lambda task, *args: task(*args))
    def test_ready_then_done(self, _, push):
        self.assertEqual(self.set_status(Order.COLLECTING).status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.set_status(Order.READY_FOR_PICKUP)
        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.pickup_deadline - self.order.ready_for_pickup_at, timedelta(days=2))
        self.assertTrue(OrderOutboxEvent.objects.filter(order=self.order, event_type=ORDER_EVENT_PICKUP_READY).exists())

        customer_id, title, body = push.call_args.args
        self.assertEqual(customer_id, self.customer.id)
        self.assertIn("Chilonzor", body)
        self.assertIn(self.order.pickup_deadline.strftime("%d.%m.%Y %H:%M"), body)
        self.assertNotIn(self.customer.phone_number, body)
        data = push.call_args.kwargs["data"]
        self.assertEqual((data["status"], data["store_id"]), ("5", str(self.store.id)))

        # back to Collecting would take the stock twice
        self.assertEqual(self.set_status(Order.COLLECTING).status_code, 400)
        self.assertEqual(self.set_status(Order.COMPLETED).status_code, 200)
        self.assertTrue(OrderOutboxEvent.objects.filter(order=self.order, event_type=ORDER_EVENT_PICKUP_DONE).exists())

    def test_expired(self):
        past = timezone.now() - timedelta(days=3)
        Order.objects.filter(id=self.order.id).update(status=Order.READY_FOR_PICKUP, ready_for_pickup_at=past,
                                                      pickup_deadline=past + timedelta(days=2))
        with mock.patch("apps.service.outbox._deliver_in_background"):
            self.assertEqual(expire_overdue_pickups(), 1)
            self.assertEqual(expire_overdue_pickups(), 0)
        self.assertEqual(OrderOutboxEvent.objects.filter(event_type=ORDER_EVENT_PICKUP_EXPIRED).count(), 1)

        row = self.client.get("/api/v1/admin/orders/").data["results"][0]
        self.assertEqual((row["pickup_expired"], row["pickup_store"]["id"]), (True, self.store.id))
        self.assertEqual(self.client.get("/api/v1/admin/orders/?pickup_expired=true").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/v1/admin/orders/?pickup_branch={self.store.id}").data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/admin/orders/stats/").data["pickup_expired"], 1)

    def test_telegram_caption_shows_store(self):
        caption = build_order_caption(build_order_data(self.order))
        self.assertIn("Самовывоз: <b>Chilonzor</b>", caption)
        self.assertIn("Бунёдкор 1", caption)


class StockGuardTests(TestCase):
    """`Product.quantity` follows the status the order comes from (`signals.STOCK_TAKEN_STATUSES`), so a
    status an order already passed through never moves the stock twice."""

    def setUp(self):
        self.customer = make_customer("+998900000105")
        _, item_category = make_item_category("C")
        self.product = make_product("P1", item_category, 1000)  # quantity = 100
        self.order, _ = make_order(self.customer, [(self.product, 10)], delivery_type=Order.PICKUP,
                                   pickup_branch=make_store(), payment_type=1)

    def set_status(self, status):
        """The 1C / payment-callback way: a plain save, no admin validation."""
        self.order.status = status
        self.order.save(update_fields=["status", "updated_at"])

    def quantity(self):
        self.product.refresh_from_db()
        return self.product.quantity

    def test_stock_is_taken_once(self):
        self.set_status(Order.COLLECTING)
        self.assertEqual(self.quantity(), 90)
        self.set_status(Order.READY_FOR_PICKUP)
        self.assertEqual(self.quantity(), 90)
        # 1C re-sends "collecting" for the order waiting in the store
        self.set_status(Order.COLLECTING)
        self.assertEqual(self.quantity(), 90)
        # the same from Delivering and Completed
        for status in (Order.DELIVERING, Order.COMPLETED):
            self.set_status(status)
            self.set_status(Order.COLLECTING)
            self.assertEqual(self.quantity(), 90)

    def test_canceling_gives_the_stock_back_once(self):
        self.set_status(Order.COLLECTING)
        self.set_status(Order.CANCELED)
        self.assertEqual(self.quantity(), 100)
        # collecting it again takes the stock once more, cancelling gives it back again
        self.set_status(Order.COLLECTING)
        self.assertEqual(self.quantity(), 90)
        self.set_status(Order.CANCELED)
        self.assertEqual(self.quantity(), 100)

    def test_canceling_an_unpaid_order_does_not_invent_stock(self):
        # status 0: the stock was never taken (the customer never paid)
        self.set_status(Order.CANCELED)
        self.assertEqual(self.quantity(), 100)
        # the staff group still hears about the cancellation
        self.assertEqual(OrderOutboxEvent.objects.filter(order=self.order,
                                                         event_type=ORDER_EVENT_CANCELED).count(), 1)


class AddressTranslationTests(TestCase):
    """`MarketBranch.address` is translated: the order snapshot keeps both languages and the old single
    column is filled by `manage.py backfill_branch_address` (migration 0031 adds it empty)."""

    def test_snapshot_keeps_both_languages(self):
        customer = make_customer("+998900000106")
        _, item_category = make_item_category("C")
        product = make_product("P1", item_category, 1000)
        store = make_store()
        order, _ = make_order(customer, [(product, 1)], delivery_type=Order.PICKUP, pickup_branch=store)
        snapshot = order.pickup_store_snapshot
        self.assertEqual((snapshot["address_uz"], snapshot["address_ru"]), ("Bunyodkor 1", "Бунёдкор 1"))

        # the customer reads it in the request language, the ru one is the fallback
        client = APIClient()
        access, _ = issue_customer_tokens(customer)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        for language, expected in (("uz", "Bunyodkor 1"), ("ru", "Бунёдкор 1")):
            response = client.get(f"/api/v1/order/{order.id}/", HTTP_ACCEPT_LANGUAGE=language)
            self.assertEqual(response.data["result"]["pickup_store"]["address"], expected, language)

    def test_snapshot_written_before_the_address_became_translated(self):
        customer = make_customer("+998900000107")
        _, item_category = make_item_category("C")
        product = make_product("P1", item_category, 1000)
        order, _ = make_order(customer, [(product, 1)], delivery_type=Order.PICKUP, pickup_branch=make_store())
        # the old shape: one "address" key, no language
        old = {**order.pickup_store_snapshot, "address": "Старый адрес"}
        old.pop("address_uz"), old.pop("address_ru")
        Order.objects.filter(pk=order.pk).update(pickup_store_snapshot=old)
        self.assertEqual(localized_snapshot(old, "uz")["address"], "Старый адрес")

    def test_backfill_fills_the_language_column(self):
        store = make_store()
        # a branch as it is right after migrate: only the old column has the address
        with connection.cursor() as cursor:
            cursor.execute("UPDATE base_marketbranch SET address = %s, address_uz = NULL, address_ru = NULL "
                           "WHERE id = %s", ["Чиланзар 1", store.id])
        store.refresh_from_db()
        self.assertIsNone(store.address_ru)

        call_command("backfill_branch_address", "--dry-run")
        store.refresh_from_db()
        self.assertIsNone(store.address_ru, "a dry run changes nothing")

        call_command("backfill_branch_address")
        store.refresh_from_db()
        self.assertEqual((store.address_ru, store.address_uz), ("Чиланзар 1", None))

        # safe to run again: a branch that already has the ru address is left alone
        MarketBranch.objects.filter(id=store.id).update(address_ru="Исправлено")
        call_command("backfill_branch_address")
        store.refresh_from_db()
        self.assertEqual(store.address_ru, "Исправлено")
