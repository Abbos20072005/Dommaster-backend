from django.core.management.base import BaseCommand

from apps.service import funnel


class Command(BaseCommand):
    help = ("Sums up the product funnel events (views, cart additions, checkout starts) of the last days per "
            "day, product and platform into ProductFunnelDaily and deletes the raw events older than --keep-days. "
            "Safe to run again. Celery beat runs it every night (apps.service.tasks.build_product_funnel).")

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=funnel.REBUILD_DAYS,
                            help="Rebuild the last N days up to yesterday (default %(default)s)")
        parser.add_argument("--keep-days", type=int, default=funnel.EVENT_DAYS,
                            help="Keep the raw events of the last N days (default %(default)s)")

    def handle(self, *args, **options):
        built, deleted = funnel.nightly(days=options["days"], keep_days=options["keep_days"])
        self.stdout.write(f"Daily rows built: {built}, old events deleted: {deleted}")
