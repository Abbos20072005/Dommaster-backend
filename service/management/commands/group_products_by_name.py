import re
import time
from collections import defaultdict, Counter
from difflib import SequenceMatcher
from django.db import transaction
from django.core.management.base import BaseCommand
from service.models import (
    Product, ProductVariantGroup, ProductVariantItem, ProductItemCategory,
)

DIMENSION_UNIT_MAP = {
    "A": "Ампераж (Ток)",
    "а": "Ампераж (Ток)",
    "V": "Напряжение",
    "в": "Напряжение",
    "W": "Мощность",
    "Вт": "Мощность",
    "кА": "Ток отключения",
    "кВт": "Мощность",
    "кВа": "Мощность",
    "мм": "Длина",
    "см": "Длина",
    "м": "Длина",
    "кг": "Вес",
    "г": "Вес",
    "HP": "Мощность",
    "dB": "Шум",
    "мл": "Объём",
    "л": "Объём",
    "дюйм": "Длина (дюйм)",
    "\"": "Длина (дюйм)",
    "P": "Полюс (P)",
    "п": "Полюс (P)",
    "K": "Температура (K)",
    "к": "Температура (K)",
    "Lm": "Световой поток (Лм)",
    "лм": "Световой поток (Лм)",
    "Hz": "Частота (Гц)",
    "Гц": "Частота (Гц)",
    "mA": "Ток (мА)",
    "ма": "Ток (мА)",
    "Nm": "Момент (Нм)",
    "нм": "Момент (Нм)",
    "bar": "Давление (бар)",
    "бар": "Давление (бар)",
}

SOCKET_PATTERN = re.compile(r"(?<!\w)([A-Za-z]+)(\d+(?:[.,]\d+)?)(?!\w)", re.IGNORECASE)

SOCKET_DIMENSIONS = {
    "e": "Цоколь (E)",
    "gu": "Цоколь (GU)",
    "g": "Цоколь (G)",
    "r": "Цоколь (R)",
    "par": "Тип лампы (PAR)",
    "mr": "Тип лампы (MR)",
}

NORMALIZE_PATTERNS = [
    (re.compile(r"\s+"), " "),
    (re.compile(r"\s*[–—-]\s*"), " "),
    (re.compile(r"\([^)]*\)"), ""),
    (re.compile(r"\s*/\s*"), "/"),
]

VALUE_PATTERN = re.compile(r"(\d+[.,]?\d*)\s*([A-Za-zА-Яа-я]+)", re.IGNORECASE)

DIMENSION_LABELS = {
    "ампераж": "Ампераж (Ток)",
    "ток": "Ампераж (Ток)",
    "напряжение": "Напряжение",
    "мощность": "Мощность",
    "длина": "Длина",
    "ширина": "Ширина",
    "высота": "Высота",
    "вес": "Вес",
    "объём": "Объём",
    "объем": "Объём",
    "цвет": "Цвет",
    "материал": "Материал",
    "полюс": "Полюс (P)",
    "температура": "Температура (K)",
    "световой поток": "Световой поток (Лм)",
}


def normalize_name(name):
    name = name.lower().strip()
    for pattern, repl in NORMALIZE_PATTERNS:
        name = pattern.sub(repl, name)
    return name.strip()


def extract_params(name):
    normalized = normalize_name(name)
    params = []
    for match in VALUE_PATTERN.finditer(normalized):
        num, unit = match.group(1), match.group(2)
        unit_lower = unit.lower()
        for map_key in DIMENSION_UNIT_MAP:
            if unit_lower == map_key.lower():
                label = DIMENSION_UNIT_MAP[map_key]
                params.append((f"{num}{unit}", label))
                break
    for match in SOCKET_PATTERN.finditer(normalized):
        letters, num = match.group(1), match.group(2)
        letters_lower = letters.lower()
        for map_key in SOCKET_DIMENSIONS:
            if letters_lower == map_key.lower():
                label = SOCKET_DIMENSIONS[map_key]
                params.append((f"{letters}{num}", label))
                break
    return params


def make_base_key(name, exclude_unit_label=None):
    normalized = normalize_name(name)
    if not exclude_unit_label:
        return normalized
    for match in VALUE_PATTERN.finditer(normalized):
        num, unit = match.group(1), match.group(2)
        for map_key in DIMENSION_UNIT_MAP:
            if unit.lower() == map_key.lower():
                label = DIMENSION_UNIT_MAP[map_key]
                if label == exclude_unit_label:
                    return normalized.replace(f"{num}{unit}", f"{{{label}}}", 1)
    for match in SOCKET_PATTERN.finditer(normalized):
        letters, num = match.group(1), match.group(2)
        for map_key in SOCKET_DIMENSIONS:
            if letters.lower() == map_key.lower():
                label = SOCKET_DIMENSIONS[map_key]
                if label == exclude_unit_label:
                    return normalized.replace(f"{letters}{num}", f"{{{label}}}", 1)
    return normalized


def resolve_dimension_label(raw_label):
    if not raw_label:
        return "Характеристика"
    lower = raw_label.lower().strip()
    for key, val in DIMENSION_LABELS.items():
        if key in lower:
            return val
    return raw_label


