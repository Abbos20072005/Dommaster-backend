"""Celery tasks of the base app. The periodic ones are scheduled in `CELERY_BEAT_SCHEDULE`
(`config/settings.py`)."""
from celery import shared_task

from . import notification_push


@shared_task
def send_notification_push(notification_id):
    notification_push.send_push(notification_id)


@shared_task
def push_due_notifications():
    return notification_push.push_due_notifications()
