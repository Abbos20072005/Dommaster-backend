from datetime import datetime

from payment.models import MerchatTransactionsModel
from payment.serializers import PaymeTransactionSerializer


class GetStatement:
    def __call__(self, data: dict):
        params = data.get("params", {})
        timestamp_from = params.get("from")
        timestamp_to = params.get("to")

        transactions = PaymeTransactionSerializer(
            MerchatTransactionsModel.objects.filter(created_at_ms__gte=timestamp_from,
                                                    created_at_ms__lte=timestamp_to), many=True).data

        response: dict = {
            "id": data.get("id"),
            'result': {
                'transactions': transactions

            }
        }

        return response
