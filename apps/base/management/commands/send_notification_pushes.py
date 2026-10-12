from django.core.management.base import BaseCommand

from apps.base.notification_push import push_due_notifications


class Command(BaseCommand):
    help = ("Sends the FCM push of the notifications whose publish time has come (scheduled ones and "
            "those created outside the admin API). Celery beat runs the same job every minute "
            "(apps.base.tasks.push_due_notifications); the command is for a run by hand.")

    def handle(self, *args, **options):
        sent = push_due_notifications()
        for notification_id, devices in sent.items():
            self.stdout.write(f"Notification {notification_id}: {devices} devices")
        self.stdout.write(f"Pushed: {len(sent)} notifications")
