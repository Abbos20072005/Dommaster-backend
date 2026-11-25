"""IKPU (MXIK) codes: product card format + log, copy to the order item, a pending order's item code goes to the
product card, an order leaves Pending only when every item has a code. Run: env/Scripts/python.exe manage.py test
apps.service.tests_ikpu"""
from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.authorization.models import CustomerAddresses
from apps.base.admin_actions import status_collecting
from apps.service.models import Cart, CartItem, Order, ProductCodeChange
from apps.service.tests import TEST_IKPU, ApiTestCase, make_customer, make_item_category, make_order, make_product
from exceptions.error_exception import CustomApiException

NEW = "10202001001000002"
NEWER = "10202001001000003"


class IkpuTests(ApiTestCase):
    def setUp(self):
        self.customer = make_customer("+998900000601")
        self.address = CustomerAddresses.objects.create(customer=self.customer, name="Uy", is_default=True)
        _, item_category = make_item_category("C")
        self.bare = make_product("P1", item_category, 1000, ikpu_code="")
        self.coded = make_product("P2", item_category, 2000)
        self.user = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        self.admin = APIClient()
        self.admin.force_authenticate(self.user)

    def order(self, *products, status=Order.PENDING):
        order, items = make_order(self.customer, [(product, 1) for product in products], order_location=self.address)
        Order.objects.filter(pk=order.pk).update(status=status)
        order.refresh_from_db()
        return order, items

    def set_status(self, order, status):
        return self.admin.patch(f"/api/v1/admin/orders/{order.id}/", {"status": status}, format="json")

    def set_codes(self, order, *rows):
        return self.admin.patch(f"/api/v1/admin/orders/{order.id}/ikpu/",
                                {"items": [{"id": item.id, "ikpu_code": code} for item, code in rows]}, format="json")

    def test_product_card_format_and_log(self):
        url = f"/api/v1/admin/products/{self.bare.id}/"
        for bad in ("1020200100100000a", "1020200100100000", "102020010010000022", "abc"):
            response = self.admin.patch(url, {"ikpu_code": bad}, format="json")
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn("ikpu_code", response.data)
        self.assertEqual(self.admin.patch(url, {"package_code": "15a"}, format="json").status_code, 400)
        self.assertFalse(ProductCodeChange.objects.exists())

        response = self.admin.patch(url, {"ikpu_code": NEW, "package_code": "1500594"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["ikpu_code"], response.data["package_code"]), (NEW, "1500594"))
        self.bare.refresh_from_db()
        self.assertEqual((self.bare.ikpu_code, self.bare.package_code), (NEW, "1500594"))
        rows = sorted(ProductCodeChange.objects.values_list("field", "old_value", "new_value", "source",
                                                            "changed_by", "order"))
        self.assertEqual(rows, [("ikpu_code", "", NEW, "product", self.user.id, None),
                                ("package_code", "", "1500594", "product", self.user.id, None)])
        # the same values again: nothing to log
        self.admin.patch(url, {"ikpu_code": NEW}, format="json")
        self.assertEqual(ProductCodeChange.objects.count(), 2)

        log = self.admin.get(f"/api/v1/admin/ikpu-changes/?product={self.bare.id}").data
        self.assertEqual(log["count"], 2)
        self.assertEqual(log["results"][0]["changed_by"]["username"], "admin")

    def test_ikpu_missing_filter(self):
        ids = lambda query: [row["id"] for row in self.admin.get(f"/api/v1/admin/products/?{query}").data["results"]]
        self.assertEqual(ids("ikpu_missing=true"), [self.bare.id])
        self.assertEqual(ids("ikpu_missing=false"), [self.coded.id])

    def test_checkout_copies_the_product_code(self):
        CartItem.objects.create(cart=Cart.objects.create(customer=self.customer), product=self.coded, quantity=1)
        response = self.client_for(self.customer).post(
            "/api/v1/order/", {"payment_type": 1, "delivery_price": "30000"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        item = Order.objects.get(id=response.data["order_id"]).order_items.get()
        self.assertEqual(item.ikpu_code, TEST_IKPU)

    def test_confirm_refused_while_an_item_has_no_code(self):
        order, (bare_item, _) = self.order(self.bare, self.coded)
        for status in (Order.CONFIRMED, Order.COLLECTING):
            response = self.set_status(order, status)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["missing_ikpu"],
                             [{"item_id": bare_item.id, "product": {"id": self.bare.id, "name": "P1"}}])
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PENDING)
        # cancelling needs no code
        self.assertEqual(self.set_status(order, Order.CANCELED).status_code, 200)

    def test_admin_create_refused_without_code(self):
        response = self.admin.post("/api/v1/admin/orders/", {
            "customer": {"id": self.customer.id}, "order_location": {"id": self.address.id},
            "items": [{"product": {"id": self.bare.id}, "quantity": 1}], "status": Order.CONFIRMED,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["missing_ikpu"], [{"item_id": None, "product": {"id": self.bare.id, "name": "P1"}}])
        self.assertFalse(Order.objects.exists())

    def test_other_ways_refused(self):
        order, _ = self.order(self.bare)
        # 1C status update and anything else that saves the order
        order.status = Order.COLLECTING
        with self.assertRaises(CustomApiException):
            order.save(update_fields=["status", "updated_at"])
        # django admin action (queryset.update)
        with mock.patch("apps.base.admin_actions.messages") as messages:
            status_collecting(None, None, Order.objects.filter(pk=order.pk))
        messages.error.assert_called_once()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PENDING)

    def test_item_code_goes_to_the_product_card(self):
        order, (bare_item, coded_item) = self.order(self.bare, self.coded)
        other_pending, (other_bare, _) = self.order(self.bare, self.coded)
        confirmed, (_, confirmed_coded) = self.order(self.bare, self.coded, status=Order.CONFIRMED)

        response = self.set_codes(order, (bare_item, NEW), (coded_item, NEWER))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["ikpu_code"] for item in response.data["items"]], [NEW, NEWER])
        self.bare.refresh_from_db()
        self.coded.refresh_from_db()
        self.assertEqual((self.bare.ikpu_code, self.coded.ikpu_code), (NEW, NEWER))
        # another pending order follows the card, a confirmed one keeps its code
        other_bare.refresh_from_db()
        confirmed_coded.refresh_from_db()
        self.assertEqual((other_bare.ikpu_code, confirmed_coded.ikpu_code), (NEW, TEST_IKPU))
        rows = sorted(ProductCodeChange.objects.values_list("product", "order", "old_value", "new_value", "source"))
        self.assertEqual(rows, sorted([(self.bare.id, order.id, "", NEW, "order"),
                                       (self.coded.id, order.id, TEST_IKPU, NEWER, "order")]))

        self.assertEqual(self.set_status(order, Order.CONFIRMED).status_code, 200)
        # a confirmed order's codes are fixed
        response = self.set_codes(order, (bare_item, NEWER))
        self.assertEqual(response.status_code, 400)
        bare_item.refresh_from_db()
        self.assertEqual(bare_item.ikpu_code, NEW)

    def test_item_codes_input(self):
        order, (bare_item,) = self.order(self.bare)
        foreign, (foreign_item,) = self.order(self.coded)
        self.assertEqual(self.set_codes(order, (bare_item, "123")).status_code, 400)
        self.assertEqual(self.set_codes(order, (bare_item, "")).status_code, 400)
        self.assertEqual(self.set_codes(order, (foreign_item, NEW)).status_code, 400)
        self.assertFalse(ProductCodeChange.objects.exists())

    def test_items_edit_keeps_the_code(self):
        order, (bare_item,) = self.order(self.bare)
        self.set_codes(order, (bare_item, NEW))
        response = self.admin.patch(f"/api/v1/admin/orders/{order.id}/", {
            "items": [{"product": {"id": self.bare.id}, "quantity": 3}, {"product": {"id": self.coded.id}, "quantity": 1}],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["ikpu_code"] for item in response.data["items"]], [NEW, TEST_IKPU])
