"""FCM push to the customer when the order status changes.

`notify_order_status` is called from the Order signals (and by hand where `queryset.update()` skips
them). The push starts only after commit, in a background thread, so an FCM failure never affects
the order itself.
"""
import logging
import threading

from django.db import connection, transaction

from utils.send_notification import send_push_to_customer

logger = logging.getLogger(__name__)

ORDER_STATUS_PUSH_TYPE = "order_status"

# the customer's language is not stored anywhere, so the texts are in the project default language (ru);
# the app can localize by `data.status` instead. Status 0 (Pending) is not announced.
ORDER_STATUS_PUSH = {
    1: ("Заказ в сборке", "Ваш заказ №{order_id} принят и передан в сборку."),
    2: ("Заказ в доставке", "Ваш заказ №{order_id} передан в доставку."),
    3: ("Заказ выполнен", "Ваш заказ №{order_id} выполнен. Спасибо за покупку!"),
    4: ("Заказ отменён", "Ваш заказ №{order_id} отменён."),
}


def notify_order_status(order_id, customer_id, status):
    if not customer_id or status not in ORDER_STATUS_PUSH:
        return
    transaction.on_commit(lambda: threading.Thread(
        target=_send_thread, args=(order_id, customer_id, status), daemon=True,
    ).start())


def _send_thread(order_id, customer_id, status):
    try:
        title, body = ORDER_STATUS_PUSH[status]
        sent = send_push_to_customer(
            customer_id, title, body.format(order_id=order_id),
            # FCM data values must be strings
            data={"type": ORDER_STATUS_PUSH_TYPE, "order_id": str(order_id), "status": str(status)},
        )
        logger.info("Order status push: order_id=%s status=%s devices=%s", order_id, status, sent)
    except Exception as e:
        logger.error("Order status push failed: order_id=%s status=%s error=%s", order_id, status, e)
    finally:
        connection.close()
