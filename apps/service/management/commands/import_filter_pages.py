"""Filter landing pages (FilterPage) from the agreed keyword list: one row = one page.

Columns (first row, any order; .xlsx first sheet or .csv UTF-8):
  keyword_ru (required), keyword_uz, search_volume, item_category / sub_category / category (id or slug; the most
  specific filled one is the page's level — "Knauf" + a sub category = a brand x category page), brand (id or name),
  filters (item category pages only: "Name ru = value | value; Number name ru = 2.5..4", a number: "4" exact,
  "2..", "..4"),
  slug, title_ru, title_uz, meta_title_ru, meta_title_uz, meta_description_ru, meta_description_uz, text_ru, text_uz.
A row whose combination already has a page updates it (only non-empty cells); a new page without `text_ru` is
created inactive. Rows below --min-volume searches a month are skipped.
"""
import csv
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.service import filter_pages

from apps.service.models import (
    Brand, FilterPage, ProductAttribute, ProductCategory, ProductItemCategory, ProductItemCategoryAttribute,
    ProductSubCategory,
)

LEVEL_MODELS = {"item_category": ProductItemCategory, "sub_category": ProductSubCategory,
                "category": ProductCategory}

TEXT_FIELDS = ("keyword_uz", "title_ru", "title_uz", "meta_title_ru", "meta_title_uz", "meta_description_ru",
               "meta_description_uz", "text_ru", "text_uz")


def read_rows(path):
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as file:
            return [{(key or "").strip(): (value or "").strip() for key, value in row.items()}
                    for row in csv.DictReader(file)]
    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = [str(cell or "").strip() for cell in next(rows, [])]
    return [{key: str(cell).strip() if cell is not None else "" for key, cell in zip(header, row)}
            for row in rows if any(cell not in (None, "") for cell in row)]


def parse_number(text):
    text = text.strip().replace(",", ".")
    return float(text) if text else None


def parse_filters(item_category, text):
    """"Name = a | b; Other = 2..4" -> {"<attribute id>": ["a", "b"], "<id>": {"min": 2, "max": 4}}."""
    attributes = {
        link.attribute.name_ru.strip().lower(): link.attribute
        for link in ProductItemCategoryAttribute.objects.filter(item_category=item_category).select_related("attribute")
    }
    filters = {}
    for part in filter(None, (part.strip() for part in text.split(";"))):
        name, separator, value = part.partition("=")
        attribute = attributes.get(name.strip().lower())
        if not separator or attribute is None:
            raise filter_pages.FilterPageError(f"{part}: no such attribute in the item category.")
        if attribute.value_type == ProductAttribute.NUMBER:
            low, dots, high = value.partition("..")
            try:
                low, high = parse_number(low), parse_number(high) if dots else parse_number(low)
            except ValueError:
                raise filter_pages.FilterPageError(f"{part}: not a number.")
            filters[str(attribute.id)] = {"min": low, "max": high}
        else:
            filters[str(attribute.id)] = [item.strip() for item in value.split("|")]
    return filters


class Command(BaseCommand):
    help = "Create / update filter landing pages from the keyword list (.xlsx or .csv)."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the list (.xlsx or .csv).")
        parser.add_argument("--min-volume", type=int, default=FilterPage.MIN_SEARCH_VOLUME,
                            help="Skip rows searched fewer times a month (default %(default)s).")
        parser.add_argument("--dry-run", action="store_true", help="Roll everything back at the end")

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"{path}: no such file.")
        rows = read_rows(path)
        created, updated, skipped, pages = 0, 0, [], []

        with transaction.atomic():
            for number, row in enumerate(rows, start=2):
                try:
                    page, is_new = self.apply_row(row, options["min_volume"])
                except filter_pages.FilterPageError as error:
                    skipped.append(f"row {number}: {error}")
                    continue
                pages.append(page)
                created += is_new
                updated += not is_new

            filter_pages.refresh_counts(pages)
            closed = [page for page in pages if page.products_count < FilterPage.MIN_PRODUCTS]

            self.stdout.write(f"rows: {len(rows)}, created: {created}, updated: {updated}, skipped: {len(skipped)}")
            for line in skipped:
                self.stdout.write(f"  skipped {line}")
            if closed:
                self.stdout.write(f"fewer than {FilterPage.MIN_PRODUCTS} products (page stays closed): {len(closed)}")
                for page in closed:
                    self.stdout.write(f"  {page.slug}: {page.products_count}")
            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write("dry run: rolled back")

    def apply_row(self, row, min_volume):
        keyword = row.get("keyword_ru", "")
        if not keyword:
            raise filter_pages.FilterPageError("keyword_ru is empty.")
        volume = row.get("search_volume", "")
        volume = int(float(volume)) if volume.replace(".", "", 1).isdigit() else 0
        if volume < min_volume:
            raise filter_pages.FilterPageError(f"{keyword}: {volume} searches a month.")

        level, node = self.node(row)
        brand = self.brand(row.get("brand", ""))
        filters_text = row.get("filters", "")
        if filters_text and level != filter_pages.ITEM_CATEGORY:
            raise filter_pages.FilterPageError(f"{keyword}: filters are only for an item category page.")
        filters = parse_filters(node, filters_text) if filters_text else {}
        try:
            filters = filter_pages.clean_page(level, node.id, brand.id if brand else None, filters)
        except filter_pages.FilterPageError as error:
            raise filter_pages.FilterPageError(f"{keyword}: {error}")

        page = FilterPage.objects.filter(
            combination_hash=filter_pages.combination_hash(level, node.id, brand.id if brand else None, filters),
        ).first()
        is_new = page is None
        if is_new:
            page = FilterPage(**{level: node}, brand=brand, filters=filters,
                              title_ru=keyword[:1].upper() + keyword[1:], is_active=bool(row.get("text_ru")))
        slug = row.get("slug", "")
        if slug and FilterPage.objects.filter(slug=slug).exclude(pk=page.pk).exists():
            raise filter_pages.FilterPageError(f"{keyword}: slug {slug} is taken.")

        page.keyword_ru, page.search_volume = keyword, volume
        page.slug = slug or page.slug
        for field in TEXT_FIELDS:
            if row.get(field):
                setattr(page, field, row[field])
        page.save()
        return page, is_new

    @staticmethod
    def node(row):
        """(level, category object) of the most specific filled level column."""
        for level, model in LEVEL_MODELS.items():
            value = row.get(level, "")
            if not value:
                continue
            lookup = Q(id=int(value)) if value.isdigit() else Q(slug_ru=value) | Q(slug_uz=value)
            node = model.objects.filter(lookup).first()
            if node is None:
                raise filter_pages.FilterPageError(f"{level} {value!r} not found.")
            return level, node
        raise filter_pages.FilterPageError("none of item_category / sub_category / category is filled.")

    @staticmethod
    def brand(value):
        if not value:
            return None
        brand = Brand.objects.filter(**({"id": int(value)} if value.isdigit() else {"name__iexact": value})).first()
        if brand is None:
            raise filter_pages.FilterPageError(f"brand {value!r} not found.")
        return brand
