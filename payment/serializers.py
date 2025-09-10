from django.conf import settings
from rest_framework import serializers
from rest_framework.response import Response

from .models import MerchatTransactionsModel, AccountModel, UzumBankTransactionsModel
from .utils.exception_payme import IncorrectAmount, PerformTransactionDoesNotExist
from .utils.exception_uzumbank import UzumBankAPIException, ErrorCode
from .utils.logger import logged


class MerchatTransactionsModelSerializer(serializers.ModelSerializer):
    class Meta:
        model: MerchatTransactionsModel = MerchatTransactionsModel
        fields: str = "__all__"

    def validate(self, data):
        """
        Validate the data given to the MerchatTransactionsModel.
        """
        if data.get("order_id") is not None:
            try:
                order = AccountModel.objects.get(
                    id=data['order_id']
                )
                if order.total_price * 100 != int(data['amount']):
                    raise IncorrectAmount()

            except IncorrectAmount:
                raise IncorrectAmount()

        return data

    def validate_order_id(self, order_id) -> int:
        """
        Use this method to check if a transaction is allowed to be executed.
        :param order_id: string -> Order Indentation.
        """
        try:
            AccountModel.objects.get(
                id=order_id,
            )
        except AccountModel.DoesNotExist:
            raise PerformTransactionDoesNotExist()

        return order_id


class PaymeTransactionSerializer(serializers.ModelSerializer):
    account = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()
    create_time = serializers.SerializerMethodField()

    class Meta:
        model = MerchatTransactionsModel
        fields = [
            "transaction_id",
            "account",
            "amount",
            "time",
            "perform_time",
            "cancel_time",
            "state",
            "reason",
            "create_time"
        ]

    def get_account(self, obj):
        return {
            "order_id": obj.order_id
        }

    def get_reason(self, obj):
        try:
            return int(obj.reason) if obj.reason else None
        except ValueError:
            return None

    def get_create_time(self, obj):
        try:
            return int(obj.created_at_ms)
        except (TypeError, ValueError):
            return None


class BascUzumSerializer(serializers.Serializer):
    serviceId: int = serializers.IntegerField()
    timestamp: int = serializers.IntegerField()


class UzumBascAccountCheckSerializer(serializers.Serializer):
    account = serializers.IntegerField()

    def validate_account(self, account):
        order = self.context.get('order')
        if not order:
            logged(logged_message=ErrorCode.VALIDATION_ERROR.message, logged_type="error")
            raise UzumBankAPIException(
                service_id=settings.SERVICE_ID_UZUM,
                error_code_enum=ErrorCode.VALIDATION_ERROR
            )
        if order.status != 0:
            logged(logged_message=ErrorCode.ALREADY_PAID.message, logged_type="error")
            raise UzumBankAPIException(
                service_id=settings.SERVICE_ID_UZUM,
                error_code_enum=ErrorCode.ALREADY_PAID
            )

        return account


class UzumAccountCheckSerializer(BascUzumSerializer):
    params = UzumBascAccountCheckSerializer()


class UzumTransactionInitSerializer(UzumAccountCheckSerializer):
    transId = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, data):
        data = super().validate(data)
        order = self.context.get('order')
        amount = data['amount']
        trans_id = data['transId']

        if UzumBankTransactionsModel.objects.filter(trans_id=trans_id).exists():
            logged(logged_message=ErrorCode.TRANSACTION_ID_ALREADY_EXISTS.message, logged_type="error")
            raise UzumBankAPIException(
                service_id=settings.SERVICE_ID_UZUM,
                error_code_enum=ErrorCode.TRANSACTION_ID_ALREADY_EXISTS
            )

        if float(amount) != float(order.total_price):
            logged(logged_message=ErrorCode.INCORRECT_AMOUNT.message, logged_type="error")
            raise UzumBankAPIException(
                service_id=settings.SERVICE_ID_UZUM,
                error_code_enum=ErrorCode.INCORRECT_AMOUNT
            )

        return data


class UzumConFirmSerializer(BascUzumSerializer):
    transId = serializers.CharField()
    paymentSource = serializers.CharField(required=False)
    tariff = serializers.CharField(required=False)
    processingReferenceNumber = serializers.CharField(required=False)
    phone = serializers.CharField(max_length=50, required=False)


class BaseUzumResponse:
    def __init__(self, service_id: int):
        self.service_id = service_id

    def _base_response(self, status_str, data=None, extra=None, **time_fields):
        response = {
            "serviceId": self.service_id,
            "status": status_str,
        }
        # Vaqt maydonlarini shartli qo‘shish
        for key in ("transTime", "confirmTime", "reverseTime", 'timestamp'):
            if key in time_fields and time_fields[key] is not None:
                response[key] = time_fields[key]

        if data:
            response["data"] = data
        if extra:
            response.update(extra)

        return Response(response, status=200)

    def success(self, order_id=None, amount=None, status_str="OK", trans_time=None):
        data = {"account": {"value": str(order_id)}, "amount": {"value": amount}} if order_id else None
        return self._base_response(status_str=status_str, data=data, timestamp=trans_time)

    def with_trans(self, trans_id, amount, order_id, status_str="CREATED",
                   trans_time=None, confirm_time=None, reverse_time=None):
        extra = {
            "transId": trans_id,
            "amount": float(amount),
        }
        data = {"account": {"value": str(order_id)}}
        return self._base_response(
            status_str=status_str,
            data=data,
            extra=extra,
            transTime=trans_time,
            confirmTime=confirm_time,
            reverseTime=reverse_time
        )
