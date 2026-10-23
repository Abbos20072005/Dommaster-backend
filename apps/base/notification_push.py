"""FCM push of a notification (`Notification`) to the devices of its audience (`audience.py`).

A notification is pushed once, at the moment it becomes published: `push_if_published` is called by
the admin serializer after create / update (the push starts after commit, in the background —
`tasks.send_notification_push`), `push_due_notifications` by the periodic task of the same name
(Celery beat; by hand: `manage.py send_notification_pushes`) for the scheduled ones whose time has
come. `push_sent_at` is set before sending, so two callers never push the same notification twice —
and a failed push is not repeated.

A notification with `push_to_topic` (the automatic ones of new articles / videos, `content_push.py`)
goes to the static FCM topic `Notification.CONTENT_TOPIC` instead: one request whatever the number of
devices, guests' devices included (the app subscribes to the topic itself).
"""
import logging

from django.db import transaction
from django.utils import timezone

from django.conf import settings

from apps.base import audience
from apps.base.models import Notification, NotificationRecipient
from utils.background import run_in_background
from utils.send_notification import send_push_to_devices, send_push_to_topic

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


def push_data(notification):
    """FCM `data` of the push: where a tap leads, the same as in the client API. Values must be strings."""
    target = notification.content_object
    return {
        "type": NOTIFICATION_PUSH_TYPE,
        "notification_id": str(notification.pk),
        "deeplink": notification.deeplink,
        "link_type": notification.link_type,
        "target_model": target._meta.model_name if target else "",
        "target_id": str(target.pk) if target else "",
        "page": notification.page,
    }


def push_image(notification):
    """Absolute URL of the image, or None: FCM downloads it itself, so it needs the public address."""
    if not notification.image:
        return None
    if not settings.BACKEND_URL:
        logger.warning("Notification push without its image, BACKEND_URL is not set: notification_id=%s",
                       notification.pk)
        return None
    return f"{settings.BACKEND_URL.rstrip('/')}/{notification.image.url.lstrip('/')}"


def send_topic_push(notification):
    """One request to `Notification.CONTENT_TOPIC`, ru text like every other push. The number of devices
    is unknown, so `push_devices` stays 0 (returned as such)."""
    accepted = send_push_to_topic(
        Notification.CONTENT_TOPIC,
        notification.title_ru or notification.title, notification.description_ru or notification.description,
        data=push_data(notification), image=push_image(notification),
    )
    logger.info("Notification topic push: notification_id=%s topic=%s accepted=%s",
                notification.pk, Notification.CONTENT_TOPIC, accepted)
    return 0


def send_push(notification_id):
    notification = Notification.objects.get(pk=notification_id)
    # a topic reaches everybody: a notification made targeted before its push goes to its devices instead
    if notification.push_to_topic and not notification.is_targeted:
        return send_topic_push(notification)
    if notification.is_targeted:
        # the audience as it is now: these customers keep the notification in their list
        customers = audience.audience_customers(notification.segment, notification.platform)
        NotificationRecipient.objects.bulk_create(
            [NotificationRecipient(notification=notification, customer_id=customer_id)
             for customer_id in customers.values_list("id", flat=True)],
            ignore_conflicts=True, batch_size=2000,
        )
    devices = audience.audience_devices(notification.segment, notification.platform)
    # the customer's language is not stored anywhere, so the text is in the project default language (ru)
    sent = send_push_to_devices(
        devices.values_list("fcm_token", flat=True),
        notification.title_ru or notification.title, notification.description_ru or notification.description,
        data=push_data(notification), image=push_image(notification),
    )
    Notification.objects.filter(pk=notification_id).update(push_devices=sent)
    logger.info("Notification push: notification_id=%s devices=%s", notification_id, sent)
    return sent
