# your_app/exceptions.py

from enum import Enum
from rest_framework.exceptions import APIException
from rest_framework import status
import time


class ErrorCode(Enum):
    ACCESS_DENIED = ("10001", "Доступ запрещен - Ошибка авторизации")
    JSON_PARSE_ERROR = ("10002", "Ошибка парсинга JSON объекта с параметрами запроса")
    INVALID_OPERATION = ("10003", "Недопустимая операция - Неверный HTTP метод")
    MISSING_PARAMETERS = ("10005", "Отсутствуют обязательные параметры в запросе")
    INVALID_SERVICE_ID = ("10006", "Неверный serviceId")
    ATTRIBUTE_NOT_FOUND = ("10007", "Дополнительный атрибут платежа не найден")
    ALREADY_PAID = ("10008", "Платеж уже оплачен")
    PAYMENT_CANCELED = ("10009", "Платеж отменен")
    TRANSACTION_ID_ALREADY_EXISTS = ("10010", "Транзакция с указанным идентификатором transId уже создана")
    INCORRECT_AMOUNT = ("10011", "Неверная сумма")
    TRANSACTION_NOT_FOUND = ("10014", "Транзакция не найдена")
    TRANSACTION_CANCELED = ("10015", "Транзакция отменена")
    TRANSACTION_ALREADY_PAID = ("10016", "Транзакция с идентификатором transId уже подтверждена")
    TRANSACTION_UNABLE_CANCELED = ("10017", "Невозможно отменить транзакцию")
    TRANSACTION_ALREADY_CANCELED = ("10018", "Транзакция с идентификатором transId уже отменена")
    VALIDATION_ERROR = ("99999", "Ошибка проверки данных - Сервис недоступен, повторите попытку позже")


    def __init__(self, code, message):
        self.code = code
        self.message = message

    def as_dict(self):
        return {
            "errorCode": self.code,
            "errorMessage": self.message,
        }


class UzumBankAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'failed'

    def __init__(self, service_id: int, error_code_enum: ErrorCode, trans_id: str = None):
        self.service_id = service_id
        self.error_code = error_code_enum.code
        self.trans_id = trans_id

        detail = {
            "serviceId": self.service_id,
            "status": "FAILED",
            "errorCode": self.error_code,
        }

        if self.trans_id:
            detail["transId"] = self.trans_id
            detail["transTime"] = int(time.time() * 1000)
        else:
            detail["timestamp"] = int(time.time() * 1000)

        super().__init__(detail=detail)
