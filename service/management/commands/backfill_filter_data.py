import re
import time
from django.db import transaction
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from service.models import (
    Product, ProductCharacteristics, ProductItemCategoryFilterSchema,
    ProductFilterNumericValue, ProductItemCategory,
)

NUMERIC_UNITS = {"kg", "g", "l", "m", "sm", "cm", "mm", "kw", "w", "v", "a"}


def parse_numeric(raw_value):
    if not raw_value:
        return None
    cleaned = re.sub(r'[^\d.,]', '', str(raw_value)).replace(',', '.')
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def make_filter_key(name):
    return slugify(name, allow_unicode=True) or slugify(name, allow_unicode=False)


def detect_filter_type(schema, raw_value, unit, item_category):
    if schema.type_locked:
        return schema.type

    if unit and unit.lower() in NUMERIC_UNITS:
        return "range"

    existing_count = ProductFilterNumericValue.objects.filter(schema=schema).count()
    total_count = Product.objects.filter(
        product_item_category=item_category,
        is_active=True,
        filter_data__has_key=schema.key
    ).count() if schema.key else 0

    is_numeric = parse_numeric(raw_value) is not None

    if total_count == 0:
        return "range" if is_numeric else "checkbox"

    numeric_ratio = existing_count / max(total_count, 1)
    if is_numeric and numeric_ratio > 0.5:
        return "range"

    return "checkbox"


