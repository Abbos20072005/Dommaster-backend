import io
import re
from collections import Counter

import openpyxl
import requests
from PIL import Image
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import translation
from django.utils.html import linebreaks

from apps.service.models import (
    Brand, Product, ProductCategory, ProductCharacteristics, ProductImage, ProductItemCategory, ProductSubCategory,
)
from apps.service.models.choices import PUBLISH_STATUS_DRAFT

from .apply_audit_corrections import clean, named

# A supplier price list / a content team sheet of new products: category, name, unit, price, description and
# characteristics as "Name: value" lines (or "Name | value | unit" ones). 1C knows nothing about these products:
# they get no product_code, so a product 1C sends later under its own code becomes a second card - put the 1C
# code into the product first.
# The category is either one "Категория" column = the item category name, or the whole path in "Категория" /
# "Подкатегория" / "Предметная категория" (--create-categories makes the levels that are missing).
# The brand is --brand, else the row's "Бренд" column, else its "Марка" / "Бренд" characteristic.
# The content team's two-language sheet ("Nomi (uz)" / "Название (ru)", "Kategoriya (uz)" / "Категория (ru)", ...,
# "Narx (USD)+5%", "Artikul", "Brend", "Rasm havolasi") works too: uz texts go to the *_uz fields, the dollar price
# is multiplied by --usd-rate, the picture of the link is downloaded after the products are saved.

# A header matches a name exactly (the first name of the list wins), else by its text before " (".
COLUMNS = {
    "category": ("Категория",),
    "sub_category": ("Подкатегория",),
    "item_category": ("Предметная категория",),
    "name": ("Наименование", "Товар (параметр)", "Товар", "Название"),
    "unit": ("Ед. изм.", "Ед.изм.", "Единица измерения", "O‘lchov birligi", "O'lchov birligi"),
    "price": ("Цена", "Цена (сум)", "Цена (сум.)", "Цена, сум", "Цена, UZS"),
    # a dollar price: price = round(USD × --usd-rate); the "+5%" column (the markup already added) comes first
    "price_usd": ("Narx (USD)+5%", "Narx (USD)"),
    "short_description": ("Краткое описание",),
    "description": ("Описание",),
    # "Характеристики (Характеристика | Значение | Единица)": a header is also matched by its text before " ("
    "characteristics": ("Характеристики", "Характеристика"),
    "brand": ("Бренд", "Brend"),
    "articul": ("Артикул", "Artikul"),
    # a direct link to the picture: downloaded after the products are saved, becomes the main image
    "image_url": ("Rasm havolasi",),
    # the uz texts of the content team's two-language sheets ("Nomi (uz)" / "Название (ru)" ...)
    "name_uz": ("Nomi",),
    "category_uz": ("Kategoriya",),
    "sub_category_uz": ("Subkategoriya",),
    "item_category_uz": ("Predmet kategoriya",),
    "short_description_uz": ("Qisqa tavsif",),
    "description_uz": ("Tavsif",),
}
BRAND_CHARACTERISTICS = {"марка", "бренд"}
# the "no unit" mark of the "Name | value | unit" lines
NO_UNIT = {"—", "–", "-"}
TAG_RE = re.compile(r"<[a-zA-Z/][^>]*>")
UNITS = {"шт": "pcs", "кг": "kg", "л": "l", "м": "m", "г": "g", "см": "sm", "уп": "pkg", "упак": "pkg",
         "компл": "set", "набор": "set", "dona": "pcs", "qadoq": "pkg", "metr": "m", "komplekt": "set"}
IMAGE_MAX_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}
# "…для полых стен, артикул UKG10-068-045-000-P-UO." / "…для твёрдых стен Артикул: UKT10-068-060-000-A-S-UO"
ARTICUL_RE = re.compile(r"[\s,]*артикул:?\s*([\w./-]+?)\.?$", re.IGNORECASE)
# several characteristics typed on one line, far apart: "Высота C: 4,0 м               Высота D: 2,5 м"
GAP_RE = re.compile(r"\s{3,}")


