"""Order event outbox.

`emit_order_event` must be called inside the transaction that changes the order: the event row is
committed (or rolled back) together with it. Delivery to Telegram starts only after commit, in the
background (`tasks.deliver_order_event`), so a Telegram failure never affects the order itself.
A failed delivery is repeated by `retry_due_events` (`tasks.retry_order_events`, Celery beat).
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from utils.background import run_in_background
from .models import OrderOutboxEvent
from .models.choices import (
    OUTBOX_SENT, OUTBOX_FAILED, OUTBOX_RECORDED, ORDER_EVENT_PICKUP_SELECTED, ORDER_EVENT_PICKUP_READY,
    ORDER_EVENT_PICKUP_DONE,
)
from .utils import send_order_event_to_telegram

logger = logging.getLogger(__name__)

# wait before the 2nd, 3rd, ... attempt; after the last one the event stays `failed`
RETRY_DELAYS = [timedelta(minutes=minutes) for minutes in (1, 5, 15, 60, 180)]
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1
# an event whose delivery never reported back (the process died) is taken again after this
CLAIM_TIME = timedelta(minutes=10)
# older events are not repeated: a day-old message in the staff group is only noise
RETRY_WINDOW = timedelta(days=1)
RECORD_ONLY_EVENTS = {ORDER_EVENT_PICKUP_SELECTED, ORDER_EVENT_PICKUP_READY, ORDER_EVENT_PICKUP_DONE}
DONE_STATUSES = (OUTBOX_SENT, OUTBOX_RECORDED)


def emit_order_event(order, event_type, payload=None):
    # statuses as of the event, not as of delivery
    payload = {"status": order.status, "payment_status": order.payment_status, **(payload or {})}
    if event_type in RECORD_ONLY_EVENTS:
        return OrderOutboxEvent.objects.create(order=order, event_type=event_type, payload=payload,
                                               status=OUTBOX_RECORDED)
    event = OrderOutboxEvent.objects.create(order=order, event_type=event_type, payload=payload)
    transaction.on_commit(lambda: _deliver_in_background(event.pk))
    return event


def _deliver_in_background(event_pk):
    from . import tasks
    run_in_background(tasks.deliver_order_event, event_pk)


def retry_due_events():
    """Delivers again the recent events that failed or never reported back. Returns how many were taken."""
    now = timezone.now()
    due = OrderOutboxEvent.objects.exclude(status__in=DONE_STATUSES).filter(
        next_attempt_at__lte=now, attempts__lt=MAX_ATTEMPTS, created_at__gte=now - RETRY_WINDOW,
    ).order_by("id").values_list("id", flat=True)
    return sum(1 for event_pk in list(due) if dispatch_event(event_pk))


def dispatch_event(event_pk):
    """Sends the event unless it is sent or being sent already. False = it was not this call's to send."""
    now = timezone.now()
    # the claim: only the caller that moves `next_attempt_at` forward sends the event, so the delivery
    # started on commit and the retry task never send one event twice
    claimed = OrderOutboxEvent.objects.exclude(status__in=DONE_STATUSES).filter(
        pk=event_pk, next_attempt_at__lte=now,
    ).update(next_attempt_at=now + CLAIM_TIME)
    if not claimed:
        return False

    event = OrderOutboxEvent.objects.select_related(
        "order", "order__customer", "order__order_location", "order__pickup_branch", "order__promocode",
    ).get(pk=event_pk)
    try:
        send_order_event_to_telegram(event.event_type, event.order, event.payload)
    except Exception as e:
        logger.error(
            "Order event delivery failed: event_id=%s type=%s order_id=%s error=%s",
            event.event_id, event.event_type, event.order_id, e,
        )
        OrderOutboxEvent.objects.filter(pk=event.pk).update(
            status=OUTBOX_FAILED, attempts=F("attempts") + 1, last_error=str(e)[:2000],
            next_attempt_at=now + RETRY_DELAYS[min(event.attempts, len(RETRY_DELAYS) - 1)], updated_at=now,
        )
        return True

    OrderOutboxEvent.objects.filter(pk=event.pk).update(
        status=OUTBOX_SENT, attempts=F("attempts") + 1, sent_at=now, last_error="", updated_at=now,
    )
    logger.info("Order event sent: event_id=%s type=%s order_id=%s", event.event_id, event.event_type, event.order_id)
    return True
