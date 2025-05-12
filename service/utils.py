from .models import ProductItemCategory, ProductSubCategory, ProductCategory, Product
import requests


def build_breadcrumbs(obj):
    breadcrumbs = []

    if isinstance(obj, Product):
        breadcrumbs.insert(0, {"id": obj.id, "name": obj.name, "level": "product"})
        obj = obj.product_item_category

    if isinstance(obj, ProductItemCategory):
        breadcrumbs.insert(0, {"id": obj.id, "name": obj.name, "level": "product_item_category"})
        obj = obj.product_sub_category

    if isinstance(obj, ProductSubCategory):
        breadcrumbs.insert(0, {"id": obj.id, "name": obj.name, "level": "product_sub_category"})
        obj = obj.product_category

    if isinstance(obj, ProductCategory):
        breadcrumbs.insert(0, {"id": obj.id, "name": obj.name, "level": "product_category"})

    return breadcrumbs

TELEGRAM_TOKEN = '6380957235:AAHOgqvvnffZL4deU_pY79mieYdBJYr0J-w'
TELEGRAM_CHAT_ID = '1624671606'


def send_telegram_message(message: str):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    requests.post(url, data=data)