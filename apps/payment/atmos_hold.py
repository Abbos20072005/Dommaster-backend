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


def _text(value, size, default=""):
    """Atmos sends null for empty values (`status_message: null` broke the charge of order 403) - the columns
    are NOT NULL and sized."""
    return str(default if value is None else value)[:size]


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def save_charge(order, data):
    """Stores a successful `charge_hold` answer: payment Paid + `ofd_url` (the receipt), then the transaction row.
    The money is already taken, so the order is marked paid even when the row can't be written (only logged,
    with the answer). The order status is not touched."""
    ofd_url = data.get("ofd_url") or None
    store_transaction = data.get("store_transaction") or {}
    logger.info("Atmos hold charged: order_id=%s hold_id=%s ofd_url=%s store_transaction=%s",
                order.id, order.hold_id, ofd_url, str(store_transaction)[:2000])
    order.payment_status = PAYMENT_PAID
    order.ofd_url = ofd_url
    order.save(update_fields=["payment_status", "ofd_url"])

    store_info = store_transaction.get("store") or {}
    get = store_transaction.get
    try:
        with transaction.atomic():
            AtmosTransaction.objects.create(
                order=order,
                success_trans_id=_int(get("success_trans_id"), 0),
                trans_id=_int(get("trans_id"), 0),
                store_id=_int(store_info.get("id")),
                store_name=_text(store_info.get("name"), 255),
                terminal_id=_text(get("terminal_id"), 255),
                account=_text(get("account"), 255),
                amount=_int(get("amount"), 0),
                confirmed=bool(get("confirmed")),
                prepay_time=_int(get("prepay_time")),
                confirm_time=_int(get("confirm_time")),
                ofd_url=ofd_url[:500] if ofd_url else None,
                commission_value=_text(get("commission_value"), 50, "0"),
                commission_type=_text(get("commission_type"), 50),
                total=_int(get("total")),
                status_code=_text(get("status_code"), 10),
                status_message=_text(get("status_message"), 255),
                pc_type=_text(get("pc_type"), 50),
            )
    except Exception:
        logger.exception("Atmos transaction row not saved (the order is paid): order_id=%s", order.id)


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


def _charged_already(order):
    """The `hold/<id>` answer when Atmos says the hold is charged (`store_transaction.confirmed`), else None —
    a charge whose answer was lost (timeout, or our save failed after the money was taken) is not refused
    forever. Any error -> None."""
    try:
        data = AtmosHoldService.get_hold(access_token=AtmosAuthService.get_access_token(), hold_id=order.hold_id)
    except Exception as e:
        logger.warning("Atmos get hold failed: order_id=%s hold_id=%s error=%s", order.id, order.hold_id, e)
        return None
    if (data.get("result") or {}).get("code") == "OK" and (data.get("store_transaction") or {}).get("confirmed"):
        logger.warning("Atmos hold was charged already: order_id=%s hold_id=%s", order.id, order.hold_id)
        return data
    return None


def charge_order_hold(order_id):
    """Charges the whole frozen sum. Returns the order (fresh from the db); raises `HoldError`."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if has_hold(order):
            try:
                data = _call(order, "charge", AtmosHoldService.charge_hold)
            except HoldError:
                data = _charged_already(order)
                if data is None:
                    raise
            save_charge(order, data)
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
