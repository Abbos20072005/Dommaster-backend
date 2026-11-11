"""manage.py convert_old_order_statuses: the status codes of the orders made before the renumbering of 02.11.2026.
Run: manage.py test apps.service.tests_order_status_convert"""
from datetime import datetime
from io import StringIO

from django.core.management import call_command
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase

from apps.service.models import Order, OrderStatusChange

CUT = datetime(2026, 11, 2, 12, 43, 9)
BEFORE = "2026-11-02 12:43:09"


def old_order(status, created=datetime(2026, 10, 1), updated=datetime(2026, 10, 2)):
    """An order as the renumbering left it: old status code, no status log, not saved since."""
    order = Order.objects.create()
    OrderStatusChange.objects.filter(order=order).delete()
    Order.objects.filter(pk=order.pk).update(status=status, created_at=created, updated_at=updated)
    return order


def run(*args):
    out = StringIO()
    call_command("convert_old_order_statuses", *args, stdout=out)
    return out.getvalue()


def statuses(orders):
    return [Order.objects.get(pk=o.pk).status for o in orders]


class ConvertOldOrderStatusesTest(TestCase):
    def test_converts_every_old_code(self):
        orders = [old_order(code) for code in range(6)]
        output = run("--before", BEFORE)
        self.assertIn("Converted: 6", output)
        self.assertEqual(statuses(orders), [Order.PENDING, Order.COLLECTING, Order.DELIVERING, Order.COMPLETED,
                                            Order.CANCELED, Order.READY_FOR_PICKUP])
        for order in orders:
            self.assertGreaterEqual(Order.objects.get(pk=order.pk).updated_at, CUT)
        self.assertFalse(OrderStatusChange.objects.exists())

    def test_second_run_changes_nothing(self):
        orders = [old_order(1), old_order(4)]
        run("--before", BEFORE)
        output = run("--before", BEFORE)
        self.assertIn("Nothing to convert", output)
        self.assertEqual(statuses(orders), [Order.COLLECTING, Order.CANCELED])

    def test_dry_run_writes_nothing(self):
        order = old_order(4)
        output = run("--before", BEFORE, "--dry-run")
        self.assertIn("Canceled (4) -> Canceled (6): 1", output)
        self.assertEqual(statuses([order]), [4])

    def test_newer_and_touched_orders_are_left_alone(self):
        new = Order.objects.create()                    # created after the renumbering
        Order.objects.filter(pk=new.pk).update(status=Order.COLLECTING, created_at=datetime(2026, 11, 3),
                                               updated_at=datetime(2026, 11, 3))
        saved_after = old_order(1, updated=datetime(2026, 11, 5))  # saved after it (new code or unknown)
        logged = old_order(2)                           # a status change after it wrote the log
        OrderStatusChange.objects.create(order=logged, from_status=Order.CONFIRMED, to_status=Order.COLLECTING)
        old = old_order(3)
        output = run("--before", BEFORE)
        self.assertIn("Converted: 1", output)
        self.assertEqual(statuses([new, saved_after, logged, old]),
                         [Order.COLLECTING, 1, 2, Order.COMPLETED])

    def test_default_time_is_the_migration(self):
        MigrationRecorder.Migration.objects.filter(
            app="service", name="0126_order_status_confirmed_and_log").update(applied=CUT)
        early, late = old_order(4), old_order(4, created=datetime(2026, 11, 5), updated=datetime(2026, 11, 5))
        output = run()
        self.assertIn("Renumbering time: 2026-11-02 12:43:09", output)
        self.assertEqual(statuses([early, late]), [Order.CANCELED, 4])
