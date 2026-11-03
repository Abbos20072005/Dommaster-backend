"""Product funnel events (`events/`, `cart/item/`) and the daily table. Run: env/Scripts/python.exe manage.py test apps.service"""
import uuid
from datetime import datetime, timedelta
from unittest import mock

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.service import funnel
from apps.service.models import Cart, CartItem, ProductEvent, ProductFunnelDaily
from apps.service.tests import ApiTestCase, make_customer, make_item_category, make_product

EVENTS = "/api/v1/events/"
BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"


@mock.patch("apps.service.funnel.run_in_background", side_effect=lambda task, *args: task(*args))
class FunnelEventTests(ApiTestCase):
    def setUp(self):
        _, item_category = make_item_category("Asboblar")
        self.drill = make_product("F1", item_category, 1000)
        self.hammer = make_product("F2", item_category, 2000)
        self.saw = make_product("F3", item_category, 3000)
        self.customer = make_customer("+998900000071")
        self.device = uuid.uuid4().hex
        cache.delete_many([f"funnel:{t}:c:{self.customer.id}:{p.id}"
                           for t in (ProductEvent.VIEW, ProductEvent.ADD_TO_CART, ProductEvent.CHECKOUT_START)
                           for p in (self.drill, self.hammer, self.saw)])

    def send(self, body, client=None, **headers):
        headers.setdefault("HTTP_USER_AGENT", BROWSER)
        with self.captureOnCommitCallbacks(execute=True):
            return (client or APIClient()).post(EVENTS, body, format="json", **headers)

    def guest_view(self, product, **headers):
        return self.send({"type": "product_view", "product_id": product.id, "platform": "site"},
                         HTTP_X_DEVICE_ID=self.device, **headers)

    def test_guest_view_is_recorded_with_platform_and_session(self, _):
        response = self.guest_view(self.drill)
        self.assertEqual(response.status_code, 200, response.data)
        event = ProductEvent.objects.get()
        self.assertEqual((event.event_type, event.product_id, event.platform, event.customer_id, event.session_id),
                         (ProductEvent.VIEW, self.drill.id, "site", None, self.device))

    def test_repeat_within_30_seconds_is_one_view(self, _):
        self.guest_view(self.drill)
        self.guest_view(self.drill)
        self.guest_view(self.hammer)
        self.assertEqual(ProductEvent.objects.filter(product=self.drill).count(), 1)
        self.assertEqual(ProductEvent.objects.count(), 2)

    def test_prefetch_is_not_counted(self, _):
        self.guest_view(self.drill, HTTP_SEC_PURPOSE="prefetch")
        self.guest_view(self.drill, HTTP_PURPOSE="prefetch")
        self.assertFalse(ProductEvent.objects.exists())

    def test_view_needs_product_and_platform(self, _):
        self.assertFalse(self.send({"type": "product_view", "platform": "site"}).data["ok"])
        self.assertFalse(self.send({"type": "product_view", "product_id": self.drill.id}).data["ok"])
        self.assertFalse(self.send({"type": "purchase", "platform": "site"}).data["ok"])
        self.assertFalse(ProductEvent.objects.exists())

    def test_checkout_start_records_checked_cart_items(self, _):
        cart, _created = Cart.objects.get_or_create(customer=self.customer)
        CartItem.objects.create(cart=cart, product=self.drill, quantity=1, is_checked=True)
        CartItem.objects.create(cart=cart, product=self.hammer, quantity=2, is_checked=True)
        CartItem.objects.create(cart=cart, product=self.saw, quantity=1, is_checked=False)

        self.send({"type": "checkout_start", "platform": "ios"}, self.client_for(self.customer))

        events = ProductEvent.objects.filter(event_type=ProductEvent.CHECKOUT_START)
        self.assertEqual(sorted(events.values_list("product_id", flat=True)), sorted([self.drill.id, self.hammer.id]))
        self.assertEqual(set(events.values_list("platform", "customer_id")), {("ios", self.customer.id)})

    def test_add_to_cart_is_recorded_by_the_cart_api(self, _):
        Cart.objects.get_or_create(customer=self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.customer).post(
                "/api/v1/cart/item/", {"product": self.drill.id, "quantity": 1, "platform": "android"},
                format="json", HTTP_USER_AGENT=BROWSER)
        self.assertTrue(response.data["ok"], response.data)
        event = ProductEvent.objects.get()
        self.assertEqual((event.event_type, event.product_id, event.platform, event.customer_id),
                         (ProductEvent.ADD_TO_CART, self.drill.id, "android", self.customer.id))


class FunnelDailyTests(ApiTestCase):
    def setUp(self):
        _, item_category = make_item_category("Asboblar")
        self.drill = make_product("D1", item_category, 1000)
        self.customer = make_customer("+998900000072")

    def event(self, when, event_type=ProductEvent.VIEW, platform="site", customer=None, session_id=""):
        event = ProductEvent.objects.create(event_type=event_type, product=self.drill, platform=platform,
                                            customer=customer, session_id=session_id)
        ProductEvent.objects.filter(pk=event.pk).update(created_at=when)

    def test_day_sums_up_per_platform(self):
        day = timezone.now().date() - timedelta(days=1)
        noon = datetime.combine(day, datetime.min.time()) + timedelta(hours=12)
        # site: 3 views by 2 viewers (customer twice + one session) + one without any id, 1 cart, 1 checkout
        self.event(noon, customer=self.customer)
        self.event(noon, customer=self.customer)
        self.event(noon, session_id="dev-1")
        self.event(noon)
        self.event(noon, ProductEvent.ADD_TO_CART, customer=self.customer)
        self.event(noon, ProductEvent.CHECKOUT_START, customer=self.customer)
        # app, and an event of the next day that is not in this one
        self.event(noon, platform="ios", session_id="dev-2")
        self.event(noon + timedelta(days=1))

        self.assertEqual(funnel.build_day(day), 2)
        self.assertEqual(funnel.build_day(day), 2)  # safe to run again

        site = ProductFunnelDaily.objects.get(date=day, platform="site")
        self.assertEqual((site.views, site.viewers, site.add_to_cart, site.checkout_start), (4, 2, 1, 1))
        ios = ProductFunnelDaily.objects.get(date=day, platform="ios")
        self.assertEqual((ios.views, ios.viewers, ios.add_to_cart, ios.checkout_start), (1, 1, 0, 0))

    def test_nightly_deletes_old_raw_events_only(self):
        now = timezone.now()
        self.event(now - timedelta(days=funnel.EVENT_DAYS + 2))
        self.event(now - timedelta(days=1))

        built, deleted = funnel.nightly()

        self.assertEqual((built, deleted), (1, 1))
        self.assertEqual(ProductEvent.objects.count(), 1)
