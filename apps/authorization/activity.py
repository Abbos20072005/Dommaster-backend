"""Customer journal (`CustomerActivity`): who did what with the account and from where. Written by the client auth
views (register / login / delete) and the admin customer API; read by `GET admin/customers/<id>/activity/`."""
import re

from apps.authorization.models import Customer, CustomerActivity, OTP

Kind = CustomerActivity.Kind

# admin panel labels (uz) of the customer fields an admin PATCH may change
FIELD_LABELS = {
    "full_name": "ism",
    "phone_number": "telefon",
    "email": "email",
    "verified": "tasdiqlangan",
    "segment": "segment",
    "tags": "teglar",
    "language": "til",
}


def platform_of(value):
    """A client `platform` value -> Customer.Platform value or None."""
    return value if value in Customer.Platform.values else None


def record(customer, kind, channel=None, actor=None, **data):
    return CustomerActivity.objects.create(customer=customer, kind=kind, channel=channel, actor=actor, data=data)


def record_admin(customer, kind, user, **data):
    return record(customer, kind, channel=CustomerActivity.ADMIN, actor=user, **data)


def activity_text(activity):
    """Journal line (uz) of one event."""
    data = activity.data or {}
    kind = activity.kind
    if kind == Kind.REGISTERED:
        by = "Telegram" if data.get("otp_channel") == OTP.Channel.TELEGRAM else "SMS"
        return f"Hisob yaratildi, telefon {by} kod bilan tasdiqlandi"
    if kind == Kind.LOGGED_IN:
        return "Hisobga kirildi"
    if kind == Kind.UPDATED:
        fields = [FIELD_LABELS.get(f, f) for f in data.get("fields", [])]
        return "Profil o'zgartirildi" + (f": {', '.join(fields)}" if fields else "")
    if kind == Kind.BLOCKED:
        return "Bloklandi"
    if kind == Kind.UNBLOCKED:
        return "Blokdan chiqarildi"
    if kind == Kind.ROLE_CHANGED:
        text = "PRO berildi" if data.get("new_value") == Customer.Role.PRORAB else "PRO bekor qilindi"
        return text + (f" ({data['reason']})" if data.get("reason") else "")
    if kind == Kind.PHONE_REVEALED:
        return "Telefon ko'rsatildi"
    if kind == Kind.LOGGED_OUT_ALL:
        return "Barcha qurilmalardan chiqarildi"
    if kind == Kind.DELETED:
        return "Hisob o'chirildi"
    return activity.get_kind_display()


def mask_phone(phone):
    """'+998901234567' -> '+998 90 *** ** 67'; another format keeps its first 4 and last 2 characters."""
    if not phone:
        return phone
    digits = re.sub(r"\D", "", phone)
    if re.fullmatch(r"998\d{9}", digits):
        return f"+998 {digits[3:5]} *** ** {digits[-2:]}"
    if len(phone) <= 6:
        return "*" * len(phone)
    return phone[:4] + "*" * (len(phone) - 6) + phone[-2:]
