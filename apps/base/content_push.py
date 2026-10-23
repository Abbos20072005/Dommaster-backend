"""Notification + push of a new article / video.

The admin API (`articles/`, `videos/` create, unless `send_push=false`) creates a `Notification` for
everybody that leads to the new row (`link_type` article / video, `buildex://article/<id>`,
`buildex://video/<id>`), with quiet hours on: it is in the customers' list like any other notification,
and its push goes to the static FCM topic `buildex_content` (`notification_push.send_topic_push`).
Deleting the article / video deletes its notifications, so a scheduled one never goes out to a dead link.
"""
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.base.models import Articles, Notification
from apps.base.notification_push import push_if_published

TITLE_LENGTH = Notification._meta.get_field("title").max_length
# a push body is cut by the phone anyway; the list shows the same text
BODY_LENGTH = 200
# a video has no text of its own: its name is the body
VIDEO_TITLE = {"uz": "Yangi video", "ru": "Новое видео"}


def cut(text, length):
    text = (text or "").strip()
    return text if len(text) <= length else text[:length - 1].rstrip() + "…"


def texts_of(obj):
    """{field: value} of the notification's title / description per language."""
    if isinstance(obj, Articles):
        # articles are not translated: the same text in both languages
        title, body = cut(obj.title, TITLE_LENGTH), cut(obj.short_description, BODY_LENGTH)
        return {"title_uz": title, "title_ru": title, "description_uz": body, "description_ru": body}
    return {
        "title_uz": VIDEO_TITLE["uz"], "title_ru": VIDEO_TITLE["ru"],
        "description_uz": cut(obj.name_uz or obj.name_ru, BODY_LENGTH),
        "description_ru": cut(obj.name_ru or obj.name_uz, BODY_LENGTH),
    }


def notify_new_content(obj):
    """Creates the notification of a new article / video and starts its push (now, or at 09:00 when it
    is quiet hours). Call inside the transaction that created `obj`."""
    link_type = Notification.ARTICLE if isinstance(obj, Articles) else Notification.VIDEO
    notification = Notification.objects.create(
        **texts_of(obj),
        link_type=link_type, content_object=obj, deeplink=Notification.deeplink_of(link_type, obj),
        segment=Notification.SEGMENT_ALL, platform=Notification.PLATFORM_ALL,
        quiet_hours=True, publish_at=Notification.after_quiet_hours(timezone.now()),
        push_to_topic=True,
    )
    push_if_published(notification)
    return notification


def drop_content_notifications(obj):
    """Deletes the notifications leading to `obj` (the article / video is being deleted)."""
    notifications = Notification.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk,
        link_type__in=(Notification.ARTICLE, Notification.VIDEO),
    )
    for notification in notifications.exclude(image=""):
        notification.image.delete(save=False)
    notifications.delete()

