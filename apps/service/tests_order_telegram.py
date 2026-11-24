"""New-order Telegram message: date / time, source, product site links in the Excel (BLD-515).
Run: env/Scripts/python.exe manage.py test apps.service.tests_order_telegram"""
from io import BytesIO

from django.test import TestCase
from openpyxl import load_workbook

from apps.service.models import Order
from apps.service.models.choices import ORDER_CHANNEL_ANDROID, ORDER_CHANNEL_SITE
from apps.service.tests import make_customer, make_item_category, make_order, make_product
from apps.service.utils import build_order_caption, build_order_data, build_order_excel


class OrderTelegramTests(TestCase):
    def setUp(self):
        _, item_category = make_item_category("Lamps")
        self.product = make_product("LAMP-1", item_category, 15000)
        self.order, _ = make_order(make_customer("+998900000515"), [(self.product, 3)], channel=ORDER_CHANNEL_SITE)

    def test_caption_has_date_and_source(self):
        caption = build_order_caption(build_order_data(self.order))
        self.assertIn(f"🕒 Дата: {self.order.created_at:%d.%m.%Y %H:%M}", caption)
        self.assertIn("📲 Источник: <b>Сайт</b>", caption)

        Order.objects.filter(id=self.order.id).update(channel=ORDER_CHANNEL_ANDROID)
        self.order.refresh_from_db()
        self.assertIn("Источник: <b>Приложение (Android)</b>", build_order_caption(build_order_data(self.order)))

        Order.objects.filter(id=self.order.id).update(channel=None)
        self.order.refresh_from_db()
        self.assertIn("Источник: <b>Не указан", build_order_caption(build_order_data(self.order)))

    def test_payment_is_atmos_or_on_receipt(self):
        # Click / Payme / Uzum are not used: the app sends 0 (older versions 1) for an Atmos card payment
        for payment_type in (0, 1, None):
            Order.objects.filter(id=self.order.id).update(payment_type=payment_type, payment_method=None)
            self.order.refresh_from_db()
            caption = build_order_caption(build_order_data(self.order))
            self.assertIn("💳 Оплата: Картой онлайн (Atmos) — ", caption)
            self.assertNotIn("Click", caption)

        Order.objects.filter(id=self.order.id).update(payment_type=4, payment_method="cash")
        self.order.refresh_from_db()
        data = build_order_data(self.order)
        self.assertIn("💳 Оплата: При получении (Наличные) — ", build_order_caption(data))
        ws = load_workbook(BytesIO(build_order_excel(data))).active
        self.assertTrue(any("При получении (Наличные)" in str(cell.value or "") for row in ws.iter_rows() for cell in row))

    def test_excel_links_every_product(self):
        self.product.refresh_from_db()
        url = f"https://buildex.uz/product/{self.product.slug_ru}"
        data = build_order_data(self.order)
        self.assertEqual(data["items"][0]["url"], url)

        ws = load_workbook(BytesIO(build_order_excel(data))).active
        self.assertEqual(ws["G10"].value, "Ссылка на сайте")
        self.assertEqual((ws["F11"].value, ws["G11"].value, ws["G11"].hyperlink.target), ("LAMP-1", "Открыть на сайте", url))
        self.assertEqual((ws["H11"].value, ws["I11"].value), ("шт.", 3))
        self.assertIn("Источник: Сайт", ws["A2"].value)
        # totals moved one column right: label I:K, value L:M
        self.assertEqual((ws["I13"].value, ws["L13"].number_format), ("Стоимость товаров:", '#,##0" сум"'))
