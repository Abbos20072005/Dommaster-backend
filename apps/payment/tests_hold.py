"""Atmos card payment flow (BLD-486): hold/create leaves the order Pending, the admin panel charges the hold when
the order leaves Pending and releases it on cancel, the client charge / cancel only work on the customer's own
order. Atmos is mocked. Run: env/Scripts/python.exe manage.py test apps.payment.tests_hold"""
import os
from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.authorization.models import CustomerAddresses
from apps.payment.models import AtmosTransaction, CustomerCard
from apps.payment.services_pay.auth_services import AtmosAuthService, AtmosHoldService
from apps.service.models import Order, OrderOutboxEvent
from apps.service.tests import ApiTestCase, make_customer, make_item_category, make_order, make_product

ATMOS_ENV = {"ATMOS_HOLD_DURATION": "60", "ATMOS_STORE_ID": "1"}
OK = {"result": {"code": "OK"}}
CHARGED = {"result": {"code": "OK"}, "ofd_url": "https://ofd2.atmos.uz/api/ofd/x",
           "store_transaction": {"trans_id": 5, "success_trans_id": 6, "amount": 100000, "store": {"id": 1}}}
REFUSED = {"result": {"code": "STPIMS-ERR-092", "description": "Hold expired"}}


class HoldFlowTests(ApiTestCase):
    def setUp(self):
        patcher = mock.patch.object(AtmosAuthService, "get_access_token", return_value="t")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.customer = make_customer("+998900000401")
        self.client = self.client_for(self.customer)
        CustomerCard.objects.create(user=self.customer, card_id="1", token="tok", is_active=True, is_default=True)
        _, item_category = make_item_category("Cement")
        self.product = make_product("P1", item_category, 1000)
        address = CustomerAddresses.objects.create(customer=self.customer, name="Uy")
        self.order, _ = make_order(self.customer, [(self.product, 2)], total_price=2000, order_location=address)
        self.admin = APIClient()
        self.admin.force_authenticate(get_user_model().objects.create_user("admin", password="x", is_staff=True))

    def hold(self):
        with mock.patch.dict(os.environ, ATMOS_ENV), \
                mock.patch.object(AtmosHoldService, "create_hold", return_value={**OK, "hold_id": 77}), \
                mock.patch.object(AtmosHoldService, "apply_hold", return_value=OK):
            response = self.client.post("/payment/hold/create/", {"order_id": self.order.id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()

    def set_status(self, status, **extra):
        return self.admin.patch(f"/api/v1/admin/orders/{self.order.id}/", {"status": status, **extra}, format="json")

    def test_hold_keeps_the_order_pending(self):
        self.hold()
        self.assertEqual(self.order.status, Order.PENDING)
        self.assertEqual(self.order.payment_status, 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 100)

    def test_confirm_charges_the_hold(self):
        self.hold()
        with mock.patch.object(AtmosHoldService, "charge_hold", return_value=CHARGED) as charge:
            # the panel sends the old payment status back with the form - it must not undo the charge
            response = self.set_status(Order.CONFIRMED, payment_status=1)
        self.assertEqual(response.status_code, 200, response.data)
        charge.assert_called_once_with(access_token="t", hold_id=77)
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status), (Order.CONFIRMED, 2))
        self.assertEqual(self.order.ofd_url, CHARGED["ofd_url"])
        self.assertEqual(AtmosTransaction.objects.get(order=self.order).trans_id, 5)

        # paid already: the next statuses charge nothing
        with mock.patch.object(AtmosHoldService, "charge_hold") as charge:
            self.assertEqual(self.set_status(Order.COLLECTING).status_code, 200)
        charge.assert_not_called()

    def test_refused_charge_keeps_the_status(self):
        self.hold()
        with mock.patch.object(AtmosHoldService, "charge_hold", return_value=REFUSED):
            response = self.set_status(Order.CONFIRMED)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Hold expired", str(response.data["status"]))
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status), (Order.PENDING, 1))

    def test_skipping_confirmed_charges_too(self):
        self.hold()
        with mock.patch.object(AtmosHoldService, "charge_hold", return_value=CHARGED) as charge:
            self.assertEqual(self.set_status(Order.COLLECTING).status_code, 200)
        charge.assert_called_once()
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status), (Order.COLLECTING, 2))

    def test_cancel_releases_the_hold(self):
        self.hold()
        with mock.patch.object(AtmosHoldService, "cancel_hold", return_value=OK) as cancel, \
                mock.patch.object(AtmosHoldService, "charge_hold") as charge, \
                self.captureOnCommitCallbacks():
            self.assertEqual(self.set_status(Order.CANCELED).status_code, 200)
        cancel.assert_called_once()
        charge.assert_not_called()
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status), (Order.CANCELED, 3))
        self.assertTrue(OrderOutboxEvent.objects.filter(order=self.order, event_type="order.refunded").exists())

    def test_order_without_hold_is_not_sent_to_atmos(self):
        with mock.patch.object(AtmosHoldService, "charge_hold") as charge:
            self.assertEqual(self.set_status(Order.CONFIRMED).status_code, 200)
        charge.assert_not_called()

    def test_client_charge_and_cancel_only_own_order(self):
        self.hold()
        stranger = self.client_for(make_customer("+998900000402"))
        with mock.patch.object(AtmosHoldService, "charge_hold") as charge, \
                mock.patch.object(AtmosHoldService, "cancel_hold") as cancel:
            self.assertEqual(stranger.post("/payment/hold/charge/", {"order_id": self.order.id},
                                           format="json").status_code, 404)
            self.assertEqual(stranger.post("/payment/hold/cancel/", {"order_id": self.order.id},
                                           format="json").status_code, 404)
        charge.assert_not_called()
        cancel.assert_not_called()

    def test_client_charge_does_not_move_the_status(self):
        self.hold()
        with mock.patch.object(AtmosHoldService, "charge_hold", return_value=CHARGED):
            response = self.client.post("/payment/hold/charge/", {"order_id": self.order.id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status), (Order.PENDING, 2))
