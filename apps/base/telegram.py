import html
import json
import logging
import threading

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_MEDIA_GROUP_LIMIT = 10
# customer text is cut before escaping (never inside an HTML entity);
# leaves room for the header within Telegram's 4096 message limit
BODY_TEXT_LIMIT = 3500


def _truncate(text, limit):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _customer_lines(name, phone):
    if not name and not phone:
        return ["👤 Неавторизованный пользователь"]
    lines = []
    if name:
        lines.append(f"👤 {html.escape(name)}")
    if phone:
        lines.append(f"📞 {html.escape(phone)}")
    return lines


def _format_dt(value):
    return value.strftime("%d.%m.%Y %H:%M") if value else ""


def _build_chat_caption(data):
    lines = [f"💬 <b>Новое сообщение в чате #{data['chat_id']}</b>"]
    lines += _customer_lines(data["customer_name"], data["customer_phone"])
    lines.append(f"🕒 {data['created_at']}")
    if data["text"]:
        lines.append("")
        lines.append(html.escape(_truncate(data["text"], BODY_TEXT_LIMIT)))
    return "\n".join(lines)


def _build_feedback_caption(title, instance, text, extra_lines=()):
    product = instance.product
    customer = instance.customer
    product_line = f"📦 {html.escape(getattr(product, 'name_ru', None) or product.name or '')}"
    if product.product_code:
        product_line += f" (код: {html.escape(str(product.product_code))})"
    lines = [f"<b>{title} #{instance.id}</b>", product_line, *extra_lines]
    lines += _customer_lines(
        customer.full_name if customer else None, customer.phone_number if customer else None
    )
    lines.append(f"🕒 {_format_dt(instance.created_at)}")
    if text:
        lines.append("")
        lines.append(html.escape(_truncate(text, BODY_TEXT_LIMIT)))
    return "\n".join(lines)


def _post(method, payload, ref, files=None):
    response = requests.post(
        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}",
        data=payload, files=files, timeout=20,
    )
    result = response.json()
    if not result.get("ok"):
        logger.error(
            "Telegram %s failed: %s status=%s error_code=%s description=%s",
            method, ref, response.status_code, result.get("error_code"), result.get("description"),
        )


def _send_to_group_sync(caption, topic_id, image_paths, ref):
    payload = {"chat_id": settings.TELEGRAM_CHANNEL_ID, "parse_mode": "HTML"}
    if topic_id:
        payload["message_thread_id"] = topic_id
    opened = []

    try:
        for path in image_paths[:TELEGRAM_MEDIA_GROUP_LIMIT]:
            try:
                opened.append(open(path, "rb"))
            except OSError:
                logger.warning("Telegram image not found, skipped: %s %s", ref, path)

        # text that doesn't fit a photo caption goes as its own message, photos follow
        if not opened or len(caption) > TELEGRAM_CAPTION_LIMIT:
            _post("sendMessage", {**payload, "text": caption}, ref)
            caption = ""
        if not opened:
            return

        if len(opened) == 1:
            if caption:
                payload["caption"] = caption
            _post("sendPhoto", payload, ref, files={"photo": opened[0]})
        else:
            media = [{"type": "photo", "media": f"attach://photo{i}"} for i in range(len(opened))]
            if caption:
                media[0].update(caption=caption, parse_mode="HTML")
            payload["media"] = json.dumps(media)
            _post("sendMediaGroup", payload, ref, files={f"photo{i}": f for i, f in enumerate(opened)})
    except requests.RequestException as e:
        logger.error("Telegram request error: %s %s", ref, type(e).__name__)
    except Exception:
        logger.exception("Failed to send to Telegram: %s", ref)
    finally:
        for f in opened:
            f.close()


def _send_to_group(caption, topic_id, ref, image_paths=()):
    """Send to the staff Telegram group (TELEGRAM_CHANNEL_ID) in a thread, never blocks the request."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
        return
    threading.Thread(
        target=_send_to_group_sync, args=(caption, topic_id, list(image_paths), ref), daemon=True
    ).start()


def send_chat_message_to_telegram(message):
    """Forward a customer's chat message to the support Telegram group (non-blocking)."""
    if message.is_answer:
        return

    customer = message.chat.customer
    data = {
        "chat_id": message.chat_id,
        "customer_name": customer.full_name if customer else None,
        "customer_phone": customer.phone_number if customer else None,
        "created_at": _format_dt(message.created_at),
        "text": message.message or "",
    }
    _send_to_group(
        _build_chat_caption(data), settings.TELEGRAM_CHAT_TOPIC_ID, f"message_id={message.id}",
        image_paths=[message.image.path] if message.image else (),
    )


def send_comment_to_telegram(comment):
    """Forward a customer's product review (with its images) to the Telegram group (non-blocking)."""
    rating = max(0, min(comment.product_rating or 0, 5))
    caption = _build_feedback_caption(
        "📝 Новый отзыв", comment, comment.comment,
        extra_lines=[f"{'⭐' * rating}{'☆' * (5 - rating)} ({rating}/5)"],
    )
    _send_to_group(
        caption, settings.TELEGRAM_COMMENT_TOPIC_ID, f"comment_id={comment.id}",
        image_paths=[item.image.path for item in comment.comment_image.all() if item.image],
    )


def send_question_to_telegram(question):
    """Forward a customer's product question to the Telegram group (non-blocking)."""
    caption = _build_feedback_caption("❓ Новый вопрос", question, question.question)
    _send_to_group(caption, settings.TELEGRAM_QUESTION_TOPIC_ID, f"question_id={question.id}")
