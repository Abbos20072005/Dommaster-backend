"""OTP fallback via Telegram bot.

Flow ("kod kelmadi" button -> POST otp/telegram/):
- phone already linked: a new OTP is sent straight to the linked chat;
- not linked: a new (undelivered) OTP + one-time deep link token are created. The customer opens
  t.me/<bot>?start=<token>, shares their contact (phone ownership proof), the link is saved and
  the OTP is delivered to the bot. The client keeps the returned otp_key and verifies as usual.
"""
import logging
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError

from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from apps.integration.telegram_otp import TelegramOTPBot, TelegramBotError
from .models import OTP, TelegramLink, TelegramLinkToken
from .services import create_otp
from .utils import normalize_uz_phone

logger = logging.getLogger(__name__)

TELEGRAM_OTP_COOLDOWN = timedelta(minutes=1)
TELEGRAM_OTP_WINDOW = timedelta(hours=12)
TELEGRAM_OTP_MAX_PER_WINDOW = 10
OTP_LIFETIME = timedelta(minutes=1)

MSG_OTP = "Buildex Go\nTasdiqlash kodi / Код подтверждения: <b>{code}</b>\n\nKodni hech kimga bermang. / Никому не сообщайте код."
MSG_SHARE_CONTACT = ("Raqamingizni tasdiqlash uchun pastdagi tugmani bosing.\n"
                     "Нажмите кнопку ниже, чтобы подтвердить номер телефона.")
MSG_SHARE_BUTTON = "📱 Raqamni yuborish / Отправить номер"
MSG_LINK_EXPIRED = ("Havola eskirgan. Ilovada \"Kod kelmadi\" tugmasini qayta bosing.\n"
                    "Ссылка устарела. Нажмите «Код не пришёл» в приложении ещё раз.")
MSG_NO_TOKEN = ("Kod olish uchun ilovada \"Kod kelmadi\" tugmasini bosing.\n"
                "Чтобы получить код, нажмите «Код не пришёл» в приложении.")
MSG_FOREIGN_CONTACT = "Faqat o'z raqamingizni yuboring. / Отправьте, пожалуйста, свой номер."
MSG_PHONE_MISMATCH = ("Bu raqam ilovada kiritilgan raqamga mos kelmadi.\n"
                      "Этот номер не совпадает с номером, указанным в приложении.")
MSG_LINKED_NO_CODE = ("Telegram ulandi. Endi tasdiqlash kodlari shu yerga keladi.\n"
                      "Telegram привязан. Теперь коды подтверждения будут приходить сюда.")
MSG_UNLINKED = "Telegram raqamdan uzildi. / Telegram отвязан от номера."
MSG_NOT_LINKED = "Bu chat hech qaysi raqamga ulanmagan. / Этот чат не привязан к номеру."


def check_telegram_otp_limit(customer):
    now = datetime.now()
    tg_otps = OTP.objects.filter(customer_id=customer.id, channel=OTP.Channel.TELEGRAM,
                                 created_at__gt=now - TELEGRAM_OTP_WINDOW)
    last_otp = tg_otps.order_by("-created_at").first()
    if last_otp and last_otp.created_at + TELEGRAM_OTP_COOLDOWN > now:
        raise CustomApiException(error_code=ErrorCodes.OTP_NOT_EXPIRED,
                                 time=(last_otp.created_at + TELEGRAM_OTP_COOLDOWN - now).total_seconds())
    if tg_otps.count() >= TELEGRAM_OTP_MAX_PER_WINDOW:
        raise CustomApiException(error_code=ErrorCodes.TELEGRAM_OTP_LIMIT,
                                 time=tg_otps.order_by("created_at").first().created_at + TELEGRAM_OTP_WINDOW)


def is_telegram_linked(phone_number):
    return TelegramLink.objects.filter(phone_number=phone_number).exists()


def _deliver_otp(chat_id, otp):
    """Send the code and restart its lifetime from the delivery moment."""
    TelegramOTPBot.send_message(chat_id, MSG_OTP.format(code=otp.otp_code), TelegramOTPBot.remove_keyboard())
    otp.expire_at = datetime.now() + OTP_LIFETIME
    otp.save(update_fields=["expire_at"])


def request_telegram_otp(source_otp):
    """Called by the "kod kelmadi" button. `source_otp` must be the customer's latest OTP."""
    customer = source_otp.customer
    if not TelegramOTPBot.is_configured():
        raise CustomApiException(error_code=ErrorCodes.TELEGRAM_UNAVAILABLE)
    check_telegram_otp_limit(customer)

    otp = create_otp(customer, resend=source_otp.resend, check_limit=False, channel=OTP.Channel.TELEGRAM)

    link = TelegramLink.objects.filter(phone_number=customer.phone_number).first()
    if link:
        try:
            _deliver_otp(link.chat_id, otp)
            return {"otp_key": otp.otp_key, "linked": True, "deep_link": None, "link_token": None,
                    "expires_in": None}
        except TelegramBotError as e:
            if not e.blocked:
                otp.delete()
                raise CustomApiException(error_code=ErrorCodes.TELEGRAM_UNAVAILABLE)
            # user blocked the bot / deleted the chat -> link is dead, fall through to re-linking
            link.delete()

    link_token = secrets.token_urlsafe(24)
    try:
        deep_link = TelegramOTPBot.deep_link(link_token)
    except TelegramBotError:
        otp.delete()
        raise CustomApiException(error_code=ErrorCodes.TELEGRAM_UNAVAILABLE)

    TelegramLinkToken.objects.filter(customer_id=customer.id, is_used=False).update(is_used=True)
    ttl = timedelta(minutes=settings.TELEGRAM_LINK_TOKEN_TTL_MINUTES)
    TelegramLinkToken.objects.create(
        token=link_token, customer=customer, otp=otp, expires_at=datetime.now() + ttl,
    )
    return {
        "otp_key": otp.otp_key,
        "linked": False,
        "deep_link": deep_link,
        "link_token": link_token,
        "expires_in": int(ttl.total_seconds()),
    }


