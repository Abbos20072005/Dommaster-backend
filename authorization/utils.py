import re
import random
import string
from django.core.validators import ValidationError


def validate_number(value):
    if not re.match(r'^\+998\d{9}$', value):
        raise ValidationError("Please enter uzbek number")

    return value


def otp_code_generator():
    return random.randint(10000, 99999)


def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits
    random_password = ''.join(random.choice(characters) for _ in range(length))
    return random_password
