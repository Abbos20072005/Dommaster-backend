"""Atmos card payment of an order = a hold (BLD-486).

`hold/create/` only freezes the money and leaves the order Pending (payment status Hold); the money is charged
by the server when an operator moves the order on in the admin panel (`charge_order_hold`, first to Confirmed),
a cancelled order gets the hold released (`cancel_order_hold`). Both lock the order row, so two clicks never
charge twice, and do nothing when the order has no active hold."""
import logging

from django.db import transaction

from apps.payment.models import AtmosTransaction
from apps.payment.services_pay.auth_services import AtmosAuthService, AtmosHoldService
from apps.service.models import Order
from apps.service.models.choices import PAYMENT_CANCELLED, PAYMENT_HOLD, PAYMENT_PAID

logger = logging.getLogger(__name__)


class HoldError(Exception):
    """Atmos refused (or could not be reached); the message is for the operator."""


def error_text(exc):
    """The body Atmos sent with an HTTP error (`raise_for_status`), cut to 1000 chars; "" when none."""
    response = getattr(exc, "response", None)
    return (response.text or "")[:1000] if response is not None else ""


def has_hold(order):
    return bool(order.hold_id) and order.payment_status == PAYMENT_HOLD


def save_charge(order, data):
    """Stores a successful `charge_hold` answer: the transaction row, `ofd_url` (the receipt), payment Paid.
    The order status is not touched."""
    store_transaction = data.get("store_transaction") or {}
    store_info = store_transaction.get("store") or {}
    AtmosTransaction.objects.create(
        order=order,
        success_trans_id=store_transaction.get("success_trans_id", 0),
        trans_id=store_transaction.get("trans_id", 0),
        store_id=store_info.get("id"),
        store_name=store_info.get("name", ""),
        terminal_id=store_transaction.get("terminal_id", ""),
        account=store_transaction.get("account", ""),
        amount=store_transaction.get("amount", 0),
        confirmed=store_transaction.get("confirmed", False),
        prepay_time=store_transaction.get("prepay_time"),
        confirm_time=store_transaction.get("confirm_time"),
        ofd_url=data.get("ofd_url"),
        commission_value=store_transaction.get("commission_value", "0"),
        commission_type=store_transaction.get("commission_type", ""),
        total=store_transaction.get("total"),
        status_code=store_transaction.get("status_code", ""),
        status_message=store_transaction.get("status_message", ""),
        pc_type=store_transaction.get("pc_type", ""),
    )
    order.payment_status = PAYMENT_PAID
    order.ofd_url = data.get("ofd_url")
    order.save(update_fields=["payment_status", "ofd_url"])


def _call(order, action, call):
    try:
        data = call(access_token=AtmosAuthService.get_access_token(), hold_id=order.hold_id)
    except Exception as e:
        logger.warning("Atmos hold %s failed: order_id=%s hold_id=%s error=%s body=%s",
                       action, order.id, order.hold_id, e, error_text(e))
        raise HoldError(f"Atmos: {action} failed ({e})")
    result = data.get("result") or {}
    if result.get("code") != "OK":
        logger.warning("Atmos hold %s refused: order_id=%s hold_id=%s result=%s",
                       action, order.id, order.hold_id, result)
        raise HoldError(f"Atmos: {action} refused ({result.get('code')}: {result.get('description', '')})")
    logger.info("Atmos hold %s done: order_id=%s hold_id=%s", action, order.id, order.hold_id)
    return data


def charge_order_hold(order_id):
    """Charges the whole frozen sum. Returns the order (fresh from the db); raises `HoldError`."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if has_hold(order):
            save_charge(order, _call(order, "charge", AtmosHoldService.charge_hold))
    return order


def cancel_order_hold(order_id):
    """Releases the frozen sum (payment Cancelled -> the `order.refunded` event). Returns the order; raises
    `HoldError`."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if has_hold(order):
            _call(order, "cancel", AtmosHoldService.cancel_hold)
            order.payment_status = PAYMENT_CANCELLED
            order.save(update_fields=["payment_status"])
    return order
