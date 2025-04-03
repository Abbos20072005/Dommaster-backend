import re
from django.core.validators import ValidationError

def validate_number(value):
    if not re.match(r'^\+998\d{9}$', value):
        raise ValidationError("Please enter uzbek number")

    return value
