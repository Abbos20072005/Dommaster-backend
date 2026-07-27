from .models import ProductItemCategory, ProductSubCategory, ProductCategory, Product
import requests
import threading


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


BOT_URL = "http://localhost:8080/send_order"  # your bot host/port
SECRET_TOKEN = "supersecrettoken123"


def _send_telegram_message_sync(order_id, customer_id, total_price, items_info):
    """Internal synchronous function that runs in a separate thread."""
    message_lines = [
        f"<b>🛒 Новый заказ</b>",
        f"🆔 ID заказа: {order_id}",
        f"👤 ID клиента: {customer_id}",
        f"💰 Общая стоимость: {total_price}",
        "📦 Товары:"
    ]

    for item_info in items_info:
        message_lines.append(
            f" - {item_info['name']} (Кол-во: {item_info['quantity']}) | 👤 Менеджер: {item_info['telegram_id']}"
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
        response = requests.post(BOT_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print("❌ Failed to send message to bot:", str(e))


def send_telegram_message(order):
    """Send Telegram notification asynchronously to avoid blocking the request."""
    order_items = order.order_items.select_related('product').all()
    items_info = [
        {
            'name': item.product.name,
            'quantity': item.quantity,
            'telegram_id': item.product.telegram_id,
        }
        for item in order_items
    ]

    thread = threading.Thread(
        target=_send_telegram_message_sync,
        args=(order.id, order.customer_id, order.total_price, items_info),
        daemon=True
    )
    thread.start()
