from django.conf import settings

from rest_framework import serializers


from .models import MerchatTransactionsModel, AccountModel
from .utils.exception_payme import IncorrectAmount,PerformTransactionDoesNotExist


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
                if order.total_price != int(data['amount']):
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