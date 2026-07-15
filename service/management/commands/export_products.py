import os
import openpyxl
from django.core.management.base import BaseCommand
from django.conf import settings
from service.models import Product


def _image_url(img, mode, domain):
    if mode == "path":
        return img.image.path if img.image else ""
    if mode == "full_url":
        return f"{domain}{img.image.url}" if img.image else ""
    return img.image.url if img.image else ""


class Command(BaseCommand):
    help = "Export products with category chain, brand, price, images, unit to Excel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="products_export.xlsx",
            help="Output file path (default: products_export.xlsx in project root)",
        )
        parser.add_argument(
            "--domain",
            type=str,
            default="",
            help="Domain to prefix image URLs (e.g. https://example.com). "
                 "If set, images export as full URLs instead of relative.",
        )
        parser.add_argument(
            "--use-path",
            action="store_true",
            help="Use absolute file system paths instead of URLs for images.",
        )

    def handle(self, *args, **options):
        output_path = options["output"]
        if not os.path.isabs(output_path):
            output_path = os.path.join(settings.BASE_DIR, output_path)

        domain = options["domain"].rstrip("/") if options["domain"] else ""
        mode = "path" if options["use_path"] else ("full_url" if domain else "relative")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Products"

        headers = [
            "ID",
            "Наименование",
            "Категория",
            "Подкатегория",
            "Предметная категория",
            "Бренд",
            "Цена",
            "Единица измерения",
            "Изображения",
        ]
        ws.append(headers)

        qs = Product.objects.filter(
            is_active=True,
        ).select_related(
            "brand",
            "product_item_category__product_sub_category__product_category",
        ).prefetch_related(
            "product_image",
        ).order_by("id")

        total = qs.count()
        self.stdout.write(f"Exporting {total} products...")

        for idx, product in enumerate(qs.iterator(chunk_size=500), start=1):
            item_cat = product.product_item_category
            sub_cat = item_cat.product_sub_category if item_cat else None
            cat = sub_cat.product_category if sub_cat else None

            images = product.product_image.all()
            images_str = ", ".join(
                _image_url(img, mode, domain)
                for img in images
                if img.image
            ) if images else ""

            ws.append([
                product.id,
                product.name,
                cat.name if cat else "",
                sub_cat.name if sub_cat else "",
                item_cat.name if item_cat else "",
                product.brand.name if product.brand else "",
                product.price,
                product.unit,
                images_str,
            ])

            if idx % 1000 == 0:
                self.stdout.write(f"  {idx}/{total}")

        wb.save(output_path)
        self.stdout.write(self.style.SUCCESS(f"\nDone! File saved to: {output_path}"))
        self.stdout.write(self.style.SUCCESS(f"Rows exported: {total}"))