def unlink_telegram(phone_number):
    links = list(TelegramLink.objects.filter(phone_number=phone_number))
    for link in links:
        link.delete()
        try:
            TelegramOTPBot.send_message(link.chat_id, MSG_UNLINKED, TelegramOTPBot.remove_keyboard())
        except TelegramBotError:
            pass
    return bool(links)


# ---------------------------------------------------------------- webhook

def _reply(chat_id, text, reply_markup=None):
    try:
        TelegramOTPBot.send_message(chat_id, text, reply_markup)
    except TelegramBotError:
        pass


def _complete_link(token, chat_id):
    """Mark the token used (idempotent for Telegram retries) and deliver the customer's latest OTP.

    The latest OTP (not necessarily token.otp) is the one whose otp_key the app holds, e.g. when the
    customer requested an SMS resend after getting the deep link."""
    if not TelegramLinkToken.objects.filter(pk=token.pk, is_used=False).update(is_used=True):
        return
    otp = OTP.objects.filter(customer_id=token.customer_id).order_by("-created_at").first()
    if not otp:
        # already verified (OTPs are deleted on success) -> nothing to deliver
        _reply(chat_id, MSG_LINKED_NO_CODE, TelegramOTPBot.remove_keyboard())
        return
    try:
        _deliver_otp(chat_id, otp)
    except TelegramBotError:
        logger.warning(f"Telegram OTP delivery failed for customer {token.customer_id}")


def _handle_start(chat_id, from_user, payload):
    if not payload:
        _reply(chat_id, MSG_NO_TOKEN)
        return
    token = TelegramLinkToken.objects.select_related("customer", "otp").filter(token=payload).first()
    if not token or not token.is_valid():
        _reply(chat_id, MSG_LINK_EXPIRED)
        return

    # this Telegram account already proved ownership of the phone -> no need to share contact again
    phone = token.customer.phone_number
    if TelegramLink.objects.filter(phone_number=phone, telegram_user_id=from_user["id"]).exists():
        TelegramLink.objects.filter(phone_number=phone).update(chat_id=chat_id)
        _complete_link(token, chat_id)
        return

    token.chat_id = chat_id
    token.save(update_fields=["chat_id"])
    _reply(chat_id, MSG_SHARE_CONTACT, TelegramOTPBot.contact_keyboard(MSG_SHARE_BUTTON))


def _handle_contact(chat_id, from_user, contact):
    if contact.get("user_id") != from_user["id"]:
        _reply(chat_id, MSG_FOREIGN_CONTACT)
        return

    token = TelegramLinkToken.objects.select_related("customer", "otp").filter(
        chat_id=chat_id, is_used=False, expires_at__gt=datetime.now(),
    ).order_by("-created_at").first()
    if not token:
        _reply(chat_id, MSG_LINK_EXPIRED, TelegramOTPBot.remove_keyboard())
        return

    try:
        phone = normalize_uz_phone(contact.get("phone_number", ""))
    except DjangoValidationError:
        phone = None
    if phone != token.customer.phone_number:
        _reply(chat_id, MSG_PHONE_MISMATCH)
        return

    TelegramLink.objects.update_or_create(
        phone_number=phone,
        defaults={
            "chat_id": chat_id,
            "telegram_user_id": from_user["id"],
            "username": (from_user.get("username") or "")[:64],
            "first_name": (from_user.get("first_name") or "")[:128],
        },
    )
    _complete_link(token, chat_id)


def handle_telegram_update(update):
    member_update = update.get("my_chat_member")
    if member_update:
        # user blocked / stopped the bot -> the binding can no longer deliver codes
        if member_update.get("new_chat_member", {}).get("status") == "kicked":
            TelegramLink.objects.filter(chat_id=member_update["chat"]["id"]).delete()
        return

    message = update.get("message")
    if not message or message.get("chat", {}).get("type") != "private" or "from" not in message:
        return

    chat_id = message["chat"]["id"]
    from_user = message["from"]
    text = (message.get("text") or "").strip()

    if "contact" in message:
        _handle_contact(chat_id, from_user, message["contact"])
    elif text.startswith("/start"):
        parts = text.split(maxsplit=1)
        _handle_start(chat_id, from_user, parts[1] if len(parts) > 1 else "")
    elif text in ("/unlink", "/stop"):
        deleted, _ = TelegramLink.objects.filter(chat_id=chat_id).delete()
        _reply(chat_id, MSG_UNLINKED if deleted else MSG_NOT_LINKED, TelegramOTPBot.remove_keyboard())
    else:
        _reply(chat_id, MSG_NO_TOKEN)
