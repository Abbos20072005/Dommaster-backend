from .models import ProductItemCategory, ProductSubCategory, ProductCategory, Product
import requests
import threading
from django.conf import settings


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


def _send_telegram_message_sync(order_id, customer_name, customer_phone, delivery_address, total_price, items_info):
    """Internal synchronous function that runs in a separate thread."""
    message_lines = [
        f"<b>🛒 Новый заказ</b>",
        f"🆔 ID заказа: {order_id}",
        f"👤 Клиент: {customer_name or '—'}",
        f"📞 Телефон: {customer_phone or '—'}",
        f"📍 Адрес: {delivery_address or '—'}",
        f"💰 Общая стоимость: {total_price}",
        "📦 Товары:"
    ]

    for item_info in items_info:
        message_lines.append(
            f" - {item_info['name']} (Кол-во: {item_info['quantity']})"
        )

    message = "\n".join(message_lines)

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print("❌ Failed to send message to bot:", str(e))


def send_telegram_message(order):
    """Send Telegram notification asynchronously to avoid blocking the request."""

    customer_name = order.receiver_name or (order.customer.full_name if order.customer else None)
    customer_phone = order.receiver_phone or (order.customer.phone_number if order.customer else None)

    address = order.order_location
    delivery_address = None
    if address:
        parts = [p for p in (address.name, address.location_name) if p]
        delivery_address = ", ".join(parts) if parts else None

    order_items = order.order_items.select_related('product').all()
    items_info = [
        {
            'name': item.product.name,
            'quantity': item.quantity,
        }
        for item in order_items
    ]

    thread = threading.Thread(
        target=_send_telegram_message_sync,
        args=(order.id, customer_name, customer_phone, delivery_address, order.total_price, items_info),
        daemon=True
    )
    thread.start()
