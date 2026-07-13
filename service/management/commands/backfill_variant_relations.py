import time
import re
from collections import defaultdict
from django.db import transaction
from django.core.management.base import BaseCommand
from service.models import (
    Product, ProductCharacteristics, ProductVariantGroup,
    ProductVariantItem, ProductItemCategory,
)

VARIANT_DIMENSION_PATTERNS = {
    r"цвет|color|colour": "image",
    r"размер|size|р-р": "text",
    r"материал|material|ткань|fabric": "text",
    r"объем|volume|capacity": "text",
    r"длина|length": "text",
    r"ширина|width": "text",
    r"высота|height": "text",
    r"диаметр|diameter": "text",
    r"мощность|power|watt": "text",
}

VARIANT_DIMENSION_REGEXES = [
    (re.compile(pattern, re.IGNORECASE), display_type)
    for pattern, display_type in VARIANT_DIMENSION_PATTERNS.items()
]


def detect_variant_dimension(char_name):
    for regex, display_type in VARIANT_DIMENSION_REGEXES:
        if regex.search(char_name):
            return display_type
    return None


class Command(BaseCommand):
    help = (
        "Analyze products within each ProductItemCategory, find variant "
        "siblings (products that differ in only ONE variant dimension while "
        "sharing all others), and create the corresponding "
        "ProductVariantGroup + ProductVariantItem links so the frontend "
        "shows only genuinely related variants."
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
            help="Only consider these product IDs (space-separated)",
        )
        parser.add_argument(
            "--min-variants",
            type=int,
            default=2,
            help="Minimum number of variant siblings required to create a group (default: 2)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        item_category_ids = options.get("item_category")
        product_ids = options.get("product_ids")
        min_variants = options["min_variants"]

        if dry_run:
            self.stdout.write(self.style.WARNING(">>> DRY RUN — no changes will be made\n"))

        cats = ProductItemCategory.objects.all()
        if item_category_ids:
            cats = cats.filter(id__in=item_category_ids)

        total_cats = cats.count()
        if total_cats == 0:
            self.stdout.write(self.style.WARNING("No item categories found."))
            return

        self.stdout.write(f"Found {total_cats} item categories to analyze (min siblings: {min_variants})")
        self.stdout.write("")

        stats = {
            "categories_processed": 0,
            "categories_skipped": 0,
            "products_with_dims": 0,
            "products_without_dims": 0,
            "groups_created": 0,
            "items_created": 0,
            "items_skipped_duplicate": 0,
        }

        start_time = time.time()

        for cat_idx, cat in enumerate(cats, 1):
            self._process_category(cat, stats, dry_run, verbose, product_ids, min_variants, cat_idx, total_cats)

        elapsed = time.time() - start_time
        total_prods = stats["products_with_dims"] + stats["products_without_dims"]
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  RESULTS"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Categories processed:    {stats['categories_processed']}")
        self.stdout.write(f"  Categories skipped:      {stats['categories_skipped']}")
        self.stdout.write(f"  Products with dims:      {stats['products_with_dims']}")
        self.stdout.write(f"  Products without dims:   {stats['products_without_dims']}")
        self.stdout.write(f"  Variant groups created:  {stats['groups_created']}")
        self.stdout.write(f"  Variant items created:   {stats['items_created']}")
        self.stdout.write(f"  Duplicate items skipped: {stats['items_skipped_duplicate']}")
        self.stdout.write(f"  Time elapsed:            {elapsed:.1f}s")
        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(">>> DRY RUN — no changes were made"))

    def _process_category(self, cat, stats, dry_run, verbose, product_ids, min_variants, cat_idx, total_cats):
        products = Product.objects.filter(
            product_item_category=cat,
        ).prefetch_related("product_characteristics")

        if product_ids:
            products = products.filter(id__in=product_ids)

        products = list(products)
        if not products:
            stats["categories_skipped"] += 1
            return

        # Build dimension maps per product
        product_dims = {}
        for p in products:
            dims = {}
            for c in list(p.product_characteristics.all()):
                if not c.name or not c.value:
                    continue
                dt = detect_variant_dimension(c.name)
                if dt:
                    dims[c.name.strip()] = (c.value.strip(), dt)
            if dims:
                product_dims[p.id] = (p, dims)
                stats["products_with_dims"] += 1
            else:
                stats["products_without_dims"] += 1

        if len(product_dims) < 2:
            stats["categories_skipped"] += 1
            if verbose:
                self.stdout.write(f"  [{cat_idx}/{total_cats}] {cat.name} — SKIP ({len(product_dims)} products with dims, need >= 2)")
            return

        # Collect all unique dimension names across products in this category
        all_dim_names = set()
        for p_id, (p, dims) in product_dims.items():
            all_dim_names.update(dims.keys())

        # For each dimension, find sibling relationships
        dim_sibling_map = defaultdict(set)  # {dim_name: set of (product_id, display_value)}
        p_ids = list(product_dims.keys())

        for i, p_id in enumerate(p_ids):
            p, dims = product_dims[p_id]
            for dim_name, (val, dt) in dims.items():
                for j, other_id in enumerate(p_ids):
                    if other_id == p_id:
                        continue
                    other_p, other_dims = product_dims[other_id]
                    if dim_name not in other_dims:
                        continue
                    other_val = other_dims[dim_name][0]
                    if other_val == val:
                        continue

                    # Check all OTHER dimensions match
                    all_match = True
                    for d, (v, _) in dims.items():
                        if d == dim_name:
                            continue
                        if d not in other_dims or other_dims[d][0] != v:
                            all_match = False
                            break

                    if all_match:
                        dim_sibling_map[dim_name].add((p_id, val, dt))
                        dim_sibling_map[dim_name].add((other_id, other_val, dt))

        # Filter out dimensions that don't reach min_variants
        dim_name_products_count = {}
        for dim_name, siblings in dim_sibling_map.items():
            prod_ids_in_group = set(sid for sid, _, _ in siblings)
            if len(prod_ids_in_group) >= min_variants:
                dim_name_products_count[dim_name] = len(prod_ids_in_group)

        if not dim_name_products_count:
            stats["categories_skipped"] += 1
            if verbose:
                self.stdout.write(f"  [{cat_idx}/{total_cats}] {cat.name} — SKIP (no variant families found)")
            return

        stats["categories_processed"] += 1

        if verbose:
            dims_info = ", ".join(f"{dn}={cnt}" for dn, cnt in sorted(dim_name_products_count.items()))
            self.stdout.write(f"  [{cat_idx}/{total_cats}] {cat.name} — {len(product_dims)} products, dims: {dims_info}")

        if dry_run:
            for dim_name, siblings in dim_sibling_map.items():
                prod_ids_in_group = set(sid for sid, _, _ in siblings)
                if len(prod_ids_in_group) < min_variants:
                    continue
                group = ProductVariantGroup.objects.filter(name=dim_name).first()
                if group is None:
                    stats["groups_created"] += 1
                for p_id, val, dt in siblings:
                    exists = group is not None and ProductVariantItem.objects.filter(group=group, product_id=p_id).exists()
                    if exists:
                        stats["items_skipped_duplicate"] += 1
                    else:
                        stats["items_created"] += 1
                        if verbose:
                            p_name = product_dims[p_id][0].name[:30]
                            self.stdout.write(f"    [DRY] product {p_id} ({p_name}) → {dim_name}={val}")
        else:
            with transaction.atomic():
                for dim_name, siblings in dim_sibling_map.items():
                    prod_ids_in_group = set(sid for sid, _, _ in siblings)
                    if len(prod_ids_in_group) < min_variants:
                        continue

                    # Get display_type from any entry
                    sample_dt = next((dt for _, _, dt in siblings), "text")

                    group, created = ProductVariantGroup.objects.get_or_create(
                        name=dim_name,
                        defaults={"display_type": sample_dt},
                    )
                    if created:
                        stats["groups_created"] += 1
                    elif group.display_type != sample_dt:
                        group.display_type = sample_dt
                        group.save(update_fields=["display_type"])

                    for p_id, val, dt in siblings:
                        _, was_created = ProductVariantItem.objects.get_or_create(
                            group=group,
                            product_id=p_id,
                            defaults={"display_value": val},
                        )
                        if was_created:
                            stats["items_created"] += 1
                            if verbose:
                                p_name = product_dims[p_id][0].name[:30]
                                self.stdout.write(f"    product {p_id} ({p_name}) → {dim_name}={val}")
                        else:
                            stats["items_skipped_duplicate"] += 1