class Command(BaseCommand):
    help = (
        "Group products by extracting numeric specs from names (amperage, voltage, power, etc.) "
        "and creating ProductVariantGroup + ProductVariantItem per varying dimension."
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
            help="Only process specific product IDs",
        )
        parser.add_argument(
            "--min-group-size",
            type=int,
            default=2,
            help="Minimum products per group (default: 2)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        item_category_ids = options.get("item_category")
        product_ids = options.get("product_ids")
        min_group_size = options["min_group_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING(">>> DRY RUN — no changes will be made\n"))

        cat_qs = ProductItemCategory.objects.all()
        if item_category_ids:
            cat_qs = cat_qs.filter(id__in=item_category_ids)

        if not cat_qs.exists():
            self.stdout.write(self.style.WARNING("No item categories found."))
            return

        filter_product_ids = set(product_ids) if product_ids else None

        stats = {
            "categories_processed": 0,
            "products_processed": 0,
            "groups_created": 0,
            "items_created": 0,
            "products_already_grouped": 0,
        }

        start_time = time.time()

        for cat in cat_qs:
            self._process_category(cat, stats, dry_run, verbose, min_group_size, filter_product_ids)

        elapsed = time.time() - start_time
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  RESULTS"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Categories processed:    {stats['categories_processed']}")
        self.stdout.write(f"  Products processed:      {stats['products_processed']}")
        self.stdout.write(f"  Already in a group:      {stats['products_already_grouped']}")
        self.stdout.write(f"  Variant groups created:  {stats['groups_created']}")
        self.stdout.write(f"  Variant items created:   {stats['items_created']}")
        self.stdout.write(f"  Time elapsed:            {elapsed:.1f}s")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(">>> DRY RUN — no changes were made"))

    def _group_name(self, cat, dim_label, base_key):
        base_slug = re.sub(r'[^a-zа-я0-9]', '_', base_key[:60].strip().lower())
        base_slug = re.sub(r'_+', '_', base_slug).strip('_')[:40]
        return f"{cat.name} / {dim_label} ({base_slug})"

    def _process_category(self, cat, stats, dry_run, verbose, min_group_size, filter_product_ids=None):
        products = list(
            Product.objects.filter(
                product_item_category=cat,
                is_active=True,
            ).prefetch_related("variant_items").order_by("id")
        )

        if filter_product_ids:
            products = [p for p in products if p.id in filter_product_ids]

        if len(products) < min_group_size:
            return

        stats["categories_processed"] += 1
        stats["products_processed"] += len(products)

        already_grouped = {p.id for p in products if p.variant_items.exists()}
        stats["products_already_grouped"] += len(already_grouped)

        ungrouped = [p for p in products if p.id not in already_grouped]
        if len(ungrouped) < min_group_size:
            return

        product_params = {}
        for p in ungrouped:
            params = extract_params(p.name)
            if params:
                product_params[p.id] = params

        if not product_params:
            return

        param_label_counts = Counter()
        for params in product_params.values():
            for _, label in params:
                param_label_counts[label] += 1

        all_labels = {label for params in product_params.values() for _, label in params}
        variant_labels = []
        for label in all_labels:
            unique_values = set()
            for p in ungrouped:
                for matched, l in product_params.get(p.id, []):
                    if l == label:
                        unique_values.add(matched)
            if len(unique_values) >= min_group_size:
                variant_labels.append(label)

        for label in variant_labels:
            base_groups = defaultdict(list)
            for p in ungrouped:
                base_key = make_base_key(p.name, exclude_unit_label=label)
                variant_value = None
                for matched, l in product_params.get(p.id, []):
                    if l == label:
                        variant_value = matched.upper()
                        break
                if variant_value:
                    base_groups[base_key].append((p, variant_value))

            merged = self._merge_similar_bases(base_groups, 1.0)

            for base_key, entries in merged.items():
                if len(entries) < min_group_size:
                    continue

                dim_label = resolve_dimension_label(label)

                if dry_run:
                    stats["groups_created"] += 1
                    stats["items_created"] += len(entries)
                    if verbose:
                        self._print_group(dim_label, base_key, entries)
                    continue

                group_name = self._group_name(cat, dim_label, base_key)
                with transaction.atomic():
                    group, created = ProductVariantGroup.objects.get_or_create(
                        name=group_name,
                        defaults={"display_type": "text"},
                    )
                    if created:
                        stats["groups_created"] += 1

                    for product, variant_value in entries:
                        _, item_created = ProductVariantItem.objects.get_or_create(
                            group=group,
                            product=product,
                            defaults={"display_value": variant_value},
                        )
                        if item_created:
                            stats["items_created"] += 1

                    if verbose and entries:
                        self._print_group(dim_label, base_key, entries, group_id=group.id)

    def _merge_similar_bases(self, base_groups, threshold):
        keys = list(base_groups.keys())
        merged = {}
        used = set()

        for i, key_a in enumerate(keys):
            if key_a in used:
                continue
            cluster = list(base_groups[key_a])
            for j in range(i + 1, len(keys)):
                key_b = keys[j]
                if key_b in used:
                    continue
                ratio = SequenceMatcher(None, key_a, key_b).ratio()
                if ratio >= threshold:
                    cluster.extend(base_groups[key_b])
                    used.add(key_b)
            merged[key_a] = cluster
            used.add(key_a)

        return merged

    def _print_group(self, dim_label, base_key, entries, group_id=None):
        gid = f" (id={group_id})" if group_id else ""
        self.stdout.write(f"    Group: «{dim_label}»{gid}")
        for product, variant_value in entries:
            self.stdout.write(f"      [{variant_value}] {product.id}: {product.name[:80]}")
