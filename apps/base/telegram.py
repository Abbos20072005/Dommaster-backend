import html
import logging
import threading

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_TEXT_LIMIT = 4096


def _build_chat_caption(data):
    lines = [f"💬 <b>Новое сообщение в чате #{data['chat_id']}</b>"]
    if data["customer_name"] or data["customer_phone"]:
        if data["customer_name"]:
            lines.append(f"👤 {html.escape(data['customer_name'])}")
        if data["customer_phone"]:
            lines.append(f"📞 {html.escape(data['customer_phone'])}")
    else:
        lines.append("👤 Неавторизованный пользователь")
    lines.append(f"🕒 {data['created_at']}")
    if data["text"]:
        lines.append("")
        lines.append(html.escape(data["text"]))
    return "\n".join(lines)


def _truncate(text, limit):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _send_chat_message_sync(data):
    token = settings.TELEGRAM_BOT_TOKEN
    payload = {"chat_id": settings.TELEGRAM_CHANNEL_ID, "parse_mode": "HTML"}
    if settings.TELEGRAM_CHAT_TOPIC_ID:
        payload["message_thread_id"] = settings.TELEGRAM_CHAT_TOPIC_ID
    caption = _build_chat_caption(data)

    try:
        if data["image_path"]:
            payload["caption"] = _truncate(caption, TELEGRAM_CAPTION_LIMIT)
            with open(data["image_path"], "rb") as f:
                response = requests.post(
                    f"https://api.telegram.org/bot{token}/sendPhoto",
                    data=payload, files={"photo": f}, timeout=20,
                )
        else:
            payload["text"] = _truncate(caption, TELEGRAM_TEXT_LIMIT)
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage", data=payload, timeout=20,
            )
        result = response.json()
        if not result.get("ok"):
            logger.error(
                "Telegram chat message failed: message_id=%s status=%s error_code=%s description=%s",
                data["message_id"], response.status_code, result.get("error_code"), result.get("description"),
            )
    except requests.RequestException as e:
        logger.error("Telegram request error: message_id=%s %s", data["message_id"], type(e).__name__)
    except Exception:
        logger.exception("Failed to send chat message to Telegram: message_id=%s", data["message_id"])


def send_chat_message_to_telegram(message):
    """Forward a customer's chat message to the support Telegram group (non-blocking)."""
    if message.is_answer or not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
        return

    customer = message.chat.customer
    data = {
        "message_id": message.id,
        "chat_id": message.chat_id,
        "customer_name": customer.full_name if customer else None,
        "customer_phone": customer.phone_number if customer else None,
        "created_at": message.created_at.strftime("%d.%m.%Y %H:%M") if message.created_at else "",
        "text": message.message or "",
        "image_path": message.image.path if message.image else None,
    }
    threading.Thread(target=_send_chat_message_sync, args=(data,), daemon=True).start()
