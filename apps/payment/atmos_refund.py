"""Refund of a charged Atmos card payment, whole or a part (BLD-545).

A refund = an Atmos partial reversal of the charge transaction: `create-reverse-partial` (the sum) and then
`confirm-reverse-partial` with the refunded receipt lines (`ofd_items`) - Atmos makes the refund receipt from them.
The whole sum goes the same way (every line that is left), so a refund receipt always carries the goods.

The lines come from the charge (`AtmosTransaction.receipt_lines` = what the receipt showed; a charge made before
the field = rebuilt from the order by `atmos_hold.receipt_lines`). A line can be refunded in parts: a quantity
of an item gets its share of the line sum (floor), the last pieces get the rest, so the refunds of a line add up
to the line to the tiyin. Every refund that is not `failed` counts as taken - a `pending` one (Atmos's answer to
the confirmation was lost) too, so it is never refunded twice. Everything refunded -> payment Cancelled (the
`order.refunded` event). The order status and the stock are not touched."""
import logging
import os
from collections import defaultdict

from django.db import transaction

from apps.payment.atmos_hold import error_text, receipt_lines, to_ofd
from apps.payment.models import AtmosRefund, AtmosTransaction
from apps.payment.services_pay.auth_services import AtmosAuthService, AtmosTransactionService
from apps.service.models import Order
from apps.service.models.choices import PAYMENT_CANCELLED, PAYMENT_PAID

logger = logging.getLogger(__name__)

DEFAULT_REASON = "Возврат товара"


class RefundError(Exception):
    """The refund can't be made or Atmos refused it; the message is for the operator. `refund` = the saved row
    (failed / pending) when Atmos was called."""

    def __init__(self, message, refund=None, unknown=False):
        super().__init__(message)
        self.refund = refund
        # Atmos may have returned the money (the confirmation answer was lost): the row stays pending
        self.unknown = unknown


def charge_transaction(order):
    """The order's Atmos charge (the newest row), None when it was not paid by Atmos."""
    return AtmosTransaction.objects.filter(order=order).order_by("-id").first()


def charged_lines(order, charge):
    return charge.receipt_lines or receipt_lines(order)


def remaining_lines(order, charge=None):
    """The charged receipt lines with the quantity and the sum not refunded yet (lines refunded in full left
    out); None when the charge has no lines (an item without an IKPU code)."""
    charge = charge or charge_transaction(order)
    lines = charged_lines(order, charge) if charge else None
    if lines is None:
        return None
    taken = defaultdict(lambda: [0, 0])
    for refund in AtmosRefund.objects.filter(transaction=charge).exclude(status=AtmosRefund.FAILED):
        for line in refund.lines:
            taken[line["item_id"]][0] += line["quantity"]
            taken[line["item_id"]][1] += line["amount"]
    left = []
    for line in lines:
        quantity, amount = taken[line["item_id"]]
        if line["quantity"] - quantity > 0:
            left.append({**line, "quantity": line["quantity"] - quantity, "amount": line["amount"] - amount,
                         "charged_quantity": line["quantity"], "charged_amount": line["amount"]})
    return left


def pick_lines(left, items=(), delivery=False, everything=False):
    """The refund lines: `items` = [{"item_id", "quantity"}], `delivery` = the delivery line, `everything` = all
    that is left. Raises `RefundError`."""
    if everything:
        return [{key: line[key] for key in ("item_id", "ofd_code", "name", "amount", "quantity", "package_code")}
                for line in left]
    by_item = {line["item_id"]: line for line in left}
    picked, seen = [], set()
    for row in items:
        item_id, quantity = row["item_id"], row["quantity"]
        if item_id in seen:
            raise RefundError(f"Позиция {item_id} указана дважды")
        seen.add(item_id)
        line = by_item.get(item_id) if item_id is not None else None
        if line is None:
            raise RefundError(f"Позиции {item_id} нет в чеке или она уже возвращена")
        if quantity < 1 or quantity > line["quantity"]:
            raise RefundError(f"Позиция {item_id}: можно вернуть от 1 до {line['quantity']}")
        amount = line["amount"] if quantity == line["quantity"] \
            else line["charged_amount"] * quantity // line["charged_quantity"]
        picked.append({"item_id": item_id, "ofd_code": line["ofd_code"], "name": line["name"], "amount": amount,
                       "quantity": quantity, "package_code": line.get("package_code", "")})
    if delivery:
        line = by_item.get(None)
        if line is None:
            raise RefundError("Доставки нет в чеке или она уже возвращена")
        picked.append({key: line[key] for key in ("item_id", "ofd_code", "name", "amount", "quantity",
                                                  "package_code")})
    if not picked:
        raise RefundError("Нечего возвращать: укажите позиции, доставку или всё")
    return picked


def _ok(data):
    return (data.get("result") or {}).get("code") == "OK"


