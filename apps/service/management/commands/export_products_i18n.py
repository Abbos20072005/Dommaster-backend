import os

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.service.models import Product
from apps.service.products_i18n_export import export_workbook


class Command(BaseCommand):
    help = "Export products to Excel: id, uz/ru name, category chain, short description, description, has image"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="products_i18n.xlsx",
            help="Output file path (default: products_i18n.xlsx in project root)",
        )
        parser.add_argument(
            "--raw-html",
            action="store_true",
            help="Keep descriptions as stored HTML instead of plain text",
        )

    def handle(self, *args, **options):
        output_path = options["output"]
        if not os.path.isabs(output_path):
            output_path = os.path.join(settings.BASE_DIR, output_path)

        self.stdout.write("Exporting products...")
        data, total, without_image = export_workbook(Product.objects.all(), raw_html=options["raw_html"])
        with open(output_path, "wb") as file:
            file.write(data)
        self.stdout.write(self.style.SUCCESS(f"\nDone! File saved to: {output_path}"))
        self.stdout.write(self.style.SUCCESS(f"Rows exported: {total} | Without image: {without_image}"))
