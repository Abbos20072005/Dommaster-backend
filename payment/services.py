import time
from typing import Dict, Optional
from django.conf import settings
from django.db import transaction
from .models import UzumBankTransactionsModel
from service.models import Order


class UzumBankErrors:
    ACCESS_DENIED = '10001'
    JSON_PARSE_ERROR = '10002'
    INVALID_OPERATION = '10003'
    MISSING_PARAMS = '10005'
    INVALID_SERVICE_ID = '10006'
    ATTRIBUTE_NOT_FOUND = '10007'
    ALREADY_PAID = '10008'
    PAYMENT_CANCELLED = '10009'
    TRANS_EXISTS = '10010'
    INVALID_AMOUNT = '10011'
    AMOUNT_TOO_LOW = '10012'
    AMOUNT_TOO_HIGH = '10013'
    TRANS_NOT_FOUND = '10014'
    TRANS_CANCELLED = '10015'
    TRANS_CONFIRMED = '10016'
    CANNOT_REVERSE = '10017'
    ALREADY_REVERSED = '10018'
    SERVICE_ERROR = '99999'


class UzumBankService:
    @staticmethod
    def now_ts() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def tiyin_to_sum(tiyin: int) -> float:
        return tiyin / 100

    @staticmethod
    def sum_to_tiyin(summa: float) -> int:
        return int(summa * 100)

    @staticmethod
    def get_order(account: str) -> Optional[Order]:
        try:
            return Order.objects.get(id=int(account))
        except Exception:
            return None

    @staticmethod
    def validate_service_id(service_id: int):
        if service_id != settings.SERVICE_ID_UZUM:
            return False, UzumBankErrors.INVALID_SERVICE_ID
        return True, None

    @staticmethod
    def validate_order(order: Order):
        if not order:
            return False, UzumBankErrors.ATTRIBUTE_NOT_FOUND, None

        if order.status == 1:
            return False, UzumBankErrors.ALREADY_PAID, None

        if order.status == 4:
            return False, UzumBankErrors.PAYMENT_CANCELLED, None

        data = {
            "account": {"value": str(order.id)},
            "amount": {"value": UzumBankService.sum_to_tiyin(order.total_price)},
        }

        return True, None, data

    @staticmethod
    def validate_amount(order: Order, amount: int):
        expected = UzumBankService.sum_to_tiyin(order.total_price)
        if amount != expected:
            return False, UzumBankErrors.INVALID_AMOUNT
        return True, None

    @staticmethod
    @transaction.atomic
    def create_transaction(trans_id: str, order: Order, amount: int):
        if UzumBankTransactionsModel.objects.filter(trans_id=trans_id).exists():
            return False, UzumBankErrors.TRANS_EXISTS, None

        try:
            trans = UzumBankTransactionsModel.objects.create(
                trans_id=trans_id,
                order_id=order.id,
                amount=UzumBankService.tiyin_to_sum(amount),
                status="CREATED",
                trans_time=UzumBankService.now_ts(),
            )
            return True, None, trans
        except Exception:
            return False, UzumBankErrors.SERVICE_ERROR, None

    @staticmethod
    @transaction.atomic
    def confirm_transaction(trans_id: str, pay: Dict):
        try:
            trans = UzumBankTransactionsModel.objects.select_for_update().get(trans_id=trans_id)
        except UzumBankTransactionsModel.DoesNotExist:
            return False, UzumBankErrors.TRANS_NOT_FOUND, None

        if trans.status == "REVERSED":
            return False, UzumBankErrors.TRANS_CANCELLED, None

        if trans.status == "CONFIRMED":
            return False, UzumBankErrors.TRANS_CONFIRMED, None

        try:
            trans.status = "CONFIRMED"
            trans.confirm_time = UzumBankService.now_ts()
            trans.payment_source = pay.get("paymentSource")
            trans.tariff = pay.get("tariff")
            trans.processing_reference_number = pay.get("processingReferenceNumber")
            trans.phone = pay.get("phone")
            trans.save()

            order = Order.objects.get(id=trans.order_id)
            order.status = 1
            order.save()

            return True, None, trans
        except:
            return False, UzumBankErrors.SERVICE_ERROR, None

    @staticmethod
    @transaction.atomic
    def reverse_transaction(trans_id: str):
        try:
            trans = UzumBankTransactionsModel.objects.select_for_update().get(trans_id=trans_id)
        except UzumBankTransactionsModel.DoesNotExist:
            return False, UzumBankErrors.TRANS_NOT_FOUND, None

        if trans.status == "REVERSED":
            return False, UzumBankErrors.ALREADY_REVERSED, None

        try:
            trans.status = "REVERSED"
            trans.reverse_time = UzumBankService.now_ts()
            trans.save()

            order = Order.objects.get(id=trans.order_id)
            order.status = 4
            order.save()

            return True, None, trans
        except:
            return False, UzumBankErrors.SERVICE_ERROR, None


    @staticmethod
    def get_transaction_status(trans_id: str):
        try:
            trans = UzumBankTransactionsModel.objects.get(trans_id=trans_id)
            return True, None, trans
        except UzumBankTransactionsModel.DoesNotExist:
            return False, UzumBankErrors.TRANS_NOT_FOUND, None


    @staticmethod
    def error(service_id, error_code, trans_id=None, timestamp=None, trans_time=None):
        res = {
            "status": "FAILED",
            "errorCode": error_code,
        }
        if service_id:
            res["serviceId"] = service_id
        if trans_id:
            res["transId"] = trans_id
        if timestamp:
            res["timestamp"] = timestamp
        if trans_time:
            res["transTime"] = trans_time
        return res

    @staticmethod
    def transaction_response(trans, order, mode: str):
        response = {
            "serviceId": settings.SERVICE_ID_UZUM,
            "transId": trans.trans_id,
            "status": trans.status,
            # "data": {
            #     "account": {"value": str(order.id)},
            #     "amount": {"value": UzumBankService.sum_to_tiyin(order.total_price)},
            # },
            "amount": UzumBankService.sum_to_tiyin(trans.amount),
        }

        if mode == "create":
            response["transTime"] = trans.trans_time
        elif mode == "confirm":
            response["confirmTime"] = trans.confirm_time
        elif mode == "reverse":
            response["reverseTime"] = trans.reverse_time
        elif mode == "status":
            response["transTime"] = trans.trans_time
            response["confirmTime"] = trans.confirm_time
            response["reverseTime"] = trans.reverse_time

        return response
