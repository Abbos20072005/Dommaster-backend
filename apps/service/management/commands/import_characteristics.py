import csv
import re
from collections import Counter, defaultdict, namedtuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from django.utils import timezone, translation

from apps.service.models import (
    ProductAttribute, ProductAttributeOption, ProductAttributeValue, ProductCharacteristics,
    ProductItemCategoryAttribute, ProductItemCategoryFilterSchema,
)
from apps.service.product_filters import clear_category_filter_cache

# a new attribute becomes a `list` when its values repeat: at most this many different ones
LIST_MAX_VALUES = 20
BOOLEAN_VALUES = {"да": "true", "нет": "false"}
NUMBER_RE = re.compile(r"^-?\d+(?:[.,]\d+)?$")
# "10 А", "0,75 кВт", "180°": a number followed by a short unit without digits
NUMBER_UNIT_RE = re.compile(r"^(-?\d+(?:[.,]\d+)?)\s*((?:[^\W\d_]|[°%])[^\d]{0,11})$")
SAMPLES = 15

Row = namedtuple("Row", "id product_id category_id key name value unit value_uz")


def clean(text):
    return " ".join((text or "").split())


def clean_value(text):
    # "Китай." and "Китай" are one value
    return clean(text).rstrip(" .")


def text_value(value, unit):
    return f"{value} {unit}".strip()[:255]


def split_number(value, unit):
    """("10 А", "") / ("10", "А") -> ("10", "А"); None when the value is not a number with a unit."""
    if unit:
        return (value, unit) if NUMBER_RE.match(value) else None
    match = NUMBER_UNIT_RE.match(value)
    return (match.group(1), match.group(2).rstrip(". ")) if match else None


def detect_type(rows):
    """Value type (and unit) of a new attribute, by every characteristic that has its name."""
    if all(row.value.lower() in BOOLEAN_VALUES for row in rows):
        return ProductAttribute.BOOLEAN, ""

    numbers = [split_number(row.value, row.unit) for row in rows]
    if all(numbers):
        units = Counter(unit for _, unit in numbers)
        if len({unit.lower() for unit in units}) == 1:
            return ProductAttribute.NUMBER, units.most_common(1)[0][0]

    distinct = len({text_value(row.value, row.unit).lower() for row in rows})
    if distinct <= LIST_MAX_VALUES and len(rows) >= 2 * distinct:
        return ProductAttribute.LIST, ""
    return ProductAttribute.TEXT, ""


