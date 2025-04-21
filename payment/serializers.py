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
                if order.amount != int(data['amount']):
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