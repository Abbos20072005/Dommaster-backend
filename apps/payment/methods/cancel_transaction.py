import time
from django.db import transaction

from apps.payment.utils.get_params import get_params

from apps.payment.models import MerchatTransactionsModel, AccountModel
from apps.service.models.choices import PAYMENT_CANCELLED, PAYMENT_PAID
from apps.payment.api.v1.client.serializers import MerchatTransactionsModelSerializer
from apps.payment.utils.exception_payme import PerformTransactionDoesNotExist


class CancelTransaction:

    @transaction.atomic
    def __call__(self, data: dict):
        params = data.get("params", {})
        serializer = MerchatTransactionsModelSerializer(
            data=get_params(params)
        )
        serializer.is_valid(raise_exception=True)
        clean_data: dict = serializer.validated_data
        try:
            with transaction.atomic():
                transactions: MerchatTransactionsModel = \
                    MerchatTransactionsModel.objects.filter(
                        _id=clean_data.get('_id'),
                    ).first()
                if transactions.cancel_time == 0:
                    transactions.cancel_time = int(time.time() * 1000)
                if transactions.perform_time == 0:
                    transactions.state = -1
                if transactions.perform_time != 0:
                    transactions.state = -2
                transactions.reason = clean_data.get("reason")
                transactions.save()
                # the status is the operator's (BLD-486); a paid transaction cancelled = the money went back
                if transactions.perform_time != 0:
                    order = AccountModel.objects.get(id=transactions.order_id)
                    if order.payment_status == PAYMENT_PAID:
                        order.payment_status = PAYMENT_CANCELLED
                        order.save(update_fields=["payment_status"])

        except PerformTransactionDoesNotExist:
            raise PerformTransactionDoesNotExist()

        response: dict = {
            "result": {
                "state": transactions.state,
                "cancel_time": transactions.cancel_time,
                "transaction": transactions.transaction_id,
                "reason": int(transactions.reason),
            }
        }

        return response