def parse_characteristics(text):
    """"Name: value" / "Name | value | unit" lines -> [(name, value, unit)], in their order."""
    pairs = []
    for line in str(text or "").splitlines():
        if "|" in line:
            parts = line.split("|")
            pieces = [(parts[0], parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else "")]
        else:
            pieces = [(*piece.partition(":")[::2], "") for piece in GAP_RE.split(line)]
        for name, value, unit in pieces:
            name, value, unit = clean(name), clean(value), clean(unit)
            if unit in NO_UNIT:
                unit = ""
            if name and value:
                pairs.append((name[:150], value[:150], unit[:150]))
    return pairs


def download_image(url):
    """(file name extension, bytes) of the picture at the link; raises ValueError when it is not one."""
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (compatible; catalog-import)"})
    if response.status_code != 200:
        raise ValueError(f"HTTP {response.status_code}")
    data = response.content
    if len(data) > IMAGE_MAX_BYTES:
        raise ValueError(f"{len(data)} bytes, more than {IMAGE_MAX_BYTES}")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            kind = image.format
    except Exception:
        raise ValueError(f"not a picture ({response.headers.get('Content-Type', '?')})")
    if kind not in IMAGE_TYPES:
        raise ValueError(f"picture type {kind}")
    return IMAGE_TYPES[kind], data


def html_text(text):
    """A plain text description -> paragraphs (as the content import does); HTML stays as sent."""
    text = str(text or "").strip()
    if not text or TAG_RE.search(text):
        return text
    return linebreaks(text)