def _reverse(refund, charge, refunded_before):
    """create + confirm the partial reversal; fills the row (status, ids, amounts, error). Raises `RefundError`."""
    store_id = charge.store_id or int(os.environ["ATMOS_STORE_ID"])
    # `success_trans_id`: the id the Atmos docs name for a reversal (`merchant/pay/reverse`)
    transaction_id = charge.success_trans_id
    try:
        data = AtmosTransactionService.create_partial_reverse(
            access_token=AtmosAuthService.get_access_token(), transaction_id=transaction_id, store_id=store_id,
            amount=refund.amount, reason=refund.reason or DEFAULT_REASON,
            request_id=f"order-{refund.order_id}-refund-{refund.id}")
    except Exception as e:
        logger.warning("Atmos refund create failed: order_id=%s refund_id=%s error=%s body=%s",
                       refund.order_id, refund.id, e, error_text(e))
        raise RefundError(f"Atmos: возврат не создан ({e})")
    if not _ok(data) or not data.get("transaction_partial_reverse_id"):
        logger.warning("Atmos refund create refused: order_id=%s refund_id=%s answer=%s",
                       refund.order_id, refund.id, data)
        result = data.get("result") or {}
        raise RefundError(f"Atmos отказал: {result.get('code')} {result.get('description', '')}".strip())
    refund.partial_reverse_id = data["transaction_partial_reverse_id"]
    refund.save(update_fields=["partial_reverse_id", "updated_at"])

    ofd = to_ofd(refund.lines)
    logger.info("Atmos refund confirm: order_id=%s refund_id=%s amount=%s ofd_items=%s",
                refund.order_id, refund.id, refund.amount, ofd)
    try:
        data = AtmosTransactionService.confirm_partial_reverse(
            access_token=AtmosAuthService.get_access_token(), transaction_id=transaction_id,
            transaction_partial_reverse_id=refund.partial_reverse_id, store_id=store_id, ofd_items=ofd,
            request_id=f"order-{refund.order_id}-refund-{refund.id}")
    except Exception as e:
        logger.warning("Atmos refund confirm failed: order_id=%s refund_id=%s error=%s body=%s",
                       refund.order_id, refund.id, e, error_text(e))
        data = _confirmed_already(refund, transaction_id, store_id, refunded_before)
        if data is None:
            # the money may be on its way back: the row stays pending and counts as refunded
            raise RefundError(f"Нет ответа Atmos на подтверждение ({e}) — проверьте возврат в Atmos", unknown=True)
    if not _ok(data):
        logger.warning("Atmos refund confirm refused: order_id=%s refund_id=%s answer=%s",
                       refund.order_id, refund.id, data)
        result = data.get("result") or {}
        raise RefundError(f"Atmos отказал: {result.get('code')} {result.get('description', '')}".strip())
    refund.status = AtmosRefund.CONFIRMED
    refund.reverted_amount = data.get("transaction_reverted_amount")
    refund.left_amount = data.get("transaction_left_amount")
    logger.info("Atmos refund done: order_id=%s refund_id=%s answer=%s", refund.order_id, refund.id, data)


def _confirmed_already(refund, transaction_id, store_id, refunded_before):
    """`get-reverse-partial` when the confirmation answer was lost: the answer when Atmos shows the money of this
    refund returned (reverted sum covers the earlier refunds + this one), else None."""
    try:
        data = AtmosTransactionService.get_partial_reverse(
            access_token=AtmosAuthService.get_access_token(), transaction_id=transaction_id,
            transaction_partial_reverse_id=refund.partial_reverse_id, store_id=store_id)
    except Exception as e:
        logger.warning("Atmos refund get failed: order_id=%s refund_id=%s error=%s", refund.order_id, refund.id, e)
        return None
    reverted = data.get("transaction_reverted_amount") or 0
    if _ok(data) and reverted >= refunded_before + refund.amount:
        return data
    return None


def refund_order(order_id, items=(), delivery=False, everything=False, reason="", user=None):
    """Refunds the picked lines of the order's Atmos charge. Returns the confirmed `AtmosRefund`; raises
    `RefundError` (with the failed / pending row when Atmos was called). The order row is locked, so two
    clicks never refund the same line twice."""
    failure = None
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        charge = charge_transaction(order)
        if charge is None or order.payment_status != PAYMENT_PAID:
            raise RefundError("Возврат возможен только для заказа, оплаченного картой через Atmos")
        lines = charged_lines(order, charge)
        if lines is None:
            raise RefundError("Оплата прошла без строк чека (у позиции не было ИКПУ) — возврат только через Atmos")
        left = remaining_lines(order, charge)
        picked = pick_lines(left, items, delivery, everything)
        amount = sum(line["amount"] for line in picked)
        if amount <= 0:
            raise RefundError("Сумма возврата равна нулю")
        total = sum(line["amount"] for line in lines)
        refunded_before = total - sum(line["amount"] for line in left)
        refund = AtmosRefund.objects.create(order=order, transaction=charge, amount=amount, lines=picked,
                                            reason=(reason or "")[:255], created_by=user)
        try:
            _reverse(refund, charge, refunded_before)
        except RefundError as e:
            refund.status = AtmosRefund.PENDING if e.unknown else AtmosRefund.FAILED
            refund.error = str(e)[:2000]
            failure = RefundError(refund.error, refund, e.unknown)
        refund.save()
        if refund.status == AtmosRefund.CONFIRMED and refunded_before + amount >= total:
            order.payment_status = PAYMENT_CANCELLED
            order._payment_changed_by = user  # the system comment of the payment change names the admin
            order.save(update_fields=["payment_status"])
    if failure:
        raise failure
    return refund
