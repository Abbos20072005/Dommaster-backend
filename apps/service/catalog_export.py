"""The active catalog as an .xlsx file for the PM Expert CRM: a manager's sale made outside the site is entered
there with the goods picked from this list. Columns: id, the ru name (the CRM matches the site's `purchase`
event by `item_name`, it has no id), the price the cart charges, the unit; nothing else (no cost price,
no stock, no supplier — commercial data).

Rebuilt once a day by Celery beat (`tasks.build_catalog_export`), kept outside MEDIA_ROOT (nginx serves that
publicly) and served only under the secret token of the env (`CATALOG_EXPORT_TOKEN`,
`MerchantFeedViewSet.catalog_export`). The build time is on the second sheet.
"""
import logging
import os
import tempfile

from django.conf import settings
from django.utils import timezone
from openpyxl import Workbook

from .merchant_feed import final_price
from .models import Product

logger = logging.getLogger(__name__)

FILE_NAME = "catalog.xlsx"
CHUNK = 2000
HEADERS = ("ID", "Наименование", "Цена, UZS", "Ед. изм.")
UNIT_LABELS = {
    "pcs": "шт", "m": "м", "sm": "см", "kg": "кг", "g": "г", "l": "л", "pkg": "упак", "set": "компл",
}


def export_path():
    return os.path.join(settings.PRIVATE_ROOT, FILE_NAME)


def catalog_products():
    """What the site sells: active products with a price."""
    return Product.objects.filter(is_active=True, price__gt=0).only(
        "id", "name", "name_ru", "price", "discount_price", "unit",
    ).order_by("id")


def product_row(product):
    name = (product.name_ru or product.name or "").strip()
    price = final_price(product)
    if not name or not price or price <= 0:
        return None
    return product.id, name, int(round(price)), UNIT_LABELS.get(product.unit, product.unit)


def write_workbook(path, built_at):
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Каталог")
    sheet.column_dimensions["A"].width = 10
    sheet.column_dimensions["B"].width = 80
    sheet.column_dimensions["C"].width = 14
    sheet.column_dimensions["D"].width = 10
    sheet.append(HEADERS)
    count = 0
    for product in catalog_products().iterator(chunk_size=CHUNK):
        row = product_row(product)
        if row:
            sheet.append(row)
            count += 1
    info = workbook.create_sheet("Обновлено")
    info.append(("Обновлено", built_at.strftime("%d.%m.%Y %H:%M")))
    info.append(("Товаров", count))
    workbook.save(path)
    return count


def build_export():
    """Rebuilds the file, replaced in one step (a download never gets a half-written one).
    Returns the number of products written."""
    os.makedirs(settings.PRIVATE_ROOT, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=settings.PRIVATE_ROOT, prefix=f".{FILE_NAME}.", suffix=".tmp")
    os.close(fd)
    try:
        count = write_workbook(tmp, timezone.now())
        os.replace(tmp, export_path())
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    logger.info("Catalog export built: %s products", count)
    return count
