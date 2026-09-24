import time
from collections import defaultdict
from django.db import transaction
from django.core.management.base import BaseCommand
from service.models import (
    Product, ProductCharacteristics, ProductVariantGroup,
    ProductVariantItem, ProductItemCategory,
)


def prompt_yes_no(question, default="y"):
    try:
        return input(f"{question} [y/N] ").strip().lower() == "y"
    except (EOFError, OSError):
        return default == "y"


class Command(BaseCommand):
    help = (
        "Scan ProductCharacteristics per item category, find characteristics "
        "that have 2+ distinct values (potential variant dimensions), and "
        "create ProductVariantGroup + ProductVariantItem."
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
            help="Only process these item category IDs",
        )
        parser.add_argument(
            "--product-ids",
            type=int,
            nargs="*",
            help="Only consider these product IDs",
        )
        parser.add_argument(
            "--no-confirm",
            action="store_true",
            help="Skip confirmation prompt before applying",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        item_category_ids = options.get("item_category")
        product_ids = options.get("product_ids")
        no_confirm = options["no_confirm"]

        if dry_run:
            self.stdout.write(self.style.WARNING(">>> DRY RUN — no changes will be made\n"))

        cat_base = ProductItemCategory.objects.all()
        if item_category_ids:
            cat_base = cat_base.filter(id__in=item_category_ids)

        if not cat_base.exists():
            self.stdout.write(self.style.WARNING("No item categories found."))
            return

        # Phase 1: discover potential variant dimensions per category
        all_candidates = []

        for cat in cat_base:
            products_qs = Product.objects.filter(product_item_category=cat)
            if product_ids:
                products_qs = products_qs.filter(id__in=product_ids)

            prod_ids = list(products_qs.values_list("id", flat=True))
            if len(prod_ids) < 2:
                continue

            # {char_name: set of distinct values}
            char_values = defaultdict(set)
            chars = ProductCharacteristics.objects.filter(
                product_id__in=prod_ids,
            ).values("product_id", "name", "value")

            for c in chars:
                if c["name"] and c["value"]:
                    char_values[c["name"]].add(c["value"].strip())

            # Keep only characteristics with 2+ distinct values
            candidates = [(name, sorted(vals)) for name, vals in char_values.items() if len(vals) >= 2]
            if candidates:
                all_candidates.append((cat, candidates))

        if not all_candidates:
            self.stdout.write(self.style.WARNING("No variant dimensions found (need >=2 distinct values per characteristic)."))
            return

        # Phase 2: show candidate list
        self.stdout.write(self.style.SUCCESS("\nDiscovered variant dimension candidates:"))
        self.stdout.write("")
        for cat, candidates in all_candidates:
            self.stdout.write(f"  [{cat.id}] {cat.name}")
            for name, vals in candidates:
                display_vals = ", ".join(vals[:6])
                if len(vals) > 6:
                    display_vals += "..."
                self.stdout.write(f"       - {name}  ({len(vals)} values: {display_vals})")
        self.stdout.write("")

        # Phase 3: confirm and apply
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run complete. Above dimensions would be created."))
            return

        if not no_confirm and not prompt_yes_no("Create variant groups and items for these dimensions?"):
            self.stdout.write("Cancelled.")
            return

        # Phase 4: create groups and items
        stats = {"groups_created": 0, "groups_existing": 0, "items_created": 0, "items_existing": 0}
        start_time = time.time()

        for cat, candidates in all_candidates:
            products_in_cat = list(
                Product.objects.filter(product_item_category=cat, is_active=True)
                .prefetch_related("product_characteristics")
            )
            if not products_in_cat:
                continue

            candidate_names = {name for name, _ in candidates}

            with transaction.atomic():
                for name, vals in candidates:
                    group, created = ProductVariantGroup.objects.get_or_create(
                        name=name,
                        defaults={"display_type": "text"},
                    )
                    if created:
                        stats["groups_created"] += 1
                    else:
                        stats["groups_existing"] += 1

                    for product in products_in_cat:
                        char_value = None
                        for c in list(product.product_characteristics.all()):
                            if c.name.strip() == name and c.value:
                                char_value = c.value.strip()
                                break

                        if char_value is None:
                            continue

                        _, was_created = ProductVariantItem.objects.get_or_create(
                            group=group,
                            product=product,
                            defaults={"display_value": char_value},
                        )
                        if was_created:
                            stats["items_created"] += 1
                        else:
                            stats["items_existing"] += 1

                    if verbose:
                        self.stdout.write(f"  {cat.name} → {name}: {len(vals)} values, "
                                          f"{stats['items_created'] + stats['items_existing']} items total")

        elapsed = time.time() - start_time
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  RESULTS"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Groups created:  {stats['groups_created']}")
        self.stdout.write(f"  Groups existing: {stats['groups_existing']}")
        self.stdout.write(f"  Items created:   {stats['items_created']}")
        self.stdout.write(f"  Items existing:  {stats['items_existing']}")
        self.stdout.write(f"  Time elapsed:    {elapsed:.1f}s")
