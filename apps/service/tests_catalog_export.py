"""Active catalog .xlsx of the PM Expert CRM: rows, the build date, the token link.
Run: env/Scripts/python.exe manage.py test apps.service.tests_catalog_export"""
import shutil
import tempfile
from io import BytesIO

from django.test import TestCase, override_settings
from openpyxl import load_workbook

from apps.service import catalog_export
from apps.service.models import Product
from apps.service.tests import make_item_category, make_product

TOKEN = "s3cret-token-of-the-crm-link"


class CatalogExportTests(TestCase):
    def setUp(self):
        self.private_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.private_root, ignore_errors=True)
        override = override_settings(PRIVATE_ROOT=self.private_root, CATALOG_EXPORT_TOKEN=TOKEN)
        override.enable()
        self.addCleanup(override.disable)

        _, item_category = make_item_category("Cement")
        self.cement = make_product("CEM-1", item_category, 85000)
        Product.objects.filter(id=self.cement.id).update(name_ru="Цемент М400 50 кг", name_uz="Sement M400",
                                                         unit="pkg", is_active=True)
        self.discounted = make_product("PIPE-1", item_category, 12000, discount_price=10000)
        Product.objects.filter(id=self.discounted.id).update(unit="m", is_active=True)
        hidden = make_product("HIDDEN-1", item_category, 5000)
        Product.objects.filter(id=hidden.id).update(is_active=False)
        no_price = make_product("FREE-1", item_category, 0)
        Product.objects.filter(id=no_price.id).update(is_active=True)

    def rows(self, content=None):
        workbook = load_workbook(BytesIO(content) if content else catalog_export.export_path())
        return workbook, [list(row) for row in workbook["Каталог"].iter_rows(values_only=True)]

    def test_only_active_products_with_price_ru_name_cart_price_unit(self):
        self.assertEqual(catalog_export.build_export(), 2)
        workbook, rows = self.rows()
        self.assertEqual(rows, [
            ["ID", "Наименование", "Цена, UZS", "Ед. изм."],
            [self.cement.id, "Цемент М400 50 кг", 85000, "упак"],
            [self.discounted.id, "PIPE-1", 10000, "м"],
        ])
        info = dict(workbook["Обновлено"].iter_rows(values_only=True))
        self.assertRegex(info["Обновлено"], r"^\d\d\.\d\d\.\d{4} \d\d:\d\d$")
        self.assertEqual(info["Товаров"], 2)

    def test_link_needs_the_token(self):
        response = self.client.get(f"/api/v1/feeds/catalog.xlsx?token={TOKEN}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("buildex_catalog_", response["Content-Disposition"])
        _, rows = self.rows(b"".join(response.streaming_content))
        self.assertEqual(len(rows), 3)

        self.assertEqual(self.client.get("/api/v1/feeds/catalog.xlsx?token=wrong").status_code, 404)
        with override_settings(CATALOG_EXPORT_TOKEN=""):
            self.assertEqual(self.client.get(f"/api/v1/feeds/catalog.xlsx?token={TOKEN}").status_code, 404)
            self.assertEqual(self.client.get("/api/v1/feeds/catalog.xlsx").status_code, 404)

    def test_not_modified(self):
        first = self.client.get(f"/api/v1/feeds/catalog.xlsx?token={TOKEN}")
        again = self.client.get(f"/api/v1/feeds/catalog.xlsx?token={TOKEN}",
                                HTTP_IF_MODIFIED_SINCE=first["Last-Modified"])
        self.assertEqual(again.status_code, 304)
