from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import Case, Exists, F, IntegerField, OuterRef, Value, When
from django.utils import timezone

from apps.service.models import Order, OrderStatusChange
from apps.service.models.choices import ORDER_STATUS

# old status code (before migration service 0126) -> the current one
OLD_TO_NEW = {
    0: Order.PENDING,
    1: Order.COLLECTING,
    2: Order.DELIVERING,
    3: Order.COMPLETED,
    4: Order.CANCELED,
    5: Order.READY_FOR_PICKUP,
}
OLD_NAMES = {0: "Pending", 1: "Collecting", 2: "Delivering", 3: "Completed", 4: "Canceled", 5: "Ready for pickup"}
RENUMBER_MIGRATION = ("service", "0126_order_status_confirmed_and_log")


def renumber_time():
    row = MigrationRecorder.Migration.objects.filter(app=RENUMBER_MIGRATION[0], name=RENUMBER_MIGRATION[1]).first()
    return row.applied if row else None


def old_orders(before):
    """Orders that still carry an old status code: created before the renumbering, never saved after it
    (a save after it sets updated_at, a status change also writes the status log)."""
    logged = OrderStatusChange.objects.filter(order_id=OuterRef("pk"))
    return Order.objects.filter(created_at__lt=before, updated_at__lt=before).exclude(Exists(logged))


class Command(BaseCommand):
    help = ("Converts the status of the orders created before the status renumbering of 02.11.2026 (migration "
            "service 0126 added Confirmed and renumbered the codes, the existing rows were not converted). "
            "Only orders not saved since then are touched; the converted ones get updated_at = now, so a second "
            "run finds nothing. queryset.update: no stock change, push, outbox event or status log row.")

    def add_arguments(self, parser):
        parser.add_argument("--before", help="Renumbering time, 'YYYY-MM-DD HH:MM:SS' "
                                             "(default: when migration service 0126 was applied)")
        parser.add_argument("--dry-run", action="store_true", help="Show what would change, write nothing")

    def handle(self, *args, **options):
        if options["before"]:
            try:
                before = datetime.fromisoformat(options["before"])
            except ValueError:
                raise CommandError("--before: expected 'YYYY-MM-DD HH:MM:SS'")
        else:
            before = renumber_time()
            if before is None:
                raise CommandError("Migration service 0126 is not applied — nothing to convert")
        self.stdout.write(f"Renumbering time: {before:%Y-%m-%d %H:%M:%S}")

        edited = Order.objects.filter(created_at__lt=before).exclude(id__in=old_orders(before).values("id"))
        with transaction.atomic():
            orders = old_orders(before).select_for_update()
            ids = list(orders.values_list("id", flat=True))
            counts = {}
            for old in orders.values_list("status", flat=True):
                counts[old] = counts.get(old, 0) + 1
            for old, count in sorted(counts.items()):
                new = OLD_TO_NEW.get(old)
                label = f"{dict(ORDER_STATUS)[new]} ({new})" if new is not None else "UNKNOWN, left as is"
                self.stdout.write(f"  {OLD_NAMES.get(old, old)} ({old}) -> {label}: {count}")
            self.stdout.write(f"Orders to convert: {len(ids)}")
            skipped = edited.count()
            if skipped:
                self.stdout.write(f"Created before but saved after the renumbering (already converted or edited "
                                  f"since — their status is not touched): {skipped}")
            if options["dry_run"] or not ids:
                self.stdout.write("Dry run, nothing written" if options["dry_run"] else "Nothing to convert")
                return
            updated = Order.objects.filter(id__in=ids).update(
                status=Case(*[When(status=old, then=Value(new)) for old, new in OLD_TO_NEW.items()],
                            default=F("status"), output_field=IntegerField()),
                updated_at=timezone.now(),
            )
        self.stdout.write(self.style.SUCCESS(f"Converted: {updated}"))
