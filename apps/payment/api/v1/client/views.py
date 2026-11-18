import base64
import binascii
import logging
import time

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

logger = logging.getLogger(__name__)

from apps.service.models import Order
from apps.payment.authentication import UzumBankBasicAuthentication
from apps.payment.methods.cancel_transaction import CancelTransaction
from apps.payment.methods.check_perform_transaction import CheckPerformTransaction
from apps.payment.methods.check_transaction import CheckTransaction
from apps.payment.methods.create_transaction import CreateTransaction
from apps.payment.methods.get_statement_transaction import GetStatement
from apps.payment.methods.perform_transaction import PerformTransaction
from apps.payment.models import ClickTransaction, CustomerCard, AtmosTransaction
from .serializers import (
    UzumBankCheckSerializer,
    UzumBankCreateSerializer,
    UzumBankConfirmSerializer,
    UzumBankReverseSerializer,
    UzumBankStatusSerializer,
    CreateHoldSerializer,
    ChargeHoldSerializer,
    CancelHoldSerializer,
    CustomerCardSerializer,
    CustomerCardUpdateSerializer
)
from apps.payment.services import UzumBankService, UzumBankErrors
from apps.payment.utils.exception_click import ClickErrorCode, ClickError
from apps.payment.utils.exception_payme import MethodNotFound, PerformTransactionDoesNotExist, PermissionDenied
from apps.payment.utils.exception_uzumbank import UzumBankAPIException, ErrorCode
from apps.payment.utils.logger import logged
from apps.payment.utils.utils_click import _serialize_request, get_order, create_transaction, get_transaction
from apps.payment.utils.utils_uzum import check_request, raise_exception_if_invalid
from apps.payment.services_pay.auth_services import AtmosAuthService, AtmosHoldService, AtmosBindWithCheckoutService
from apps.payment.atmos_hold import save_charge
import os
import uuid
from apps.authorization.models import Customer
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes


class PreparePaymentView(APIView):
    SECRET_KEY = settings.CLICK_SECRET_KEY

    @extend_schema(exclude=True)
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
            raise response

        if ClickTransaction.objects.filter(
                account_id=params["merchant_trans_id"],
                state=ClickTransaction.SUCCESSFULLY
        ).exists():
            response = ClickError(ClickErrorCode.ALREADY_PAID)
            logged("PreparePaymentView: already paid -> response: {}".format(response), "warning")
            raise response

        if float(getattr(order, settings.CLICK_AMOUNT_FIELD)) != float(params["amount"]):
            response = ClickError(ClickErrorCode.INCORRECT_AMOUNT)
            logged("PreparePaymentView: incorrect amount -> response: {}".format(response), "error")
            raise response

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
        return Response(response)



class CompletePaymentView(APIView):
    SECRET_KEY = settings.CLICK_SECRET_KEY

    @extend_schema(exclude=True)
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
            raise response

        if txn.state == ClickTransaction.SUCCESSFULLY:
            response = ClickError(ClickErrorCode.ALREADY_PAID)
            logged("CompletePaymentView: already paid -> response: {}".format(response.data), "warning")
            raise response

        txn.state = ClickTransaction.SUCCESSFULLY if int(params["error"]) == 0 else ClickTransaction.CANCELLED
        order.status = Order.COLLECTING if int(params["error"]) == 0 else Order.PENDING
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

    @extend_schema(exclude=True)
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


