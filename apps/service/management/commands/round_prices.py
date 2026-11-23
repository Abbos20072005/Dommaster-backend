from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.service.models import Product
from utils.price import PRICE_STEP, round_price_up

BATCH = 500


class Command(BaseCommand):
    help = (f"Round the stored product prices (price, discount_price) up to {PRICE_STEP} so'm - the prices written "
            "before Product.save() / the 1C price list started rounding them. Safe to run again.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only list the changes, save nothing.")

    def handle(self, *args, **options):
        changed = []
        now = timezone.now()
        rows = Product.objects.order_by("id").values_list("id", "name_ru", "price", "discount_price")
        for pk, name, price, discount_price in rows.iterator(chunk_size=2000):
            new_price, new_discount = round_price_up(price), round_price_up(discount_price)
            if new_price == price and new_discount == discount_price:
                continue
            changed.append(Product(id=pk, price=new_price, discount_price=new_discount, updated_at=now))
            line = f"  {pk} {name!r}: {price:.2f} -> {new_price:.0f}"
            if new_discount != discount_price:
                line += f", discount_price {discount_price:.2f} -> {new_discount:.0f}"
            self.stdout.write(line)

        if not options["dry_run"] and changed:
            # bulk_update skips save() and auto_now: updated_at is set by hand (the site's Last-Modified)
            with transaction.atomic():
                Product.objects.bulk_update(changed, ["price", "discount_price", "updated_at"], batch_size=BATCH)

        self.stdout.write("")
        self.stdout.write(f"  products rounded: {len(changed)}")
        self.stdout.write(self.style.SUCCESS("DRY RUN finished, nothing saved" if options["dry_run"] else "Done"))
