"""Celery tasks of the service app. The logic stays in the modules they call; the periodic ones are
scheduled in `CELERY_BEAT_SCHEDULE` (`config/settings.py`)."""
from celery import shared_task
from django.core.management import call_command

from utils.background import exclusive
from . import badges, filter_pages, merchant_feed, order_push, outbox


@shared_task
def deliver_order_event(event_pk):
    outbox.dispatch_event(event_pk)


@shared_task
def retry_order_events():
    return outbox.retry_due_events()


@shared_task
def push_order_status(order_id, customer_id, status):
    order_push.send_order_status_push(order_id, customer_id, status)


@shared_task
@exclusive(30 * 60)
def recalculate_badges():
    return badges.recalculate_auto_badges()


@shared_task
@exclusive(30 * 60)
def refresh_filter_pages():
    return filter_pages.refresh_counts()


@shared_task
@exclusive(6 * 60 * 60)
def import_characteristics():
    call_command("import_characteristics")


@shared_task
def clean_feed_log():
    call_command("clean_feed_log")


@shared_task
@exclusive(60 * 60)
def build_merchant_feeds():
    return merchant_feed.build_feeds()
