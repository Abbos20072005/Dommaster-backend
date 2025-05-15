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

import requests

BOT_URL = "http://localhost:8080/send_order"  # your bot host/port
SECRET_TOKEN = "supersecrettoken123"

def send_telegram_message(order):
    order_items = order.order_items.all()
    message_lines = [
        f"<b>🛒 New Order Created</b>",
        f"🆔 Order ID: {order.id}",
        f"👤 Customer ID: {order.customer.id if order.customer else 'Unknown'}",
        f"💰 Total Price: {order.total_price}",
        "📦 Items:"
    ]

    for item in order_items:
        message_lines.append(
            f" - {item.product.name} (Qty: {item.quantity}) | 👤 Manager: {item.product.telegram_id}"
        )

    message = "\n".join(message_lines)

    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": SECRET_TOKEN
    }

    payload = {
        "text": message
    }

    try:
        response = requests.post(BOT_URL, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print("❌ Failed to send message to bot:", str(e))
