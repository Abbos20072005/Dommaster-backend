from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .utils.exception_click import ClickErrorCode, ClickError
from .models import ClickTransaction
from .utils.utils_click import _serialize_request, get_order, create_transaction, get_transaction


class PreparePaymentView(APIView):
    SECRET_KEY = settings.CLICK_SECRET_KEY

    def post(self, request, *args, **kwargs):
        data = request.data
        params, error = _serialize_request(data, prepare=True)
        if error:
            return error

        order = get_order(params["merchant_trans_id"])
        if not order:
            return Response(ClickError(ClickErrorCode.USER_NOT_FOUND), status=status.HTTP_400_BAD_REQUEST)

        if ClickTransaction.objects.filter(
                account_id=params["merchant_trans_id"],
                state=ClickTransaction.SUCCESSFULLY
        ).exists():
            return Response(ClickError(ClickErrorCode.ALREADY_PAID), status=status.HTTP_400_BAD_REQUEST)

        if float(getattr(order, settings.CLICK_AMOUNT_FIELD)) != float(params["amount"]):
            return Response(ClickError(ClickErrorCode.INCORRECT_AMOUNT), status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            txn = create_transaction(params, order)
            return Response({
                "click_trans_id": params["click_trans_id"],
                "merchant_trans_id": params["merchant_trans_id"],
                "merchant_prepare_id": txn.id,
                "error": 0,
                "error_note": "Success"
            }, status=status.HTTP_200_OK)


class CompletePaymentView(APIView):
    SECRET_KEY = settings.CLICK_SECRET_KEY

    def post(self, request, *args, **kwargs):
        data = request.data
        params, error = _serialize_request(data, prepare=False)
        if error:
            return error
        order = get_order(params["merchant_trans_id"])
        txn = get_transaction(params["merchant_prepare_id"])
        if not txn:
            return Response(ClickError(ClickErrorCode.TRANSACTION_NOT_FOUND), status=status.HTTP_400_BAD_REQUEST)

        if txn.state == ClickTransaction.SUCCESSFULLY:
            return Response(ClickError(ClickErrorCode.ALREADY_PAID), status=status.HTTP_400_BAD_REQUEST)

        txn.state = ClickTransaction.SUCCESSFULLY if params["error"] == 0 else ClickTransaction.CANCELLED
        order.status = 1 if params["error"] == 0 else 0
        order.save()
        txn.save()

        return Response({
            "click_trans_id": txn.transaction_id,
            "merchant_trans_id": txn.account_id,
            "merchant_confirm_id": txn.id,
            "error": 0 if txn.state == ClickTransaction.SUCCESSFULLY else -9,
            "error_note": "Success" if txn.state == ClickTransaction.SUCCESSFULLY else "Payment canceled"
        })