class Command(BaseCommand):
    help = (
        "Backfill filter schemas, numeric values and filter_data from existing "
        "ProductCharacteristics. Safe for production — uses batch transactions, "
        "dry-run mode, and supports incremental processing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without making any DB changes",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print per-product details",
        )
        parser.add_argument(
            "--item-category",
            type=int,
            nargs="*",
            help="Only process products in these item category IDs",
        )
        parser.add_argument(
            "--product-ids",
            type=int,
            nargs="*",
            help="Only process specific product IDs (space-separated)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of products to process per batch transaction (default: 500)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        item_category_ids = options.get("item_category")
        product_ids = options.get("product_ids")
        batch_size = options["batch_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING(">>> DRY RUN — no changes will be made\n"))

        qs = Product.objects.filter(
            product_item_category__isnull=False,
        ).prefetch_related("product_characteristics").order_by("id")

        if item_category_ids:
            qs = qs.filter(product_item_category_id__in=item_category_ids)
        if product_ids:
            qs = qs.filter(id__in=product_ids)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No products found to process."))
            return

        self.stdout.write(f"Found {total} products to process (batch size: {batch_size})")
        if item_category_ids:
            names = list(
                ProductItemCategory.objects.filter(id__in=item_category_ids)
                .values_list("name", flat=True)
            )
            self.stdout.write(f"  Item categories: {', '.join(names)}")
        self.stdout.write("")

        stats = {
            "products_processed": 0,
            "products_skipped_no_chars": 0,
            "schemas_created": 0,
            "schemas_type_updated": 0,
            "numeric_values_created": 0,
            "numeric_values_updated": 0,
            "filter_data_updated": 0,
        }

        start_time = time.time()
        batch_count = 0

        # Process in batches with iterator for memory efficiency
        product_batch = []
        for product in qs.iterator(chunk_size=batch_size):
            product_batch.append(product)
            if len(product_batch) >= batch_size:
                batch_count += 1
                self._process_batch(
                    product_batch, stats, dry_run, verbose, batch_count, total, start_time
                )
                product_batch = []

        # Process remaining
        if product_batch:
            batch_count += 1
            self._process_batch(
                product_batch, stats, dry_run, verbose, batch_count, total, start_time
            )

        elapsed = time.time() - start_time
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  RESULTS"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Products processed:     {stats['products_processed']}")
        self.stdout.write(f"  Products skipped:       {stats['products_skipped_no_chars']} (no characteristics)")
        self.stdout.write(f"  Schemas created:        {stats['schemas_created']}")
        self.stdout.write(f"  Schemas type updated:   {stats['schemas_type_updated']}")
        self.stdout.write(f"  Numeric values created: {stats['numeric_values_created']}")
        self.stdout.write(f"  Numeric values updated: {stats['numeric_values_updated']}")
        self.stdout.write(f"  Filter data updated:    {stats['filter_data_updated']}")
        self.stdout.write(f"  Time elapsed:           {elapsed:.1f}s")
        self.stdout.write(f"  Avg speed:              {total / max(elapsed, 1):.0f} prod/s")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(">>> DRY RUN — no changes were made"))

    def _process_batch(self, product_batch, stats, dry_run, verbose, batch_count, total, start_time):
        if dry_run:
            for product in product_batch:
                self._simulate_product(product, stats, verbose, dry_run=True)
        else:
            with transaction.atomic():
                for product in product_batch:
                    self._simulate_product(product, stats, verbose, dry_run=False)

        elapsed = time.time() - start_time
        done = batch_count * len(product_batch)
        rate = done / max(elapsed, 1)
        eta_remaining = (total - done) / max(rate, 1)
        self.stdout.write(
            f"  [{done}/{total}] Batch #{batch_count} done "
            f"({rate:.0f} prod/s, ETA: {eta_remaining:.0f}s)"
            f"{' [DRY]' if dry_run else ''}"
        )

    def _simulate_product(self, product, stats, verbose, dry_run=False):
        chars = list(product.product_characteristics.all())
        if not chars:
            stats["products_skipped_no_chars"] += 1
            if verbose:
                self.stdout.write(f"    SKIP product {product.id} ({product.name}) — no characteristics")
            return

        filter_data = {}
        for char in chars:
            if not char.name or not char.value:
                continue

            key = make_filter_key(char.name)
            item_category = product.product_item_category

            if dry_run:
                schema = ProductItemCategoryFilterSchema.objects.filter(
                    item_category=item_category, key=key
                ).first()
                created = schema is None
                if schema is None:
                    schema = ProductItemCategoryFilterSchema(
                        item_category=item_category,
                        key=key,
                        source_name_ru=char.name,
                        label=char.name,
                        label_uz=char.name,
                        label_ru=char.name,
                        label_en=char.name,
                        unit=char.unit or "",
                    )
            else:
                schema, created = ProductItemCategoryFilterSchema.objects.get_or_create(
                    item_category=item_category,
                    key=key,
                    defaults={
                        "source_name_ru": char.name,
                        "label": char.name,
                        "label_uz": char.name,
                        "label_ru": char.name,
                        "label_en": char.name,
                        "unit": char.unit or "",
                    }
                )

            if created:
                stats["schemas_created"] += 1

            detected_type = detect_filter_type(schema, char.value, char.unit, item_category)
            if detected_type != schema.type and not schema.type_locked:
                schema.type = detected_type
                if not dry_run:
                    schema.save(update_fields=["type"])
                stats["schemas_type_updated"] += 1

            if schema.type == "range":
                numeric_val = parse_numeric(char.value)
                if numeric_val is not None:
                    if dry_run:
                        exists = ProductFilterNumericValue.objects.filter(
                            product=product, schema=schema
                        ).exists()
                        stats["numeric_values_created" if not exists else "numeric_values_updated"] += 1
                    else:
                        _, was_created = ProductFilterNumericValue.objects.update_or_create(
                            product=product, schema=schema,
                            defaults={"value": numeric_val}
                        )
                        if was_created:
                            stats["numeric_values_created"] += 1
                        else:
                            stats["numeric_values_updated"] += 1
            else:
                filter_data[key] = slugify(char.value, allow_unicode=True) or char.value

        if filter_data:
            if not dry_run:
                Product.objects.filter(id=product.id).update(filter_data=filter_data)
            stats["filter_data_updated"] += 1

        stats["products_processed"] += 1

        if verbose:
            char_summary = ", ".join(f"{c.name}={c.value}" for c in chars[:5])
            extra = "..." if len(chars) > 5 else ""
            self.stdout.write(
                f"    {'[DRY] ' if dry_run else ''}OK product {product.id} "
                f"({product.name[:40]}) — {len(chars)} chars [{char_summary}{extra}]"[:200]
            )
