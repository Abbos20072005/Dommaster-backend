from datetime import datetime
from unittest import mock

from django.test import TestCase

from apps.base import notification_push
from apps.base.api.v1.admin.serializers import ArticlesSerializer, VideoSerializer
from apps.base.content_push import drop_content_notifications
from apps.base.models import Notification

NOON = datetime(2026, 10, 23, 12, 0)
NIGHT = datetime(2026, 10, 23, 23, 30)


def create(serializer_class, data):
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.save()


@mock.patch("django.utils.timezone.now", return_value=NOON)
class NewContentPushTests(TestCase):
    def test_article_creates_topic_notification(self, _now):
        article = create(ArticlesSerializer, {"title": "Buildex Go", "short_description": "Qisqa", "description": "<p>x</p>"})
        notification = Notification.objects.get()
        self.assertEqual(notification.link_type, Notification.ARTICLE)
        self.assertEqual(notification.content_object, article)
        self.assertEqual(notification.deeplink, f"buildex://article/{article.pk}")
        self.assertTrue(notification.push_to_topic)
        self.assertEqual((notification.title_uz, notification.title_ru), ("Buildex Go", "Buildex Go"))
        self.assertEqual(notification.description_ru, "Qisqa")
        self.assertEqual(notification.publish_at, NOON)
        self.assertIsNotNone(notification.push_sent_at)

    def test_send_push_false(self, _now):
        create(ArticlesSerializer, {"title": "A", "short_description": "B", "description": "C", "send_push": False})
        self.assertFalse(Notification.objects.exists())

    def test_quiet_hours(self, now):
        now.return_value = NIGHT
        create(VideoSerializer, {"name_ru": "Обзор", "url": "https://youtu.be/x"})
        notification = Notification.objects.get()
        self.assertEqual(notification.publish_at, datetime(2026, 10, 24, 9, 0))
        self.assertIsNone(notification.push_sent_at)

    @mock.patch("apps.base.notification_push.send_push_to_devices")
    @mock.patch("apps.base.notification_push.send_push_to_topic", return_value=True)
    def test_topic_push(self, to_topic, to_devices, _now):
        video = create(VideoSerializer, {"name_ru": "Обзор", "name_uz": "", "url": "https://youtu.be/x"})
        notification = Notification.objects.get()
        notification_push.send_push(notification.pk)
        to_devices.assert_not_called()
        to_topic.assert_called_once()
        self.assertEqual(to_topic.call_args.args, ("buildex_content", "Новое видео", "Обзор"))
        self.assertEqual(to_topic.call_args.kwargs["data"]["deeplink"], f"buildex://video/{video.pk}")

    @mock.patch("apps.base.notification_push.send_push_to_devices", return_value=0)
    @mock.patch("apps.base.notification_push.send_push_to_topic")
    def test_targeted_goes_to_devices(self, to_topic, to_devices, _now):
        create(VideoSerializer, {"name_ru": "Обзор", "url": "https://youtu.be/x"})
        notification = Notification.objects.get()
        Notification.objects.filter(pk=notification.pk).update(segment=Notification.PRO)
        notification_push.send_push(notification.pk)
        to_topic.assert_not_called()
        to_devices.assert_called_once()

    def test_delete_drops_notifications(self, _now):
        article = create(ArticlesSerializer, {"title": "A", "short_description": "B", "description": "C"})
        drop_content_notifications(article)
        self.assertFalse(Notification.objects.exists())
