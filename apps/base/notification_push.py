"""FCM push of a common notification (`Notification`) to every registered device.

A notification is pushed once, at the moment it becomes published: `push_if_published` is called by
the admin serializer after create / update (the push starts after commit, in the background —
`tasks.send_notification_push`), `push_due_notifications` by the periodic task of the same name
(Celery beat; by hand: `manage.py send_notification_pushes`) for the scheduled ones whose time has
come. `push_sent_at` is set before sending, so two callers never push the same notification twice —
and a failed push is not repeated.
"""
import logging

from django.db import transaction
from django.utils import timezone

from apps.base.models import Notification
from utils.background import run_in_background
from utils.send_notification import send_push_to_all

logger = logging.getLogger(__name__)

NOTIFICATION_PUSH_TYPE = "notification"


def _claim(notification_id):
    """Marks a published, not yet pushed notification as pushed. False = nothing to send."""
    return bool(Notification.objects.filter(
        Notification.status_q(Notification.PUBLISHED), pk=notification_id, push_sent_at__isnull=True,
    ).update(push_sent_at=timezone.now()))


def push_if_published(notification):
    if not _claim(notification.pk):
        return
    notification.refresh_from_db(fields=("push_sent_at",))
    transaction.on_commit(lambda: _send_in_background(notification.pk))


def _send_in_background(notification_id):
    from . import tasks
    run_in_background(tasks.send_notification_push, notification_id)


def push_due_notifications():
    """Pushes every published notification that has not been pushed yet. Returns {id: devices}."""
    due = Notification.objects.filter(Notification.status_q(Notification.PUBLISHED), push_sent_at__isnull=True)
    return {pk: send_push(pk) for pk in due.order_by("publish_at", "id").values_list("id", flat=True) if _claim(pk)}


def send_push(notification_id):
    notification = Notification.objects.get(pk=notification_id)
    # the customer's language is not stored anywhere, so the text is in the project default language (ru)
    sent = send_push_to_all(
        notification.title_ru or notification.title, notification.description_ru or notification.description,
        # FCM data values must be strings
        data={"type": NOTIFICATION_PUSH_TYPE, "notification_id": str(notification.pk),
              "deeplink": notification.deeplink},
    )
    Notification.objects.filter(pk=notification_id).update(push_devices=sent)
    logger.info("Notification push: notification_id=%s devices=%s", notification_id, sent)
    return sent
