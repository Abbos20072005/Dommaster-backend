from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from integration.telegram_otp import TelegramOTPBot, TelegramBotError


class Command(BaseCommand):
    help = "Register the OTP bot webhook: set_telegram_otp_webhook https://api.example.uz"

    def add_arguments(self, parser):
        parser.add_argument("base_url", help="Public backend URL, e.g. https://api.dommaster.uz")
        parser.add_argument("--delete", action="store_true", help="Remove the webhook instead")

    def handle(self, *args, **options):
        if not settings.TELEGRAM_OTP_BOT_TOKEN:
            raise CommandError("TELEGRAM_OTP_BOT_TOKEN is not set")
        try:
            if options["delete"]:
                TelegramOTPBot.call("deleteWebhook", {})
                self.stdout.write(self.style.SUCCESS("Webhook deleted"))
                return
            if not settings.TELEGRAM_OTP_WEBHOOK_SECRET:
                raise CommandError("TELEGRAM_OTP_WEBHOOK_SECRET is not set")
            url = options["base_url"].rstrip("/") + "/api/v1/auth/telegram/webhook/"
            TelegramOTPBot.call("setWebhook", {
                "url": url,
                "secret_token": settings.TELEGRAM_OTP_WEBHOOK_SECRET,
                "allowed_updates": ["message", "my_chat_member"],
                "drop_pending_updates": True,
            })
        except TelegramBotError as e:
            raise CommandError(f"Telegram error: {e}")
        self.stdout.write(self.style.SUCCESS(f"Webhook set: {url}"))
