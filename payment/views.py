import base64
import binascii

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .methods.cancel_transaction import CancelTransaction
from .methods.check_perform_transaction import CheckPerformTransaction
from .methods.check_transaction import CheckTransaction
from .methods.create_transaction import CreateTransaction
from .methods.get_statement_transaction import GetStatement
from .methods.perform_transaction import PerformTransaction
from .models import ClickTransaction
from .utils.exception_click import ClickErrorCode, ClickError
from .utils.exception_payme import MethodNotFound, PerformTransactionDoesNotExist, PermissionDenied
from .utils.logger import logged
from .utils.utils_click import _serialize_request, get_order, create_transaction, get_transaction
from drf_yasg.utils import swagger_auto_schema


class PreparePaymentView(APIView):
    SECRET_KEY = settings.CLICK_SECRET_KEY

    @swagger_auto_schema(auto_schema=None)
    def post(self, request, *args, **kwargs):
        data = request.data or ''
        logged("PreparePaymentView: received data -> {}".format(data or ''), "info")

        params, error = _serialize_request(data, prepare=True)
        if error:
            logged("PreparePaymentView: serialization error -> {}".format(error), "error")
            raise error

        order = get_order(params["merchant_trans_id"])
        if not order:
            response = ClickError(ClickErrorCode.USER_NOT_FOUND)
            logged("PreparePaymentView: order not found -> response: {}".format(response), "error")
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if ClickTransaction.objects.filter(
                account_id=params["merchant_trans_id"],
                state=ClickTransaction.SUCCESSFULLY
        ).exists():
            response = ClickError(ClickErrorCode.ALREADY_PAID)
            logged("PreparePaymentView: already paid -> response: {}".format(response), "warning")
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if float(getattr(order, settings.CLICK_AMOUNT_FIELD)) != float(params["amount"]):
            response = ClickError(ClickErrorCode.INCORRECT_AMOUNT)
            logged("PreparePaymentView: incorrect amount -> response: {}".format(response), "error")
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            txn = create_transaction(params, order)
            response = {
                "click_trans_id": params["click_trans_id"],
                "merchant_trans_id": params["merchant_trans_id"],
                "merchant_prepare_id": txn.id,
                "error": 0,
                "error_note": "Success"
            }
            logged("PreparePaymentView: success -> response: {}".format(response), "info")
            return Response(response, status=status.HTTP_200_OK)


class CompletePaymentView(APIView):
    SECRET_KEY = settings.CLICK_SECRET_KEY

    @swagger_auto_schema(auto_schema=None)
    def post(self, request, *args, **kwargs):
        data = request.data or ''
        logged("CompletePaymentView: received data -> {}".format(data), "info")

        params, error = _serialize_request(data, prepare=False)
        if error:
            logged("CompletePaymentView: serialization error -> {}".format(error), "error")
            raise error

        order = get_order(params["merchant_trans_id"])
        txn = get_transaction(params["merchant_prepare_id"])

        if not txn:
            response = ClickError(ClickErrorCode.TRANSACTION_NOT_FOUND)
            logged("CompletePaymentView: transaction not found -> response: {}".format(response.data), "error")
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if txn.state == ClickTransaction.SUCCESSFULLY:
            response = ClickError(ClickErrorCode.ALREADY_PAID)
            logged("CompletePaymentView: already paid -> response: {}".format(response.data), "warning")
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        txn.state = ClickTransaction.SUCCESSFULLY if int(params["error"]) == 0 else ClickTransaction.CANCELLED
        order.status = 1 if int(params["error"]) == 0 else 0
        order.save()
        txn.save()

        response = {
            "click_trans_id": txn.transaction_id,
            "merchant_trans_id": txn.account_id,
            "merchant_confirm_id": txn.id,
            "error": 0 if txn.state == ClickTransaction.SUCCESSFULLY else -9,
            "error_note": "Success" if txn.state == ClickTransaction.SUCCESSFULLY else "Payment canceled"
        }

        logged("CompletePaymentView: transaction {} -> response: {}".format(
            "completed successfully" if txn.state == ClickTransaction.SUCCESSFULLY else "cancelled",
            response
        ), "info")

        return Response(response)


class MerchantAPIView(APIView):
    permission_classes = ()
    authentication_classes = ()

    @swagger_auto_schema(auto_schema=None)
    def post(self, request, *args, **kwargs):
        password = request.META.get('HTTP_AUTHORIZATION')
        if self.authorize(password):
            incoming_data: dict = request.data
            incoming_method: str = incoming_data.get("method")
            logged_message: str = "Incoming {data}"

            logged(
                logged_message=logged_message.format(
                    method=incoming_method,
                    data=incoming_data
                ),
                logged_type="info"
            )
            try:
                paycom_method = self.get_paycom_method_by_name(
                    incoming_method=incoming_method
                )
            except ValidationError:
                raise MethodNotFound()
            except PerformTransactionDoesNotExist:
                raise PerformTransactionDoesNotExist()

            paycom_method = paycom_method(incoming_data)

        return Response(data=paycom_method)

    @staticmethod
    def get_paycom_method_by_name(incoming_method: str) -> object:
        """
        Use this static method to get the paycom method by name.
        :param incoming_method: string -> incoming method name
        """
        available_methods: dict = {
            "CheckTransaction": CheckTransaction,
            "CreateTransaction": CreateTransaction,
            "CancelTransaction": CancelTransaction,
            "PerformTransaction": PerformTransaction,
            "CheckPerformTransaction": CheckPerformTransaction,
            "GetStatement": GetStatement
        }

        try:
            MerchantMethod = available_methods[incoming_method]
        except Exception:
            error_message = "Unavailable method: %s" % incoming_method
            logged(
                logged_message=error_message,
                logged_type="error"
            )
            raise MethodNotFound(error_message=error_message)

        merchant_method = MerchantMethod()

        return merchant_method

    @staticmethod
    def authorize(password: str) -> None:
        """
        Authorize the Merchant.
        :param password: string -> Merchant authorization password
        """
        is_payme: bool = False
        error_message: str = ""

        if not isinstance(password, str):
            error_message = "Request from an unauthorized source!"
            logged(
                logged_message=error_message,
                logged_type="error"
            )
            raise PermissionDenied(error_message=error_message)

        password = password.split()[-1]

        try:
            password = base64.b64decode(password).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError):
            error_message = "Error when authorize request to merchant!"
            logged(
                logged_message=error_message,
                logged_type="error"
            )
            raise PermissionDenied(error_message=error_message)

        merchant_key = password.split(':')[-1]

        if merchant_key == settings.PAYME_KEY:
            is_payme = True

        if merchant_key != settings.PAYME_KEY:
            logged(
                logged_message="Invalid key in request!",
                logged_type="error"
            )

        if is_payme is False:
            raise PermissionDenied(
                error_message="Unavailable data for unauthorized users!"
            )

        return is_payme
