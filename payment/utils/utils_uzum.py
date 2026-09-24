from django.conf import settings
from .exception_uzumbank import UzumBankAPIException, ErrorCode
from .logger import logged
import base64
import binascii

def raise_auth_error(message="Authorization failed"):
    logged(logged_message=message, logged_type="error")
    raise UzumBankAPIException(
        service_id=settings.SERVICE_ID_UZUM,
        error_code_enum=ErrorCode.ACCESS_DENIED,
    )


def check_auth(token):
    if not isinstance(token, str):
        raise_auth_error("Authorization token is not a string")

    try:
        decoded = base64.b64decode(token.split()[-1]).decode('utf-8')
        key, password = decoded.split(':', 1)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise_auth_error("Invalid token format")

    if key != settings.SERVICE_UZUM_KEY or password != settings.SERVICE_UZUM_PASSWORD:
        raise_auth_error("Invalid merchant key or service ID")

def check_request(request):
    check_auth(request.META.get('HTTP_AUTHORIZATION'))
    service_id = request.data.get('serviceId', '')
    if service_id != settings.SERVICE_ID_UZUM:
        logged(
            logged_message=ErrorCode.INVALID_SERVICE_ID.message,
            logged_type="error"
        )
        raise UzumBankAPIException(
            service_id=settings.SERVICE_ID_UZUM,
            error_code_enum=ErrorCode.INVALID_SERVICE_ID,
        )



def raise_exception_if_invalid(serializer):
    if not serializer.is_valid():
        logged(logged_message=serializer.errors, logged_type="error")
        raise UzumBankAPIException(
            service_id=settings.SERVICE_ID_UZUM,
            error_code_enum=ErrorCode.MISSING_PARAMETERS
        )
