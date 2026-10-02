from django.core.management.base import BaseCommand
from apps.service.badges import recalculate_auto_badges


class Command(BaseCommand):
    help = "Sync the products of auto badges with their rules. Run it from cron every 15 minutes."

    def handle(self, *args, **options):
        changed = recalculate_auto_badges()
        self.stdout.write(self.style.SUCCESS(f"Auto badges recalculated, product links changed: {changed}"))
