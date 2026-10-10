from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.service import feed
from apps.service.models import FeedImpression, InterestEvent


class Command(BaseCommand):
    help = ("Deletes old rows of the personal feed log: interest events the profile no longer reads "
            "and feed impressions. Run it by cron (there is no scheduler in the project).")

    def add_arguments(self, parser):
        parser.add_argument("--event-days", type=int, default=feed.EVENT_DAYS,
                            help="Keep interest events of the last N days (the profile reads %(default)s)")
        parser.add_argument("--impression-days", type=int, default=180,
                            help="Keep feed impressions of the last N days (default %(default)s)")

    def handle(self, *args, **options):
        now = timezone.now()
        events, _ = InterestEvent.objects.filter(
            created_at__lt=now - timedelta(days=options["event_days"])).delete()
        impressions, _ = FeedImpression.objects.filter(
            created_at__lt=now - timedelta(days=options["impression_days"])).delete()
        self.stdout.write(f"Deleted: {events} interest events, {impressions} feed impressions")
