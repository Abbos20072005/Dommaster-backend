from django.core.management.base import BaseCommand

from apps.service import catalog_export


class Command(BaseCommand):
    help = ("Rebuilds the active catalog .xlsx of the PM Expert CRM (PRIVATE_ROOT/catalog.xlsx, served at "
            "feeds/catalog.xlsx?token=<CATALOG_EXPORT_TOKEN>). Celery beat runs it once a day "
            "(apps.service.tasks.build_catalog_export).")

    def handle(self, *args, **options):
        count = catalog_export.build_export()
        self.stdout.write(f"{catalog_export.export_path()}: {count} products")
