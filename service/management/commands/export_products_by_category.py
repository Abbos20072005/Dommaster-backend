import os
import openpyxl
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Prefetch
from service.models import ProductCategory, Product


class Command(BaseCommand):
    help = "Export products to Excel with one sheet per ProductCategory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="products_by_category.xlsx",
            help="Output file path (default: products_by_category.xlsx in project root)",
        )

    def handle(self, *args, **options):
        output_path = options["output"]
        if not os.path.isabs(output_path):
            output_path = os.path.join(settings.BASE_DIR, output_path)

        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        categories = ProductCategory.objects.all().order_by("position", "id")
        total_products = 0

        used_names = set()

        for cat in categories:
            sheet_name = cat.name[:31]
            if sheet_name in used_names:
                suffix = 2
                while f"{sheet_name[:27]}_{suffix}" in used_names:
                    suffix += 1
                sheet_name = f"{sheet_name[:27]}_{suffix}"
            used_names.add(sheet_name)

            products = (
                Product.objects.filter(
                    product_item_category__product_sub_category__product_category=cat
                )
                .select_related(
                    "brand",
                    "product_item_category__product_sub_category",
                )
                .prefetch_related(
                    Prefetch("product_image", to_attr="images"),
                )
                .order_by("id")
            )

            count = products.count()
            if count == 0:
                continue

            ws = wb.create_sheet(title=sheet_name)

            headers = [
                "ID",
                "Наименование",
                "Подкатегория",
                "Предметная категория",
                "Бренд",
                "Цена",
                "Скидочная цена",
                "Скидка %",
                "Количество",
                "Единица измерения",
                "Артикул",
                "Штрихкод",
                "Рейтинг",
                "Активен",
                "Изображения",
            ]
            ws.append(headers)

            for product in products.iterator(chunk_size=500):
                sub_cat = product.product_item_category.product_sub_category if product.product_item_category else None
                item_cat = product.product_item_category

                images = getattr(product, "images", [])
                images_str = ", ".join(
                    img.image.url for img in images if img.image
                ) if images else ""

                ws.append([
                    product.id,
                    product.name,
                    sub_cat.name if sub_cat else "",
                    item_cat.name if item_cat else "",
                    product.brand.name if product.brand else "",
                    product.price,
                    product.discount_price or "",
                    product.discount or "",
                    product.quantity,
                    product.unit,
                    product.vendor_code or "",
                    product.barcode or "",
                    product.rating,
                    "Да" if product.is_active else "Нет",
                    images_str,
                ])

            total_products += count
            self.stdout.write(f"  [{sheet_name}] {count} products")

        wb.save(output_path)
        self.stdout.write(self.style.SUCCESS(f"\nDone! File: {output_path}"))
        self.stdout.write(self.style.SUCCESS(f"Categories: {len(categories)} | Products: {total_products}"))
