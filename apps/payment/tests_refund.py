"""Refund of an Atmos card payment (BLD-545): the admin panel refunds items / the delivery / everything, Atmos gets
a partial reversal with the refunded receipt lines (`ofd_items`), sums come from the charge receipt. Atmos is
mocked. Run: env/Scripts/python.exe manage.py test apps.payment.tests_refund"""
from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.payment.atmos_hold import DELIVERY_IKPU, charge_order_hold, receipt_lines
from apps.payment.models import AtmosRefund, AtmosTransaction
from apps.payment.services_pay.auth_services import AtmosAuthService, AtmosHoldService, AtmosTransactionService
from apps.service.models import Order, OrderComment, OrderOutboxEvent
from apps.service.tests import TEST_IKPU, ApiTestCase, make_customer, make_item_category, make_order, make_product

CREATED = {"result": {"code": "OK"}, "transaction_partial_reverse_id": 3}
CONFIRMED = {"result": {"code": "OK"}, "transaction_partial_reverse_id": 3, "transaction_reverted_amount": 90000,
             "transaction_left_amount": 1648000}
REFUSED = {"result": {"code": "STPIMS-ERR-133", "description": "Reverse not allowed"}}


class RefundTests(ApiTestCase):
    def setUp(self):
        patcher = mock.patch.object(AtmosAuthService, "get_access_token", return_value="t")
        patcher.start()
        self.addCleanup(patcher.stop)
        customer = make_customer("+998900000451")
        _, item_category = make_item_category("C")
        self.lamp = make_product("Lamp", item_category, 1000)
        self.lamp.package_code = "1500594"
        self.lamp.save()
        cable = make_product("Cable", item_category, 3000, ikpu_code="10202001001000002")
        # goods 2 x 1000 + 3000 = 5000, a promocode took 500 -> 4500 + delivery 12 880 = 17 380
        self.order, (self.lamp_item, self.cable_item) = make_order(
            customer, [(self.lamp, 2), (cable, 1)], total_price=17380, delivery_price=12880,
            status=Order.CONFIRMED, payment_status=2, hold_id=77, payment_type=0)
        self.charge = AtmosTransaction.objects.create(
            order=self.order, success_trans_id=6, trans_id=5, store_id=1, account="1", amount=1738000,
            confirmed=True, receipt_lines=receipt_lines(self.order))
        self.admin = APIClient()
        self.admin.force_authenticate(get_user_model().objects.create_user("admin", password="x", is_staff=True))
        self.url = f"/api/v1/admin/orders/{self.order.id}/refunds/"

    def refund(self, body, create=CREATED, confirm=CONFIRMED):
        with mock.patch.object(AtmosTransactionService, "create_partial_reverse", return_value=create) as c, \
                mock.patch.object(AtmosTransactionService, "confirm_partial_reverse", return_value=confirm) as f:
            response = self.admin.post(self.url, body, format="json")
        return response, c, f

    def available(self):
        response = self.admin.get(self.url + "available/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_available_lines(self):
        data = self.available()
        self.assertTrue(data["can_refund"])
        self.assertEqual((data["charged_amount"], data["refunded_amount"]), (1738000, 0))
        self.assertEqual([(line["item_id"], line["quantity"], line["amount"]) for line in data["lines"]],
                         [(self.lamp_item.id, 2, 180000), (self.cable_item.id, 1, 270000), (None, 1, 1288000)])

    def test_one_piece_goes_to_atmos_with_its_receipt_line(self):
        response, create, confirm = self.refund({"items": [{"item_id": self.lamp_item.id, "quantity": 1}],
                                                 "reason": "Brak"})
        self.assertEqual(response.status_code, 201, response.data)
        refund = AtmosRefund.objects.get()
        create.assert_called_once_with(access_token="t", transaction_id=6, store_id=1, amount=90000, reason="Brak",
                                       request_id=f"order-{self.order.id}-refund-{refund.id}")
        confirm.assert_called_once_with(
            access_token="t", transaction_id=6, transaction_partial_reverse_id=3, store_id=1,
            request_id=f"order-{self.order.id}-refund-{refund.id}",
            ofd_items=[{"ofd_code": TEST_IKPU, "name": "Lamp", "amount": 90000,
                        "details": [{"key": "quantity", "value": "1000"},
                                    {"key": "package_code", "value": "1500594"}]}])
        self.assertEqual((refund.status, refund.amount, refund.partial_reverse_id, refund.reverted_amount),
                         (AtmosRefund.CONFIRMED, 90000, 3, 90000))
        self.assertEqual(response.data["status"], "confirmed")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 2)  # a part: still paid
        self.assertEqual(self.available()["lines"][0]["quantity"], 1)

        # the second lamp gets the rest of the line
        response, create, _ = self.refund({"items": [{"item_id": self.lamp_item.id, "quantity": 1}]})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(create.call_args.kwargs["amount"], 90000)
        self.assertEqual([line["item_id"] for line in self.available()["lines"]], [self.cable_item.id, None])

    def test_uneven_parts_add_up_to_the_line(self):
        lines = self.charge.receipt_lines
        lines[0].update(quantity=3, amount=100000)
        AtmosTransaction.objects.filter(pk=self.charge.pk).update(receipt_lines=lines)
        amounts = []
        for quantity in (1, 2):
            response, create, _ = self.refund({"items": [{"item_id": self.lamp_item.id, "quantity": quantity}]})
            self.assertEqual(response.status_code, 201, response.data)
            amounts.append(create.call_args.kwargs["amount"])
        self.assertEqual(amounts, [33333, 66667])

    def test_everything_refunds_the_rest_and_cancels_the_payment(self):
        self.refund({"items": [{"item_id": self.lamp_item.id, "quantity": 1}]})
        response, create, confirm = self.refund({"all": True})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(create.call_args.kwargs["amount"], 1738000 - 90000)
        self.assertEqual([(row["name"], row["amount"]) for row in confirm.call_args.kwargs["ofd_items"]],
                         [("Lamp", 90000), ("Cable", 270000), ("Yetkazib berish xizmati", 1288000)])
        self.assertEqual(confirm.call_args.kwargs["ofd_items"][2]["ofd_code"], DELIVERY_IKPU)
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_status), (Order.CONFIRMED, 3))
        self.assertTrue(OrderOutboxEvent.objects.filter(order=self.order, event_type="order.refunded").exists())
        comment = OrderComment.objects.filter(order=self.order, is_system=True).last()
        self.assertEqual((comment.author.username, "Qaytarilgan" in comment.text), ("admin", True))
        data = self.available()
        self.assertFalse(data["can_refund"])
        self.assertEqual(data["lines"], [])

    def test_delivery_alone(self):
        response, create, confirm = self.refund({"delivery": True})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(create.call_args.kwargs["amount"], 1288000)
        self.assertEqual(len(confirm.call_args.kwargs["ofd_items"]), 1)
        response, create, _ = self.refund({"delivery": True})
        self.assertEqual(response.status_code, 400)
        create.assert_not_called()

    def test_refused_refund_is_kept_failed_and_counts_nothing(self):
        response, _, confirm = self.refund({"all": True}, create=REFUSED)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Reverse not allowed", str(response.data["detail"]))
        confirm.assert_not_called()
        refund = AtmosRefund.objects.get()
        self.assertEqual(refund.status, AtmosRefund.FAILED)
        self.assertEqual(str(response.data["refund"]), str(refund.id))
        self.assertEqual(self.available()["refunded_amount"], 0)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 2)

    def test_lost_confirm_answer(self):
        body = {"items": [{"item_id": self.cable_item.id, "quantity": 1}]}
        with mock.patch.object(AtmosTransactionService, "create_partial_reverse", return_value=CREATED), \
                mock.patch.object(AtmosTransactionService, "confirm_partial_reverse", side_effect=TimeoutError), \
                mock.patch.object(AtmosTransactionService, "get_partial_reverse",
                                  return_value={**CONFIRMED, "transaction_reverted_amount": 270000}):
            response = self.admin.post(self.url, body, format="json")
        # Atmos shows the money returned -> confirmed
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(AtmosRefund.objects.get().status, AtmosRefund.CONFIRMED)

        body = {"items": [{"item_id": self.lamp_item.id, "quantity": 2}]}
        with mock.patch.object(AtmosTransactionService, "create_partial_reverse", return_value=CREATED), \
                mock.patch.object(AtmosTransactionService, "confirm_partial_reverse", side_effect=TimeoutError), \
                mock.patch.object(AtmosTransactionService, "get_partial_reverse", side_effect=TimeoutError):
            response = self.admin.post(self.url, body, format="json")
        # unknown -> pending, counted as refunded so it is never sent twice
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AtmosRefund.objects.order_by("-id").first().status, AtmosRefund.PENDING)
        self.assertEqual([line["item_id"] for line in self.available()["lines"]], [None])

    def test_bad_requests_never_reach_atmos(self):
        for body in ({}, {"items": [{"item_id": self.lamp_item.id, "quantity": 3}]},
                     {"items": [{"item_id": 999999, "quantity": 1}]},
                     {"items": [{"item_id": self.lamp_item.id, "quantity": 1}] * 2}):
            response, create, _ = self.refund(body)
            self.assertEqual(response.status_code, 400, body)
            create.assert_not_called()
        self.assertFalse(AtmosRefund.objects.exists())

    def test_order_not_paid_by_atmos(self):
        Order.objects.filter(pk=self.order.pk).update(payment_status=1)
        response, create, _ = self.refund({"all": True})
        self.assertEqual(response.status_code, 400)
        create.assert_not_called()
        self.assertFalse(self.available()["can_refund"])

    def test_charge_made_before_the_lines_were_stored(self):
        # orders 407 / 408: the lines are rebuilt from the order
        AtmosTransaction.objects.filter(pk=self.charge.pk).update(receipt_lines=None)
        self.assertEqual(self.available()["charged_amount"], 1738000)
        response, create, _ = self.refund({"items": [{"item_id": self.cable_item.id, "quantity": 1}]})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(create.call_args.kwargs["amount"], 270000)

    def test_unknown_order(self):
        self.assertEqual(self.admin.get("/api/v1/admin/orders/999999/refunds/").status_code, 404)

    def test_list(self):
        self.refund({"delivery": True})
        response = self.admin.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["lines"][0]["item_id"], None)
        self.assertEqual(response.data["results"][0]["created_by"]["username"], "admin")


class ChargeStoresLinesTests(ApiTestCase):
    def test_charge_keeps_the_receipt_lines(self):
        customer = make_customer("+998900000452")
        _, item_category = make_item_category("C")
        order, (item,) = make_order(customer, [(make_product("P", item_category, 1000), 2)], total_price=2000,
                                    hold_id=77, payment_status=1)
        charged = {"result": {"code": "OK"}, "ofd_url": "https://ofd2.atmos.uz/api/ofd/x",
                   "store_transaction": {"trans_id": 5, "success_trans_id": 6, "amount": 200000, "store": {"id": 1}}}
        with mock.patch.object(AtmosAuthService, "get_access_token", return_value="t"), \
                mock.patch.object(AtmosHoldService, "charge_hold", return_value=charged):
            charge_order_hold(order.id)
        self.assertEqual(AtmosTransaction.objects.get(order=order).receipt_lines, [
            {"item_id": item.id, "ofd_code": TEST_IKPU, "name": "P", "amount": 200000, "quantity": 2,
             "package_code": ""}])