class Command(BaseCommand):
    help = (
        "Create the products of a price list sheet (category, name, unit, price, description, characteristics). "
        "Products are created hidden, as drafts, without a 1C code; the characteristics become attribute "
        "values (import_characteristics). The category is an item category name or the category / sub category "
        "/ item category path. Run with --dry-run first."
    )

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the workbook (.xlsx).")
        parser.add_argument("--sheet", help="Sheet to read (default: the first one).")
        parser.add_argument(
            "--usd-rate",
            type=float,
            help='So\'m per dollar for a sheet with a "Narx (USD)" price column: price = round(USD × rate).',
        )
        parser.add_argument(
            "--brand",
            help='Brand of every product (created hidden when missing). Without it: the "Бренд" column, else the '
                 '"Марка" / "Бренд" characteristic of the row.',
        )
        parser.add_argument(
            "--map",
            nargs="+",
            default=[],
            metavar="CATEGORY=ID",
            help='Item category id for a value of the "Категория" column that is not an item category name.',
        )
        parser.add_argument(
            "--create-in",
            type=int,
            metavar="SUB_CATEGORY_ID",
            help='Create an item category for a "Категория" value that is neither an item category nor in --map, '
                 "in this sub category (ru name only).",
        )
        parser.add_argument(
            "--create-categories",
            action="store_true",
            help='Path sheets ("Подкатегория" / "Предметная категория" columns): create the levels of a path that '
                 "are missing (ru name only, no image; a new top category is hidden).",
        )
        parser.add_argument("--active", action="store_true", help="Create the products active (default: hidden).")
        parser.add_argument("--dry-run", action="store_true", help="Roll everything back at the end.")

    def handle(self, *args, **options):
        self.stats = Counter()
        self.category_map = self.parse_map(options["map"])
        self.item_categories = {}
        self.paths = {}
        self.brands = {}
        self.create_in = options["create_in"]
        self.create_categories = options["create_categories"]
        if self.create_in and not ProductSubCategory.objects.filter(pk=self.create_in).exists():
            raise CommandError(f"--create-in: no sub category {self.create_in}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN - everything below is rolled back at the end"))

        self.usd_rate = options["usd_rate"]
        rows = self.read_rows(options["file"], options["sheet"])
        if self.has_usd_price and not self.usd_rate:
            raise CommandError('The sheet has a dollar price column ("Narx (USD)"): pass --usd-rate')
        self.stdout.write(f"Rows: {len(rows)}")
        images = []
        with translation.override("ru"), transaction.atomic():
            brand = self.get_brand(clean(options["brand"])) if clean(options["brand"]) else None
            created = []
            taken = {clean(name).lower() for name in Product.objects.values_list("name_ru", flat=True)}
            for row in rows:
                product = self.create_product(row, brand, options["active"], taken)
                if product:
                    created.append(product.pk)
                    if clean(row["image_url"]):
                        images.append((product.pk, clean(row["image_url"])))
            if created:
                out = io.StringIO()
                call_command("import_characteristics", product_ids=created, stdout=out)
                self.stats["attribute values created"] = int(
                    re.search(r"values created: (\d+)", out.getvalue()).group(1))
            if options["dry_run"]:
                transaction.set_rollback(True)
        self.stats["products without an image link"] = len(created) - len(images)
        # after the commit: a slow / broken link must not hold the transaction, a failed one leaves the card
        # without a picture
        self.load_images(images, options["dry_run"])

        self.stdout.write("")
        for label, count in self.stats.items():
            self.stdout.write(f"  {label}: {count}")
        if created and not options["dry_run"]:
            self.stdout.write(f"  created ids: {' '.join(map(str, created))}")
        self.stdout.write(self.style.SUCCESS("DRY RUN finished, nothing saved" if options["dry_run"] else "Done"))

    def warn(self, message):
        self.stdout.write(self.style.WARNING(f"  ! {message}"))

    @staticmethod
    def parse_map(items):
        mapping = {}
        for item in items:
            name, _, pk = item.rpartition("=")
            if not name or not pk.isdigit():
                raise CommandError(f"--map: expected CATEGORY=ID, got {item!r}")
            mapping[clean(name).lower()] = int(pk)
        return mapping

    def load_images(self, images, dry_run):
        """Download the picture of each (product id, link) and make it the product's first image; a dry run
        only checks that the link gives a picture."""
        for product_id, url in images:
            try:
                extension, data = download_image(url)
            except (requests.RequestException, ValueError) as error:
                self.stats["images failed"] += 1
                self.warn(f"product {product_id}: image {url} - {error}")
                continue
            if not dry_run:
                image = ProductImage(product_id=product_id)
                image.image.save(f"{product_id}{extension}", ContentFile(data), save=False)
                image.save()
            self.stats["images loaded" + (" (checked only)" if dry_run else "")] += 1

    @staticmethod
    def find_column(headers, names):
        names = [name.lower() for name in names]
        for name in names:
            if name in headers:
                return headers.index(name)
        for index, header in enumerate(headers):
            if header.split(" (")[0] in names:
                return index
        return None

    def read_rows(self, path, sheet=None):
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if sheet and sheet not in workbook.sheetnames:
            raise CommandError(f"No sheet {sheet!r}, the workbook has {workbook.sheetnames}")
        rows = (workbook[sheet] if sheet else workbook.worksheets[0]).iter_rows(values_only=True)
        for row in rows:
            headers = [clean(value).lower() for value in row]
            columns = {key: self.find_column(headers, names) for key, names in COLUMNS.items()}
            if columns["name"] is not None and (columns["category"] is not None
                                                or columns["item_category"] is not None):
                break
        else:
            raise CommandError(f"No header row with the columns {COLUMNS['category']} and {COLUMNS['name']}")

        self.path_columns = columns["item_category"] is not None or columns["sub_category"] is not None
        self.has_usd_price = columns["price"] is None and columns["price_usd"] is not None
        result = []
        for row in rows:
            values = {key: row[index] if index is not None and index < len(row) else None
                      for key, index in columns.items()}
            if clean(values["name"]):
                result.append(values)
        workbook.close()
        return result

    def get_brand(self, name):
        if name.lower() in self.brands:
            return self.brands[name.lower()]
        brand = named(Brand, name).first()
        if not brand:
            # no logo yet: hidden from the public brand list until someone uploads it in the admin
            brand = Brand.objects.create(name=name, name_ru=name, image="", is_visible=False)
            self.stats["brands created"] += 1
            self.stdout.write(f"  Brand {brand.pk} {name!r} created (hidden, without a logo)")
        self.brands[name.lower()] = brand
        return brand

    def get_item_category(self, name):
        key = name.lower()
        if key not in self.item_categories:
            if key in self.category_map:
                found = list(ProductItemCategory.objects.filter(pk=self.category_map[key]))
            else:
                found = list(named(ProductItemCategory, name))
                if not found and self.create_in:
                    found = [self.create_item_category(name, self.create_in)]
            self.item_categories[key] = found[0] if len(found) == 1 else None
            if len(found) != 1:
                self.warn(f"item category {name!r}: {'ambiguous' if found else 'not found'} - pass --map")
        return self.item_categories[key]

    def get_item_category_at(self, path, uz_path=("", "", "")):
        """The item category at a category / sub category / item category path; None (with a warning) when a
        level is missing or ambiguous. uz_path = the uz names of a level that has to be created."""
        key = tuple(name.lower() for name in path)
        if key not in self.paths:
            self.paths[key] = self.find_path(*path, uz_path)
        return self.paths[key]

    def find_path(self, category_name, sub_category_name, name, uz_path=("", "", "")):
        path = (category_name, sub_category_name, name)
        label = " / ".join(path)
        if not all(path):
            self.warn(f"{label!r}: the path is not full")
            return None
        found = list(named(ProductCategory, category_name))
        if not found and self.create_categories:
            found = [self.create_category(category_name, uz_path[0])]
        if len(found) == 1:
            parent = found[0]
            found = list(named(ProductSubCategory, sub_category_name).filter(product_category=parent))
            if not found and self.create_categories:
                found = [self.create_sub_category(sub_category_name, parent, uz_path[1])]
            if len(found) == 1:
                parent = found[0]
                found = list(named(ProductItemCategory, name).filter(product_sub_category=parent))
                if not found and self.create_categories:
                    found = [self.create_item_category(name, parent.pk, uz_path[2])]
        if len(found) != 1:
            hint = "" if self.create_categories else " - pass --create-categories"
            self.warn(f"{label!r}: {'ambiguous' if found else 'not found'}{hint}")
            return None
        return found[0]

    def create_category(self, name, name_uz=""):
        last = ProductCategory.objects.aggregate(last=Max("position"))["last"] or 0
        # no image yet: hidden until someone uploads it in the admin; save() (not create()) builds the slug
        category = ProductCategory(name=name, name_ru=name, name_uz=name_uz or None, image="", icon="",
                                   position=last + 1, is_active=False)
        category.save()
        self.stats["categories created (hidden, no image)"] += 1
        self.stdout.write(f"  Category {category.pk} {name!r} created (hidden, without an image)")
        return category

    def create_sub_category(self, name, category, name_uz=""):
        last = ProductSubCategory.objects.filter(product_category=category).aggregate(
            last=Max("position"))["last"] or 0
        sub_category = ProductSubCategory(product_category=category, name=name, name_ru=name, name_uz=name_uz or None,
                                          position=last + 1)
        sub_category.save()
        self.stats["sub categories created"] += 1
        self.stdout.write(f"  Sub category {sub_category.pk} {name!r} created in {category.name!r}")
        return sub_category

    def create_item_category(self, name, sub_category_id, name_uz=""):
        last = ProductItemCategory.objects.filter(product_sub_category_id=sub_category_id).aggregate(
            last=Max("position"))["last"] or 0
        # save() (not create()): the slug is built there
        item_category = ProductItemCategory(
            product_sub_category_id=sub_category_id, name=name, name_ru=name, name_uz=name_uz or None,
            position=last + 1)
        item_category.save()
        self.stats["item categories created"] += 1
        self.stdout.write(f"  Item category {item_category.pk} {name!r} created in sub category {sub_category_id}")
        return item_category

    def create_product(self, row, brand, active, taken):
        name = clean(row["name"])
        articul = ARTICUL_RE.search(name)
        if articul:
            name = clean(name[:articul.start()])
        characteristics = parse_characteristics(row["characteristics"])
        if not articul:
            articul = clean(row["articul"]) or next(
                (value for key, value, _ in characteristics if key.lower() == "артикул"), None)
        else:
            articul = articul.group(1)

        if name.lower() in taken:
            self.stats["skipped (a product with this name exists / repeated in the file)"] += 1
            self.warn(f"{name!r}: a product with this name exists / repeated in the file, skipped")
            return None
        if not brand:
            brand_name = clean(row["brand"])
            if not brand_name:
                # the brand is a field of the product, not one more attribute
                brand_name = next((value for key, value, _ in characteristics
                                   if key.lower() in BRAND_CHARACTERISTICS), "")
                characteristics = [item for item in characteristics if item[0].lower() not in BRAND_CHARACTERISTICS]
            if not brand_name:
                self.stats["skipped (no brand)"] += 1
                self.warn(f"{name!r}: no brand (--brand, a «Бренд» column or a «Марка» characteristic), skipped")
                return None
            brand = self.get_brand(brand_name)
        if self.path_columns:
            item_category = self.get_item_category_at(
                (clean(row["category"]), clean(row["sub_category"]), clean(row["item_category"])),
                (clean(row["category_uz"]), clean(row["sub_category_uz"]), clean(row["item_category_uz"])))
        else:
            item_category = self.get_item_category(clean(row["category"]))
        if not item_category:
            self.stats["skipped (item category)"] += 1
            return None
        raw_price = row["price_usd"] if self.has_usd_price else row["price"]
        try:
            price = float(str(raw_price).replace(" ", "").replace(",", "."))
        except ValueError:
            self.stats["skipped (no price)"] += 1
            self.warn(f"{name!r}: price {raw_price!r} is not a number, skipped")
            return None
        if self.has_usd_price:
            price = float(round(price * self.usd_rate))

        # a slip worth a look before the card goes public: the model written for another product
        model = next((value for key, value, _ in characteristics if key.lower() == "модель"), "")
        if model and model.lower() not in name.lower():
            self.warn(f"{name!r}: characteristic «Модель: {model}» does not match the name")

        description = html_text(row["description"])
        short_description = clean(row["short_description"]) or None
        # uz texts of a two-language sheet; empty -> NULL, so modeltranslation falls back to ru
        name_uz = clean(row["name_uz"]) or None
        description_uz = html_text(row["description_uz"]) or None
        short_description_uz = clean(row["short_description_uz"]) or None
        product = Product(
            name=name, name_ru=name, name_uz=name_uz, description=description, description_ru=description,
            description_uz=description_uz, short_description=short_description,
            short_description_ru=short_description, short_description_uz=short_description_uz, price=price,
            unit=UNITS.get(clean(row["unit"]).lower().rstrip("."), "pcs"), brand=brand,
            product_item_category=item_category, articul_code=articul or None,
            is_active=active, erp_active=False, publish_status=PUBLISH_STATUS_DRAFT,
        )
        product.save()
        ProductCharacteristics.objects.bulk_create([
            ProductCharacteristics(product=product, name=key, name_ru=key, value=value, value_ru=value,
                                   unit=unit or None, unit_ru=unit or None)
            for key, value, unit in characteristics
        ])
        taken.add(name.lower())
        self.stats["products created"] += 1
        self.stdout.write(f"  product {product.pk} {name!r} -> {item_category.name}, {brand.name}, {price:.0f}"
                          + (f", articul {articul}" if articul else ""))
        return product
