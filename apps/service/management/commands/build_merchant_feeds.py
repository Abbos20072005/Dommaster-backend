from django.core.management.base import BaseCommand, CommandError

from apps.service import merchant_feed


class Command(BaseCommand):
    help = ("Rebuilds the product feeds for Google Merchant Center (feeds/google.xml) and Yandex (feeds/yandex.yml). "
            "Celery beat runs it 4 times a day (apps.service.tasks.build_merchant_feeds).")

    def handle(self, *args, **options):
        try:
            result = merchant_feed.build_feeds()
        except merchant_feed.FeedConfigError as e:
            raise CommandError(str(e))
        for name, count in result.items():
            self.stdout.write(f"{merchant_feed.feed_path(name)}: {count} products")
