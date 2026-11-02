"""FCM push to the customer when the order status changes.

`notify_order_status` is called from the Order signals (and by hand where `queryset.update()` skips
them). The push starts only after commit, in the background (`tasks.push_order_status`), so an FCM
failure never affects the order itself.
"""
import logging

from django.db import transaction

from apps.base.models import Notification
from apps.service.models.choices import ORDER_CONFIRMED, ORDER_COLLECTING, ORDER_DELIVERING, \
    ORDER_READY_FOR_PICKUP, ORDER_COMPLETED, ORDER_CANCELED
from utils.background import run_in_background
from utils.send_notification import send_push_to_customer

logger = logging.getLogger(__name__)

ORDER_STATUS_PUSH_TYPE = "order_status"

# the customer's language is not stored anywhere, so the texts are in the project default language (ru);
# the app can localize by `data.status` instead. Status 0 (Pending) is not announced.
ORDER_STATUS_PUSH = {
    ORDER_CONFIRMED: ("Заказ подтверждён", "Ваш заказ №{order_id} подтверждён."),
    ORDER_COLLECTING: ("Заказ в сборке", "Ваш заказ №{order_id} принят и передан в сборку."),
    ORDER_DELIVERING: ("Заказ в доставке", "Ваш заказ №{order_id} передан в доставку."),
    ORDER_READY_FOR_PICKUP: ("Заказ готов к выдаче",
                             "Ваш заказ №{order_id} ждёт вас в магазине «{store}». Заберите его до {deadline}."),
    ORDER_COMPLETED: ("Заказ выполнен", "Ваш заказ №{order_id} выполнен. Спасибо за покупку!"),
    ORDER_CANCELED: ("Заказ отменён", "Ваш заказ №{order_id} отменён."),
}


def notify_order_status(order_id, customer_id, status):
    if not customer_id or status not in ORDER_STATUS_PUSH:
        return
    transaction.on_commit(lambda: _send_in_background(order_id, customer_id, status))


def _send_in_background(order_id, customer_id, status):
    from . import tasks
    run_in_background(tasks.push_order_status, order_id, customer_id, status)


def order_deeplink(order_id):
    """`buildex://order/125` — the same scheme as the notification deeplinks."""
    return f"{Notification.DEEPLINK_SCHEME}order/{order_id}"


def _pickup_details(order_id):
    """Store name (ru) and deadline of a ready pickup order, for the push text and data."""
    from .models import Order
    order = Order.objects.filter(pk=order_id).only("pickup_store_snapshot", "pickup_deadline").first()
    snapshot = (order.pickup_store_snapshot if order else None) or {}
    deadline = order.pickup_deadline if order else None
    return {
        "store": snapshot.get("name_ru") or "",
        "branch_id": snapshot.get("id"),
        "deadline": deadline.strftime("%d.%m.%Y %H:%M") if deadline else "",
        "pickup_deadline": deadline.isoformat() if deadline else "",
    }


def send_order_status_push(order_id, customer_id, status):
    title, body = ORDER_STATUS_PUSH[status]
    # FCM data values must be strings
    data = {"type": ORDER_STATUS_PUSH_TYPE, "order_id": str(order_id), "status": str(status),
            "deeplink": order_deeplink(order_id)}
    text = {"order_id": order_id}
    if status == ORDER_READY_FOR_PICKUP:
        pickup = _pickup_details(order_id)
        text.update(store=pickup["store"], deadline=pickup["deadline"])
        data.update(branch_id=str(pickup["branch_id"] or ""), pickup_deadline=pickup["pickup_deadline"])
    sent = send_push_to_customer(customer_id, title, body.format(**text), data=data)
    logger.info("Order status push: order_id=%s status=%s devices=%s", order_id, status, sent)
    return sent
