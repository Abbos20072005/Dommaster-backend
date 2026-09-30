"""Order event outbox.

`emit_order_event` must be called inside the transaction that changes the order: the event row is
committed (or rolled back) together with it. Delivery to Telegram starts only after commit, in a
background thread, so a Telegram failure never affects the order itself.
"""
import logging
import threading
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import F
from django.utils import timezone

from .models import OrderOutboxEvent
from .models.choices import OUTBOX_SENT, OUTBOX_FAILED
from .utils import send_order_event_to_telegram

logger = logging.getLogger(__name__)

RETRY_DELAY = timedelta(minutes=1)


def emit_order_event(order, event_type, payload=None):
    # statuses as of the event, not as of delivery
    payload = {"status": order.status, "payment_status": order.payment_status, **(payload or {})}
    event = OrderOutboxEvent.objects.create(order=order, event_type=event_type, payload=payload)
    transaction.on_commit(lambda: _dispatch_in_background(event.pk))
    return event


def _dispatch_in_background(event_pk):
    threading.Thread(target=_dispatch_thread, args=(event_pk,), daemon=True).start()


def _dispatch_thread(event_pk):
    try:
        dispatch_event(event_pk)
    finally:
        connection.close()


def dispatch_event(event_pk):
    event = OrderOutboxEvent.objects.select_related(
        "order", "order__customer", "order__order_location", "order__pickup_branch", "order__promocode",
    ).filter(pk=event_pk).first()
    if event is None or event.status == OUTBOX_SENT:
        return

    now = timezone.now()
    try:
        send_order_event_to_telegram(event.event_type, event.order, event.payload)
    except Exception as e:
        logger.error(
            "Order event delivery failed: event_id=%s type=%s order_id=%s error=%s",
            event.event_id, event.event_type, event.order_id, e,
        )
        OrderOutboxEvent.objects.filter(pk=event.pk).update(
            status=OUTBOX_FAILED, attempts=F("attempts") + 1, last_error=str(e)[:2000],
            next_attempt_at=now + RETRY_DELAY, updated_at=now,
        )
        return

    OrderOutboxEvent.objects.filter(pk=event.pk).update(
        status=OUTBOX_SENT, attempts=F("attempts") + 1, sent_at=now, last_error="", updated_at=now,
    )
    logger.info("Order event sent: event_id=%s type=%s order_id=%s", event.event_id, event.event_type, event.order_id)
