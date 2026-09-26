import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TelegramBotError(Exception):
    def __init__(self, message, blocked=False):
        super().__init__(message)
        self.blocked = blocked  # user blocked the bot / chat not found -> link is dead


class TelegramOTPBot:
    """Minimal Bot API client for the OTP bot (TELEGRAM_OTP_BOT_TOKEN)."""
    TIMEOUT = 5

    USERNAME_CACHE_KEY = "telegram_otp_bot:username"

    @staticmethod
    def is_configured():
        return bool(settings.TELEGRAM_OTP_BOT_TOKEN)

    @classmethod
    def username(cls):
        """TELEGRAM_OTP_BOT_USERNAME if set, otherwise taken from getMe and cached for a day."""
        if settings.TELEGRAM_OTP_BOT_USERNAME:
            return settings.TELEGRAM_OTP_BOT_USERNAME
        username = cache.get(cls.USERNAME_CACHE_KEY)
        if not username:
            username = cls.call("getMe", {})["username"]
            cache.set(cls.USERNAME_CACHE_KEY, username, 86400)
        return username

    @classmethod
    def deep_link(cls, token):
        return f"https://t.me/{cls.username()}?start={token}"

    @classmethod
    def call(cls, method, payload):
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_OTP_BOT_TOKEN}/{method}"
        try:
            response = requests.post(url, json=payload, timeout=cls.TIMEOUT)
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Telegram OTP bot {method} failed: {e}")
            raise TelegramBotError(str(e))

        if not data.get("ok"):
            description = data.get("description", "")
            logger.warning(f"Telegram OTP bot {method} error: {data.get('error_code')} {description}")
            blocked = data.get("error_code") == 403 or "chat not found" in description.lower()
            raise TelegramBotError(description, blocked=blocked)
        return data.get("result")

    @classmethod
    def send_message(cls, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return cls.call("sendMessage", payload)

    @staticmethod
    def contact_keyboard(text):
        return {
            "keyboard": [[{"text": text, "request_contact": True}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        }

    @staticmethod
    def remove_keyboard():
        return {"remove_keyboard": True}