# class UzumBankPaymentView(ViewSet):
#
#     @extend_schema(exclude=True)
#     def transaction_check(self, request):
#         check_request(request)
#         account = request.data.get('params', {}).get('account')
#         order = get_order(account)
#
#         serializer = UzumAccountCheckSerializer(data=request.data, context={'order': order})
#         raise_exception_if_invalid(serializer)
#
#         return BaseUzumResponse(service_id=settings.SERVICE_ID_UZUM).success(
#             order_id=serializer.validated_data['params']['account'],amount=order.total_price,
#             trans_time=int(time.time() * 1000)
#         )
#
#     @extend_schema(exclude=True)
#     def transaction_create(self, request):
#         check_request(request)
#         account = request.data.get('params', {}).get('account')
#         order = get_order(account)
#
#         serializer = UzumTransactionInitSerializer(data=request.data, context={'order': order})
#         raise_exception_if_invalid(serializer)
#
#         validated = serializer.validated_data
#         trans_time = int(time.time() * 1000)
#         status = 'CREATED'
#
#         UzumBankTransactionsModel.objects.create(
#             trans_id=validated['transId'],
#             amount=validated['amount'],
#             order_id=validated['params']['account'],
#             status=status,
#             trans_time=trans_time,
#         )
#
#         return BaseUzumResponse(service_id=settings.SERVICE_ID_UZUM).with_trans(
#             trans_id=validated['transId'],
#             amount=validated['amount'],
#             status_str=status,
#             trans_time=trans_time,
#             order_id=validated['params']['account']
#         )
#
#     @extend_schema(exclude=True)
#     def transaction_confirm(self, request):
#         check_request(request)
#
#         serializer = UzumConFirmSerializer(data=request.data)
#         raise_exception_if_invalid(serializer)
#         data = serializer.validated_data
#
#         transaction = UzumBankTransactionsModel.objects.filter(trans_id=data['transId']).first()
#         if not transaction:
#             raise UzumBankAPIException(settings.SERVICE_ID_UZUM, ErrorCode.TRANSACTION_NOT_FOUND)
#
#         error_map = {
#             'CONFIRMED': ErrorCode.TRANSACTION_ALREADY_PAID,
#             'REVERSED': ErrorCode.TRANSACTION_CANCELED,
#         }
#         if transaction.status in error_map:
#             logged(error_map[transaction.status].message, "error")
#             raise UzumBankAPIException(settings.SERVICE_ID_UZUM, error_map[transaction.status])
#
#         order = get_order(transaction.order_id)
#         if not order:
#             logged(ErrorCode.VALIDATION_ERROR.message, "error")
#             raise UzumBankAPIException(settings.SERVICE_ID_UZUM, ErrorCode.VALIDATION_ERROR)
#
#         if order.status != 0:
#             logged(ErrorCode.ALREADY_PAID.message, "error")
#             raise UzumBankAPIException(settings.SERVICE_ID_UZUM, ErrorCode.ALREADY_PAID)
#
#         confirm_time = int(time.time() * 1000)
#
#         # Update transaction
#         transaction.status = 'CONFIRMED'
#         transaction.payment_source = serializer.data.get('paymentSource')
#         transaction.tariff = serializer.data.get('tariff')
#         transaction.processing_reference_number = serializer.data.get('processingReferenceNumber')
#         transaction.confirm_time = confirm_time
#         transaction.save()
#
#         # Update order
#         order.status = 1
#         order.save()
#
#         response_data = BaseUzumResponse(settings.SERVICE_ID_UZUM).with_trans(
#             trans_id=data['transId'],
#             amount=transaction.amount,
#             status_str='CONFIRMED',
#             confirm_time=confirm_time,
#             order_id=transaction.order_id,
#         ).data
#
#         return Response(data=response_data)
#
#     @extend_schema(exclude=True)
#     def transaction_reverse(self, request):
#         check_request(request)
#
#         serializer = UzumConFirmSerializer(data=request.data)
#         raise_exception_if_invalid(serializer)
#         data = serializer.validated_data
#         transaction = UzumBankTransactionsModel.objects.filter(trans_id=data['transId']).first()
#         if not transaction:
#             raise UzumBankAPIException(settings.SERVICE_ID_UZUM, ErrorCode.TRANSACTION_NOT_FOUND)
#         if transaction.status == "REVERSED":
#             raise UzumBankAPIException(settings.SERVICE_ID_UZUM, ErrorCode.TRANSACTION_ALREADY_CANCELED)
#         order = get_order(transaction.order_id)
#         if not order:
#             logged(ErrorCode.VALIDATION_ERROR.message, "error")
#             raise UzumBankAPIException(settings.SERVICE_ID_UZUM, ErrorCode.VALIDATION_ERROR)
#
#         if order.status == 0:
#             raise UzumBankAPIException(settings.SERVICE_ID_UZUM, ErrorCode.TRANSACTION_UNABLE_CANCELED)
#
#         reverse_time = int(time.time() * 1000)
#         transaction.status = 'REVERSED'
#         transaction.reverse_time = reverse_time
#         transaction.save()
#
#         order.status = 4
#         order.save()
#
#         response_data = BaseUzumResponse(settings.SERVICE_ID_UZUM).with_trans(
#             trans_id=data['transId'],
#             amount=transaction.amount,
#             status_str='REVERSED',
#             reverse_time=reverse_time,
#             order_id=transaction.order_id,
#         ).data
#
#         return Response(data=response_data)
#
#     @extend_schema(exclude=True)
#     def transaction_status(self, request):
#         check_request(request)
#         serializer = UzumConFirmSerializer(data=request.data)
#         raise_exception_if_invalid(serializer)
#         data = serializer.validated_data
#
#         transaction = UzumBankTransactionsModel.objects.filter(trans_id=data['transId']).first()
#         response_data = BaseUzumResponse(settings.SERVICE_ID_UZUM).with_trans(
#             trans_id=data['transId'],
#             amount=transaction.amount,
#             status_str=transaction.status,
#             trans_time=transaction.trans_time,
#             confirm_time=transaction.confirm_time,
#             reverse_time=transaction.reverse_time,
#             order_id=transaction.order_id
#         ).data
#
#         return Response(data=response_data)


