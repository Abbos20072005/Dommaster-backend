"""Pickup orders past their deadline (`Order.pickup_deadline`, ready + PICKUP_DAYS).

`expire_overdue_pickups` (Celery beat, `tasks.expire_pickup_orders`) emits `order.pickup_expired` once per
ready period: the staff Telegram group gets a message, `pickup_expired_at` marks the order. Nothing else
happens automatically - the order stays ready until staff complete or cancel it.
"""
import logging

from django.db import transaction

from apps.base.stores import tashkent_now
from .models import Order
from .models.choices import ORDER_EVENT_PICKUP_EXPIRED
from .outbox import emit_order_event

logger = logging.getLogger(__name__)


def overdue(now):
    return Order.objects.filter(status=Order.READY_FOR_PICKUP, pickup_deadline__lt=now,
                                pickup_expired_at__isnull=True)


def expire_overdue_pickups():
    """Returns how many orders were marked expired."""
    now = tashkent_now().replace(microsecond=0)
    count = 0
    for pk in list(overdue(now).values_list("id", flat=True)):
        with transaction.atomic():
            order = overdue(now).select_for_update().filter(pk=pk).first()
            if order is None:
                continue
            Order.objects.filter(pk=pk).update(pickup_expired_at=now)
            order.pickup_expired_at = now
            emit_order_event(order, ORDER_EVENT_PICKUP_EXPIRED, payload={
                "store_id": order.pickup_branch_id, "pickup_deadline": order.pickup_deadline.isoformat(),
            })
            count += 1
    if count:
        logger.info("Pickup orders expired: %s", count)
    return count
