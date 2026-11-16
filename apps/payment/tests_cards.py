"""Atmos cards: default card after a delete / bind again, the card hold/create takes, a hold that fails to apply.
Atmos is mocked. Run: env/Scripts/python.exe manage.py test apps.payment.tests_cards"""
import os
from unittest import mock

from apps.payment.models import CustomerCard
from apps.payment.services_pay.auth_services import AtmosAuthService, AtmosBindWithCheckoutService, AtmosHoldService
from apps.service.models import Order
from apps.service.tests import ApiTestCase, make_customer

ATMOS_ENV = {"ATMOS_HOLD_DURATION": "60", "ATMOS_STORE_ID": "1"}


def atmos_card(card_id, token):
    return {"card_id": card_id, "card_token": token, "pan": "986035******3078", "card_holder": "TEST", "expiry": "2612"}


class CardTests(ApiTestCase):
    def setUp(self):
        self.customer = make_customer("+998900000301")
        self.client = self.client_for(self.customer)
        self.token_patch = mock.patch.object(AtmosAuthService, "get_access_token", return_value="t")
        self.token_patch.start()
        self.addCleanup(self.token_patch.stop)

    def bind(self, card_id, token):
        with mock.patch.object(AtmosBindWithCheckoutService, "get_cards_list",
                               return_value={"cardDataSmallList": [atmos_card(card_id, token)]}):
            response = self.client.post("/atmos/card-bind/callback/", {"card_id": card_id, "account": self.customer.id},
                                        format="json")
        self.assertEqual(response.status_code, 200)
        return CustomerCard.objects.get(card_id=str(card_id))

    def test_first_card_is_default_second_is_not(self):
        first = self.bind(1, "a")
        second = self.bind(2, "b")
        self.assertTrue(first.is_default)
        self.assertFalse(second.is_default)

    def test_card_bound_again_after_delete_is_default(self):
        card = self.bind(1, "a")
        self.assertEqual(self.client.delete(f"/customer/cards/{card.id}/").status_code, 204)
        card = self.bind(1, "a")
        self.assertTrue(card.is_active)
        self.assertTrue(card.is_default)

    def test_deleting_default_card_makes_the_other_default(self):
        first = self.bind(1, "a")
        second = self.bind(2, "b")
        self.client.delete(f"/customer/cards/{first.id}/")
        second.refresh_from_db()
        self.assertTrue(second.is_default)

    def hold(self, order):
        with mock.patch.dict(os.environ, ATMOS_ENV):
            return self.client.post("/payment/hold/create/", {"order_id": order.id}, format="json")

    def test_hold_takes_active_card_without_default_flag(self):
        CustomerCard.objects.create(user=self.customer, card_id="9", token="old", is_active=True, is_default=False)
        order = Order.objects.create(customer=self.customer, total_price=1000)
        with mock.patch.object(AtmosHoldService, "create_hold", return_value={"result": {"code": "ERR"}}) as create:
            response = self.hold(order)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(create.call_args.kwargs["card_token"], "old")

    def test_hold_failed_apply_saves_hold_id_and_cancels(self):
        self.bind(1, "a")
        order = Order.objects.create(customer=self.customer, total_price=1000)
        with mock.patch.object(AtmosHoldService, "create_hold", return_value={"result": {"code": "OK"}, "hold_id": 77}), \
                mock.patch.object(AtmosHoldService, "apply_hold",
                                  return_value={"result": {"code": "STPIMS-ERR-001"}}), \
                mock.patch.object(AtmosHoldService, "cancel_hold", return_value={"result": {"code": "OK"}}) as cancel:
            response = self.hold(order)
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.hold_id, 77)
        self.assertEqual(order.payment_status, 0)
        cancel.assert_called_once_with(access_token="t", hold_id=77, send_cancel_sms=False)