class BaseUzumBankView(APIView):
    authentication_classes = [UzumBankBasicAuthentication]
    serializer_class = None

    def handle_exception(self, exc):
        logged(f"Uzum Bank webhook error: {exc}", "error")
        return Response(
            UzumBankService.error(
                service_id=None,
                error_code=UzumBankErrors.ACCESS_DENIED
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

    def _validate(self, request):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return None, Response(
                UzumBankService.error(
                    service_id=request.data.get("serviceId"),
                    error_code=UzumBankErrors.MISSING_PARAMS,
                    trans_id=request.data.get("transId"),
                    timestamp=request.data.get("timestamp"),
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        service_id = data["serviceId"]

        ok, err = UzumBankService.validate_service_id(service_id)
        if not ok:
            return None, Response(
                UzumBankService.error(
                    service_id=service_id,
                    error_code=err,
                    trans_id=data.get("transId"),
                    timestamp=data.get("timestamp"),
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        return data, None


class UzumBankCheckView(BaseUzumBankView):
    serializer_class = UzumBankCheckSerializer

    def post(self, request):
        data, error = self._validate(request)
        if error:
            return error

        params = data["params"]
        account = params.get("account")

        if not account:
            return Response(
                UzumBankService.error(
                    service_id=data["serviceId"],
                    error_code=UzumBankErrors.MISSING_PARAMS,
                    timestamp=data["timestamp"],
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        order = UzumBankService.get_order(str(account))
        ok, err, order_data = UzumBankService.validate_order(order)

        if not ok:
            return Response(
                UzumBankService.error(
                    service_id=data["serviceId"],
                    error_code=err,
                    timestamp=data["timestamp"]
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order_data["amount"]["value"] = int(order_data["amount"]["value"] / 100)

        return Response({
            "serviceId": data["serviceId"],
            "timestamp": UzumBankService.now_ts(),
            "status": "OK",
            "data": order_data
        })


class UzumBankCreateView(BaseUzumBankView):
    serializer_class = UzumBankCreateSerializer

    def post(self, request):
        data, error = self._validate(request)
        if error:
            return error

        account = data["params"].get("account")
        order = UzumBankService.get_order(str(account))

        ok, err, _ = UzumBankService.validate_order(order)
        if not ok:
            return Response(
                UzumBankService.error(data["serviceId"], err, data["transId"]),
                status=status.HTTP_400_BAD_REQUEST
            )

        ok, err = UzumBankService.validate_amount(order, data["amount"])
        if not ok:
            return Response(
                UzumBankService.error(data["serviceId"], err, data["transId"]),
                status=status.HTTP_400_BAD_REQUEST
            )

        ok, err, trans = UzumBankService.create_transaction(
            trans_id=str(data["transId"]),
            order=order,
            amount=data["amount"]
        )
        if not ok:
            return Response(
                UzumBankService.error(data["serviceId"], err, data["transId"]),
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            UzumBankService.transaction_response(trans, order, "create")
        )


class UzumBankConfirmView(BaseUzumBankView):
    serializer_class = UzumBankConfirmSerializer

    def post(self, request):
        data, error = self._validate(request)
        if error:
            return error

        payment_data = {
            "paymentSource": data["paymentSource"],
            "tariff": data.get("tariff"),
            "processingReferenceNumber": data.get("processingReferenceNumber"),
            "phone": data["phone"]
        }

        ok, err, trans = UzumBankService.confirm_transaction(
            trans_id=str(data["transId"]),
            pay=payment_data
        )
        if not ok:
            return Response(
                UzumBankService.error(data["serviceId"], err, data["transId"]),
                status=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.get(id=trans.order_id)

        return Response(
            UzumBankService.transaction_response(trans, order, "confirm")
        )



class UzumBankReverseView(BaseUzumBankView):
    serializer_class = UzumBankReverseSerializer

    def post(self, request):
        data, error = self._validate(request)
        if error:
            return error

        ok, err, trans = UzumBankService.reverse_transaction(
            trans_id=str(data["transId"])
        )

        if not ok:
            return Response(
                UzumBankService.error(data["serviceId"], err, data["transId"]),
                status=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.get(id=trans.order_id)

        return Response(
            UzumBankService.transaction_response(trans, order, "reverse")
        )



class UzumBankStatusView(BaseUzumBankView):
    serializer_class = UzumBankStatusSerializer

    def post(self, request):
        data, error = self._validate(request)
        if error:
            return error

        ok, err, trans = UzumBankService.get_transaction_status(
            trans_id=str(data["transId"])
        )

        if not ok:
            return Response(
                UzumBankService.error(data["serviceId"], err, data["transId"]),
                status=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.get(id=trans.order_id)

        return Response(
            UzumBankService.transaction_response(trans, order, "status")
        )
    
class AtmosCardBindCheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        summary="Atmos Checkout Card Bind Init",
        description=(
            "Generates an Atmos hosted checkout URL for card binding. "
            "Open the returned url in WebView. After the user binds the card via OTP, "
            "Atmos sends card_id to your callback URL."
        ),
        request=None,
        responses={200: OpenApiResponse(description="Checkout URL generated"), 400: OpenApiResponse(description="Bad Request")},
        tags=["Atmos"],
    )
    def post(self, request):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)

        # Access token obtained for Atmos API

        request_id = str(uuid.uuid4())
        account = str(request.user.id)

        try:
            data = AtmosBindWithCheckoutService.create_card_bind_session(
                access_token=access_token,
                request_id=request_id,
                store_id=os.environ["ATMOS_STORE_ID"],
                account=account,
                success_url=os.environ["ATMOS_SUCCESS_URL"],
            )
        except Exception as e:
            return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "url": data.get("url"),
            "payment_id": data.get("payment_id"),
            "token": data.get("token"),
            "message": "Open url in WebView to bind card",
        }, status=status.HTTP_200_OK)
    

class AtmosCardBindCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Atmos Checkout Card Bind Callback",
        description=(
            
        ),
        request=None,
        responses={200: OpenApiResponse(description="Checkout URL generated"), 400: OpenApiResponse(description="Bad Request")},
        tags=["Atmos"],
    )
    def post(self, request):
        card_id = request.data.get("card_id")
        account = request.data.get("account")

        # if api_key != os.environ["ATMOS_API_KEY_BIND"]:
        #     return Response({"status": 0, "message": "Invalid API key"}, status=status.HTTP_403_FORBIDDEN)

        if not card_id or not account:
            return Response({"status": 0, "message": "card_id and account are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = Customer.objects.filter(id=account).first()
        if not user:
            return Response({"status": 0, "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            access_token = AtmosAuthService.get_access_token()
            data = AtmosBindWithCheckoutService.get_cards_list(
                access_token=access_token,
            )
            cards_data = data.get("cardDataSmallList")
            
        except Exception as e:
            cards_data = []

        matched_card = next((card for card in cards_data if str(card.get("card_id")) == str(card_id)), None)

        card_info, created = CustomerCard.objects.update_or_create(
            card_id=str(card_id),
            defaults={
                "user": user,
                "card_id": matched_card.get("card_id"),
                "token": matched_card.get("card_token"),
                "pan": matched_card.get("pan"),
                "card_holder": matched_card.get("card_holder"),
                "expiry": matched_card.get("expiry"),
                "is_active": True,
            }
        )

        # the card becomes the default one when the customer has no other default card — also when it is a card
        # deleted earlier and bound again (the soft-deleted row is reused, so `created` is False then)
        has_default = CustomerCard.objects.filter(
            user=user, is_active=True, is_default=True,
        ).exclude(id=card_info.id).exists()
        if not has_default and not card_info.is_default:
            card_info.is_default = True
            card_info.save(update_fields=["is_default"])

        return Response({"status": 1, "message": "Успешно"}, status=status.HTTP_200_OK)


class AtmosCardDetailView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        summary="Atmos Get Card Details",
        description="Returns details of a previously bound card by card_id.",
        responses={200: OpenApiResponse(description="Card details returned"), 400: OpenApiResponse(description="Bad Request"), 404: OpenApiResponse(description="Not Found")},
        tags=["Atmos"],
    )
    def get(self, request, card_id):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)

        # Access token obtained for Atmos API

        # card = CustomerCard.objects.filter(card_id=card_id, user=request.user).first()
        # if not card:
        #     return Response({"error": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            data = AtmosBindWithCheckoutService.get_card_details(
                access_token=access_token,
                card_id=card_id,
            )
        except Exception as e:
            return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

        if data.get("status", {}).get("code") != 0:
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        card_data = data.get("payload", {}).get("card", {})

        return Response({
            "card_id": data.get("payload", {}).get("card_id"),
            "masked_pan": card_data.get("masked_pan"),
            "masked_card_holder": card_data.get("masked_card_holder"),
            "card_type": card_data.get("card_type"),
            "card_region": card_data.get("card_region"),
            "verified_state": card_data.get("verified_state"),
            "status_3ds": card_data.get("status_3ds"),
            "status": card_data.get("status"),
            "date_created": card_data.get("date_created"),
        }, status=status.HTTP_200_OK)

def _atmos_error_text(exc):
    """The body Atmos sent with an HTTP error (`raise_for_status`), cut to 1000 chars; "" when none."""
    response = getattr(exc, "response", None)
    return (response.text or "")[:1000] if response is not None else ""


def _cancel_unapplied_hold(access_token, order):
    """A hold Atmos created but refused to apply is cancelled at once (no SMS to the customer), so it does not
    hang on the card; `order.hold_id` keeps the id of that attempt, `payment_status` stays Pending. Errors are
    only logged — the customer already gets the apply error."""
    try:
        data = AtmosHoldService.cancel_hold(access_token=access_token, hold_id=order.hold_id, send_cancel_sms=False)
    except Exception as e:
        logger.warning(
            "Atmos hold cancel after failed apply failed: order_id=%s hold_id=%s error=%s body=%s",
            order.id, order.hold_id, e, _atmos_error_text(e),
        )
        return
    logger.info(
        "Atmos hold cancelled after failed apply: order_id=%s hold_id=%s result=%s",
        order.id, order.hold_id, data.get("result"),
    )


class AtmosCreateHoldView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        summary="Atmos Create Hold",
        description="Atmos Create Hold API endpoint. Client clicks Pay — freeze funds on card.",
        request=CreateHoldSerializer(),
        responses={200:OpenApiResponse(description="Created"), 400:OpenApiResponse(description="Bad Request")},
        tags=["Atmos"]
    )
    def post(self, request):
        order_id = request.data.get("order_id")
        duration = os.environ["ATMOS_HOLD_DURATION"]

        access_token = AtmosAuthService.get_access_token()
        logger.debug("access_token: %s", access_token)

        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # the default card, else the newest active one (a card bound again after a delete used to stay non-default)
        card = CustomerCard.objects.filter(user_id=request.user.id, is_active=True).order_by("-is_default", "-created_at").first()
        if not card:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Customer card not found")

        if not card.token:
            return Response({"error": "Card token not found"}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status != 0:
            return Response(
                {"error": f"Order is already in {order.payment_status} state"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Pre-check product quantities before holding any funds
        items = order.order_items.select_related('product').all()
        for item in items:
            if item.product.quantity < item.quantity:
                raise CustomApiException(
                    error_code=ErrorCodes.INVALID_INPUT,
                    message=f"Not enough quantity for product: {item.product.name}"
                )

        try:
            data = AtmosHoldService.create_hold(
                    access_token=access_token,
                    store_id=int(os.environ["ATMOS_STORE_ID"]),
                    account=order.id,
                    amount=int(order.total_price * 100),  # in tiins
                    duration=int(duration),
                    card_token=card.token,
                )
        except Exception as e:
            logger.warning(
                "Atmos hold/create failed: order_id=%s card_id=%s amount=%s error=%s body=%s",
                order.id, card.card_id, order.total_price, e, _atmos_error_text(e),
            )
            return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

        if data.get("result", {}).get("code") != "OK":
            logger.warning(
                "Atmos hold/create refused: order_id=%s card_id=%s amount=%s result=%s",
                order.id, card.card_id, order.total_price, data.get("result"),
            )
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        # save hold_id to order right away, so a hold that fails to apply is not lost
        order.hold_id = data.get("hold_id")
        order.save(update_fields=["hold_id"])

        try:
            apply_data = AtmosHoldService.apply_hold(
                access_token=access_token,
                hold_id=order.hold_id,
                otp="111111",
            )
        except Exception as e:
            logger.warning(
                "Atmos hold/apply failed: order_id=%s hold_id=%s error=%s body=%s",
                order.id, order.hold_id, e, _atmos_error_text(e),
            )
            _cancel_unapplied_hold(access_token, order)
            return Response({"error": f"Failed to apply hold: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        if apply_data.get("result", {}).get("code") != "OK":
            logger.warning(
                "Atmos hold/apply refused: order_id=%s hold_id=%s result=%s",
                order.id, order.hold_id, apply_data.get("result"),
            )
            _cancel_unapplied_hold(access_token, order)
            return Response(apply_data, status=status.HTTP_400_BAD_REQUEST)

        # the order stays Pending (BLD-486): the money is charged when an operator confirms it in the admin panel
        order.payment_status = 1
        order.save(update_fields=["payment_status"])

        return Response({
            "message": "Funds frozen successfully",
            "hold_id": order.hold_id,
            "hold_till": apply_data.get("hold_till"),
        }, status=status.HTTP_200_OK)


class AtmosChargeHoldView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        summary="Atmos Charge Hold",
        description="Deprecated: the server charges the hold itself when an operator confirms the order. Charges "
                    "the hold of the customer's own order; the order status is not changed.",
        request=ChargeHoldSerializer(),
        responses={200:OpenApiResponse(description="Charge"), 400:OpenApiResponse(description="Bad Request")},
        tags=["Atmos"]
    )
    def post(self, request):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)

        order_id = request.data.get("order_id")
        amount = request.data.get("amount")  # optional, for partial charge

        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # only the customer's own order; the row lock keeps the admin panel from charging it at the same time
            order = Order.objects.select_for_update().filter(id=order_id, customer_id=request.user.id).first()
            if not order:
                return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            if not order.hold_id:
                return Response({"error": "No hold found for this order"}, status=status.HTTP_400_BAD_REQUEST)

            if order.payment_status != 1:
                return Response(
                    {"error": f"Order must be in HOLD state to charge, current state: {order.payment_status}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                data = AtmosHoldService.charge_hold(
                    access_token=access_token,
                    hold_id=order.hold_id,
                    amount=amount,
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            if data.get("result", {}).get("code") != "OK":
                return Response(data, status=status.HTTP_400_BAD_REQUEST)

            # the order status is the operator's (BLD-486): it used to jump to Delivering here
            save_charge(order, data)

        return Response({
            "message": "Payment successful",
            "ofd_url": data.get("ofd_url"),
            "transaction": data.get("store_transaction") or {},
        }, status=status.HTTP_200_OK)


class AtmosCancelHoldView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        summary="Atmos Cancel Hold",
        description="Atmos Cancel Hold API endpoint",
        request=CancelHoldSerializer(),
        responses={200:OpenApiResponse(description="Cancel"), 400:OpenApiResponse(description="Bad Request")},
        tags=["Atmos"]
    )
    def post(self, request):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)

        order_id = request.data.get("order_id")

        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.filter(id=order_id, customer_id=request.user.id).first()
        if not order:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if not order.hold_id:
            return Response({"error": "No hold found for this order"}, status=status.HTTP_400_BAD_REQUEST)

        if order.payment_status != 1:
            return Response(
                {"error": f"Order must be in HOLD state to cancel, current state: {order.payment_status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            AtmosHoldService.cancel_hold(
                access_token=access_token,
                hold_id=order.hold_id,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.payment_status = 3
        order.save()

        return Response({"message": "Hold cancelled, funds released"}, status=status.HTTP_200_OK)


class CustomerCardViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        summary="Get customer cards list",
        description="Get customer cards list",
        responses={200: CustomerCardSerializer(many=True)},
        tags=["CustomerCard"],
    )
    def cards_list(self, request):
        cards = CustomerCard.objects.filter(user=request.user.id, is_active=True)
        serializer = CustomerCardSerializer(cards, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Get customer card detail",
        description="Get customer card detail",
        responses={200: CustomerCardSerializer()},
        tags=["CustomerCard"],
    )
    def card_detail(self, request, pk):
        card = CustomerCard.objects.filter(id=pk, user=request.user.id, is_active=True).first()
        if not card:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = CustomerCardSerializer(card, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update customer card",
        description="Update customer card",
        request=CustomerCardUpdateSerializer(),
        responses={202: CustomerCardUpdateSerializer()},
        tags=["CustomerCard"],
    )
    def card_update(self, request, pk):
        data = request.data
        card = CustomerCard.objects.filter(id=pk, user=request.user.id, is_active=True).first()
        if not card:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = CustomerCardUpdateSerializer(card, data=data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()

        if data.get("is_default") and data.get("is_default") is True:
            CustomerCard.objects.filter(
                user=request.user.id, is_active=True
            ).exclude(id=pk).update(is_default=False)

        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        summary="Delete customer card",
        description="Delete customer card",
        responses={204: OpenApiResponse(description="Customer card successfully deleted")},
        tags=["CustomerCard"],
    )
    def card_delete(self, request, pk):
        card = CustomerCard.objects.filter(id=pk, user=request.user.id, is_active=True).first()
        if not card:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        was_default = card.is_default
        card.is_active = False
        card.is_default = False
        card.save(update_fields=["is_active", "is_default"])
        if was_default:
            # the newest card left becomes the default one, so the customer can still pay
            next_card = CustomerCard.objects.filter(user=request.user.id, is_active=True).order_by("-created_at").first()
            if next_card:
                next_card.is_default = True
                next_card.save(update_fields=["is_default"])
        return Response(data={"result": "Customer card successfully deleted", "ok": True},
                        status=status.HTTP_204_NO_CONTENT)
