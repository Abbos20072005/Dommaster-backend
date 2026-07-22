from rest_framework import status
from enum import Enum


class ErrorCodes(Enum):
    UNAUTHORIZED = 1
    INVALID_INPUT = 2
    FORBIDDEN = 3
    NOT_FOUND = 4
    VALIDATION_FAILED = 5
    ALREADY_EXISTS = 6
    USER_DOES_NOT_EXIST = 7
    INCORRECT_PASSWORD = 8
    USER_BLOCKED = 9
    ATTEMPT_ALREADY_EXISTS = 10
    OTP_KEY_NOT_FOUND = 11
    INCORRECT_OTP = 12
    OTP_EXPIRED = 13
    OTP_ATTEMPTS_LIMITE = 14
    INVALID_TOKEN = 15
    OTP_NOT_EXPIRED = 16
    NEW_PASSWORD_NOT_MATCH = 17
    OLD_PASSWORD_NOT_MATCH = 18
    PROMOCODE_EXPIRED = 19
    OTP_NOT_FOUND = 20
    PRODUCT_QUANTITY_NOT_ENOUGH = 21
    REFRESH_TOKEN_INVALID = 22
    INTEGRATION_API_KEY_INVALID = 23
    INTEGRATION_INVALID_DATA = 24
    INTEGRATION_IMAGE_DECODE_FAILED = 25
    INTEGRATION_CATEGORY_NOT_FOUND = 26
    INTEGRATION_SUB_CATEGORY_NOT_FOUND = 27


error_messages = {
    1: {"result": "Unauthorized access", "http_status": status.HTTP_401_UNAUTHORIZED},
    2: {"result": "Invalid input provided", "http_status": status.HTTP_400_BAD_REQUEST},
    3: {"result": "Permission denied", "http_status": status.HTTP_403_FORBIDDEN},
    4: {"result": "Resource not found", "http_status": status.HTTP_404_NOT_FOUND},
    5: {"result": "Validate Error", "http_status": status.HTTP_400_BAD_REQUEST},
    6: {"result": "User Already exists", "http_status": status.HTTP_400_BAD_REQUEST},
    7: {"result": "User Does not exist", "http_status": status.HTTP_400_BAD_REQUEST},
    8: {"result": "Incorrect password", "http_status": status.HTTP_400_BAD_REQUEST},
    9: {"result": "User Blocked, Contact admins", "http_status": status.HTTP_400_BAD_REQUEST},
    10: {"result": "You already have 3 attempts, please return after 12 times",
         "http_status": status.HTTP_400_BAD_REQUEST},
    11: {"result": "Otp_key does not exist", "http_status": status.HTTP_400_BAD_REQUEST},
    12: {"result": "incorrect otp_code", "http_status": status.HTTP_400_BAD_REQUEST},
    13: {"result": "OTP key Expired", "http_status": status.HTTP_400_BAD_REQUEST},
    14: {"result": "OTP attempt riched it's limit", "http_status": status.HTTP_400_BAD_REQUEST},
    15: {"result": "Invalid Token", "http_status": status.HTTP_400_BAD_REQUEST},
    16: {"result": "Otp not expired", "http_status": status.HTTP_400_BAD_REQUEST},
    17: {"result": "New password and confirming new passoword fields are not match",
         "http_status": status.HTTP_400_BAD_REQUEST},
    18: {"result": "Old password not match your current password", "http_status": status.HTTP_400_BAD_REQUEST},
    19: {"result": "Promocode expired", "http_status": status.HTTP_400_BAD_REQUEST},
    20: {"result": "Otp not found", "http_status": status.HTTP_400_BAD_REQUEST},
    21: {"result": "Product does not enough in warehouse", "http_status": status.HTTP_400_BAD_REQUEST},
    22: {"result": "Refresh token is invalid or expired", "http_status": status.HTTP_401_UNAUTHORIZED},
    23: {"result": "Invalid integration API key", "http_status": status.HTTP_401_UNAUTHORIZED},
    24: {"result": "Invalid integration data", "http_status": status.HTTP_400_BAD_REQUEST},
    25: {"result": "Failed to decode image", "http_status": status.HTTP_400_BAD_REQUEST},
    26: {"result": "Category not found", "http_status": status.HTTP_404_NOT_FOUND},
    27: {"result": "Sub category not found", "http_status": status.HTTP_404_NOT_FOUND},
}


def get_error_message(code):
    return error_messages.get(code, 'Unknown error')
