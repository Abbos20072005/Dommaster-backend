from enum import Enum
from typing import Any


class NotificationEnumCode(Enum):
    CONTRACT_CREATE = 1



NotificationMessages = {
    1: {
        'text_uz': "{} sizni №{} raqamli va {} sanadan boshlanadigan shartnomani imzolashga taklif qildi.",
        'text_ru': "{} приглосил(а) подписать Договор №{} который вступает в силу с {}.",
        "type": 1}
    }


def send_contract_notification(enum_code: int) -> dict[str, Any]:
    return NotificationMessages.get(enum_code, {})