class Command(BaseCommand):
    help = (
        "Turn the raw characteristics (ProductCharacteristics, written by 1C) into attributes: one global "
        "attribute per characteristic name, attached to the item categories it occurs in, and an attribute "
        "value per product. Takes only the rows it has not processed yet, so it is safe to run again (cron); "
        "a product's existing attribute value is never overwritten."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Roll everything back at the end")
        parser.add_argument("--all", action="store_true",
                            help="Also take the rows processed before (values deleted in the admin panel come back)")
        parser.add_argument("--item-category", type=int, nargs="*", help="Only products of these item categories")
        parser.add_argument("--product-ids", type=int, nargs="*", help="Only these products")
        parser.add_argument("--report", help="Write a CSV with one line per attribute to this path")

    def handle(self, *args, **options):
        self.options = options
        self.stats = Counter()
        self.report = defaultdict(Counter)
        self.mismatches = []
        self.touched_item_categories = set()
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN - everything below is rolled back at the end"))

        # translated fields: `name` / `value` are written as the ru ones
        with translation.override("ru"), transaction.atomic():
            by_key, pending = self.load_rows()
            attributes = self.get_attributes(by_key, pending)
            self.import_values(pending, attributes)
            # bulk_create sends no signals
            clear_category_filter_cache(*self.touched_item_categories)
            if options["dry_run"]:
                transaction.set_rollback(True)

        self.finish(by_key, attributes)

    def load_rows(self):
        """Every characteristic by its normalized name (type detection) + the ones to import now."""
        take_all = self.options["all"]
        item_categories = set(self.options["item_category"] or ())
        products = set(self.options["product_ids"] or ())

        by_key, pending, empty = defaultdict(list), [], []
        queryset = ProductCharacteristics.objects.filter(product__isnull=False).order_by("id").values_list(
            "id", "product_id", "product__product_item_category_id", "name_ru", "name_uz",
            "value_ru", "value_uz", "unit_ru", "unit_uz", "imported_at",
        )
        for pk, product_id, category_id, name_ru, name_uz, value_ru, value_uz, unit_ru, unit_uz, imported_at \
                in queryset.iterator(chunk_size=5000):
            name, value = clean(name_ru or name_uz), clean_value(value_ru or value_uz)
            is_pending = (take_all or imported_at is None) \
                and (not item_categories or category_id in item_categories) \
                and (not products or product_id in products)
            if not name or not value:
                if is_pending:
                    empty.append(pk)
                continue

            row = Row(pk, product_id, category_id, name.lower(), name, value, clean(unit_ru or unit_uz),
                      clean_value(value_uz) if value_ru else "")
            by_key[row.key].append(row)
            if not is_pending:
                continue
            if category_id is None:
                # stays unprocessed: it is imported once the product gets an item category
                self.stats["skipped: product without an item category"] += 1
            else:
                pending.append(row)

        self.stats["skipped: empty name or value"] = len(empty)
        self.mark_imported(empty)
        self.stats["characteristics to import"] = len(pending)
        return by_key, pending

    def get_attributes(self, by_key, pending):
        """Attribute of every characteristic name to import: an existing one (same ru name) or a new one."""
        attributes = {}
        for attribute in ProductAttribute.objects.order_by("id"):
            attributes.setdefault(clean(attribute.name_ru).lower(), attribute)

        new = []
        for key in sorted({row.key for row in pending}):
            if key in attributes:
                self.stats["attributes reused"] += 1
                continue
            rows = by_key[key]
            value_type, unit = detect_type(rows)
            distinct = len({text_value(row.value, row.unit).lower() for row in rows})
            name = Counter(row.name for row in rows).most_common(1)[0][0]
            attribute = ProductAttribute(
                name_ru=name, name_uz=name, value_type=value_type, unit=unit,
                # a text that differs in nearly every product (model, articul) is no filter
                is_filterable=value_type != ProductAttribute.TEXT or distinct * 2 <= len(rows),
            )
            new.append(attribute)
            attributes[key] = attribute
            self.stats[f"attributes created: {value_type}"] += 1

        ProductAttribute.objects.bulk_create(new, batch_size=500)
        self.new_attribute_ids = {attribute.pk for attribute in new}
        return attributes

    def get_options(self, pending, attributes):
        """Options of the `list` attributes by lowered ru value, with the missing ones created (most used first)."""
        wanted = defaultdict(Counter)
        for row in pending:
            attribute = attributes[row.key]
            if attribute.value_type == ProductAttribute.LIST:
                wanted[attribute][text_value(row.value, row.unit)[:150]] += 1

        options = defaultdict(dict)
        for option in ProductAttributeOption.objects.filter(attribute__in=[attribute.pk for attribute in wanted]):
            options[option.attribute_id][clean(option.value_ru).lower()] = option

        new = []
        for attribute, spellings in wanted.items():
            known = options[attribute.pk]
            position = max((option.position for option in known.values()), default=-1)
            # "Сталь" x100 and "сталь" x3 are one option, spelled the way most rows spell it
            for spelling, _ in spellings.most_common():
                if spelling.lower() not in known:
                    position += 1
                    known[spelling.lower()] = ProductAttributeOption(
                        attribute=attribute, value_ru=spelling, value_uz=spelling, position=position)
                    new.append(known[spelling.lower()])
        ProductAttributeOption.objects.bulk_create(new, batch_size=1000)
        self.stats["options created"] = len(new)
        return options

    def convert(self, attribute, row, options):
        """Characteristic -> (value_ru, value_uz) of the attribute's type; None when it does not fit the type."""
        if attribute.value_type == ProductAttribute.BOOLEAN:
            value = BOOLEAN_VALUES.get(row.value.lower())
            return (value, value) if value else None

        if attribute.value_type == ProductAttribute.NUMBER:
            if NUMBER_RE.match(row.value) and not row.unit:
                number = row.value
            else:
                number, unit = split_number(row.value, row.unit) or (None, None)
                if number is None or unit.lower() != attribute.unit.lower():
                    return None
            number = number.replace(",", ".")
            return number, number

        value = text_value(row.value, row.unit)
        if attribute.value_type == ProductAttribute.LIST:
            option = options[attribute.pk][value[:150].lower()]
            return option.value_ru, option.value_uz
        return value, text_value(row.value_uz, row.unit) if row.value_uz else value

    def import_values(self, pending, attributes):
        options = self.get_options(pending, attributes)
        pairs = set(ProductAttributeValue.objects.values_list("product_id", "attribute_id"))
        links = set(ProductItemCategoryAttribute.objects.values_list("item_category_id", "attribute_id"))
        positions = dict(ProductItemCategoryAttribute.objects.values("item_category_id")
                         .annotate(last=Max("position")).values_list("item_category_id", "last"))
        # the quick filters of the old filter schemas move to the category's attribute
        quick_filters = {
            (item_category_id, clean(name).lower()): limit
            for item_category_id, name, limit in ProductItemCategoryFilterSchema.objects
            .filter(is_quick_filter=True).values_list("item_category_id", "source_name_ru", "max_quick_filters")
        }

        new_values, new_links, processed = [], [], []
        for row in pending:
            attribute = attributes[row.key]
            report = self.report[attribute.pk]
            report["rows"] += 1
            processed.append(row.id)

            value = self.convert(attribute, row, options)
            if value is None:
                report["skipped"] += 1
                self.stats["skipped: value does not fit the attribute's type"] += 1
                if len(self.mismatches) < SAMPLES:
                    self.mismatches.append(f"{attribute.name_ru} ({attribute.value_type} {attribute.unit}".strip()
                                           + f"): {text_value(row.value, row.unit)!r}, product {row.product_id}")
                continue

            if (row.product_id, attribute.pk) in pairs:
                report["skipped"] += 1
                self.stats["skipped: the product already has a value"] += 1
            else:
                pairs.add((row.product_id, attribute.pk))
                new_values.append(ProductAttributeValue(
                    product_id=row.product_id, attribute=attribute, value_ru=value[0], value_uz=value[1],
                    value_number=ProductAttributeValue.number_of(attribute, value[0]),
                ))
                report["values"] += 1
                self.touched_item_categories.add(row.category_id)

            if (row.category_id, attribute.pk) not in links:
                links.add((row.category_id, attribute.pk))
                positions[row.category_id] = positions.get(row.category_id, -1) + 1
                limit = quick_filters.get((row.category_id, row.key))
                new_links.append(ProductItemCategoryAttribute(
                    item_category_id=row.category_id, attribute=attribute, position=positions[row.category_id],
                    is_quick_filter=limit is not None, max_quick_filters=limit or 0,
                ))
                report["item categories"] += 1
                self.touched_item_categories.add(row.category_id)

        ProductItemCategoryAttribute.objects.bulk_create(new_links, batch_size=1000)
        ProductAttributeValue.objects.bulk_create(new_values, batch_size=2000)
        self.mark_imported(processed)
        self.stats["category attributes created"] = len(new_links)
        self.stats["quick filters moved"] = sum(link.is_quick_filter for link in new_links)
        self.stats["values created"] = len(new_values)

    def mark_imported(self, ids):
        now = timezone.now()
        for start in range(0, len(ids), 5000):
            ProductCharacteristics.objects.filter(id__in=ids[start:start + 5000]).update(imported_at=now)

    def finish(self, by_key, attributes):
        if self.options["report"]:
            self.write_report(by_key, attributes)

        self.stdout.write("")
        for label, count in sorted(self.stats.items()):
            self.stdout.write(f"  {label}: {count}")
        if self.mismatches:
            self.stdout.write(self.style.WARNING("  Values that do not fit (first ones):"))
            for line in self.mismatches:
                self.stdout.write(f"    {line}")
        self.stdout.write(self.style.SUCCESS(
            "DRY RUN finished, nothing saved" if self.options["dry_run"] else "Done"))

    def write_report(self, by_key, attributes):
        with open(self.options["report"], "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["attribute", "state", "value_type", "unit", "is_filterable", "rows", "values created",
                             "skipped", "item categories attached", "different values", "values (sample)"])
            lines = []
            for key, attribute in attributes.items():
                report = self.report.get(attribute.pk)
                if not report:
                    continue
                values = Counter(text_value(row.value, row.unit) for row in by_key[key])
                lines.append([
                    attribute.name_ru, "new" if attribute.pk in self.new_attribute_ids else "existing",
                    attribute.value_type, attribute.unit, attribute.is_filterable, report["rows"], report["values"],
                    report["skipped"], report["item categories"], len(values),
                    " | ".join(value for value, _ in values.most_common(8)),
                ])
            writer.writerows(sorted(lines, key=lambda line: -line[5]))
        self.stdout.write(f"Report: {self.options['report']}")
