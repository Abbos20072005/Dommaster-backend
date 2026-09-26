import re
import random
from django.core.validators import ValidationError


def validate_number(value):
    if not re.match(r'^\+998\d{9}$', value):
        raise ValidationError("Please enter uzbek number")

    return value


def normalize_uz_phone(value):
    """Accepts 12-digit uzbek number (998XXXXXXXXX, optional '+', spaces, '-', brackets) -> '+998XXXXXXXXX'."""
    digits = re.sub(r'[\s\-()+]', '', value or '')
    if not re.fullmatch(r'998\d{9}', digits):
        raise ValidationError("Please enter uzbek number in format 998XXXXXXXXX")
    return f"+{digits}"


def otp_code_generator():
    return random.randint(10000, 99999)
