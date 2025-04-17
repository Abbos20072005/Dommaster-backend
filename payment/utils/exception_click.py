from enum import Enum
from rest_framework.exceptions import APIException


# Xatolik kodlari va izohlarini saqlash uchun Enum
class ClickErrorCode(Enum):
    SIGN_CHECK_FAILED = (-1, "SIGN CHECK FAILED!")
    INCORRECT_AMOUNT = (-2, "Incorrect parameter amount")
    ACTION_NOT_FOUND = (-3, "Action not found")
    ALREADY_PAID = (-4, "Already paid")
    USER_NOT_FOUND = (-5, "User does not exist")
    TRANSACTION_NOT_FOUND = (-6, "Transaction does not exist")
    FAILED_TO_UPDATE_USER = (-7, "Failed to update user")
    CLICK_REQUEST_ERROR = (-8, "Error in request from click")
    TRANSACTION_CANCELLED = (-9, "Transaction cancelled")


# Asosiy xatolik klassi
class ClickError(APIException):
    status_code = 400
    default_detail = "Click error occurred"
    default_code = "click_error"

    def __init__(self, error_code: ClickErrorCode):
        # Xatolik kodlari va izohlarini Enum'dan olish
        self.detail = {
            "error": error_code.value[0],  # xatolik kodi
            "error_note": error_code.value[1]  # xatolik izohi
        }
