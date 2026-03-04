import base64
import binascii
import time

from django.conf import settings
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from service.models import Order
from .authentication import UzumBankBasicAuthentication
from .methods.cancel_transaction import CancelTransaction
from .methods.check_perform_transaction import CheckPerformTransaction
from .methods.check_transaction import CheckTransaction
from .methods.create_transaction import CreateTransaction
from .methods.get_statement_transaction import GetStatement
from .methods.perform_transaction import PerformTransaction
from .models import ClickTransaction, UzumBankTransactionsModel
from .serializers import (
    UzumBankCheckSerializer,
    UzumBankCreateSerializer,
    UzumBankConfirmSerializer,
    UzumBankReverseSerializer,
    UzumBankStatusSerializer,
    CreateHoldSerializer,
    ApplyHoldSerializer,
    ChargeHoldSerializer,
    CancelHoldSerializer
)
from .services import UzumBankService, UzumBankErrors
from .utils.exception_click import ClickErrorCode, ClickError
from .utils.exception_payme import MethodNotFound, PerformTransactionDoesNotExist, PermissionDenied
from .utils.exception_uzumbank import UzumBankAPIException, ErrorCode
from .utils.logger import logged
from .utils.utils_click import _serialize_request, get_order, create_transaction, get_transaction
from .utils.utils_uzum import check_request, raise_exception_if_invalid
from .services_pay.auth_services import AtmosAuthService, AtmosHoldService, AtmosBindWithCheckoutService
import os
import uuid


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
            raise response

        if txn.state == ClickTransaction.SUCCESSFULLY:
            response = ClickError(ClickErrorCode.ALREADY_PAID)
            logged("CompletePaymentView: already paid -> response: {}".format(response.data), "warning")
            raise response

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


# class UzumBankPaymentView(ViewSet):
#
#     @swagger_auto_schema(auto_schema=None)
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
#     @swagger_auto_schema(auto_schema=None)
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
#     @swagger_auto_schema(auto_schema=None)
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
#     @swagger_auto_schema(auto_schema=None)
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
#     @swagger_auto_schema(auto_schema=None)
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
    @swagger_auto_schema(
        operation_summary="Atmos Checkout Card Bind Init",
        operation_description=(
            "Generates an Atmos hosted checkout URL for card binding. "
            "Open the returned url in WebView. After the user binds the card via OTP, "
            "Atmos sends card_id to your callback URL."
        ),
        responses={200: "Checkout URL generated", 400: "Bad Request"},
        tags=["Atmos"],
    )
    def post(self, request):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)

        print("Access token obtained: ", access_token)

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
    
class AtmosCardDetailView(APIView):
    @swagger_auto_schema(
        operation_summary="Atmos Get Card Details",
        operation_description="Returns details of a previously bound card by card_id.",
        responses={200: "Card details returned", 400: "Bad Request", 404: "Not Found"},
        tags=["Atmos"],
    )
    def get(self, request, card_id):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)

        print("Access token obtained: ", access_token)

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

class AtmosCreateHoldView(APIView):
    @swagger_auto_schema(
        operation_summary="Atmos Create Hold",
        operation_description="Atmos Create Hold API endpoint. Client clicks Pay — freeze funds on card.",
        request_body=CreateHoldSerializer(),
        responses={200:"Created", 400:"Bad Request"},
        tags=["Atmos"]
    )
    def post(self, request):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)
        
        print("Access token obtained: ", access_token)

        order_id = request.data.get("order_id")
        card_token = request.data.get("card_token")
        card_number = request.data.get("card_number")
        card_expiry = request.data.get("card_expiry")
        duration = request.data.get("duration", "60")  # default 60 mins

        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not card_token and not (card_number and card_expiry):
            return Response(
                {"error": "Provide either card_token or both card_number and card_expiry"},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status != 0:
            return Response(
                {"error": f"Order is already in {order.payment_status} state"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = AtmosHoldService.create_hold(
                    access_token=access_token,
                    store_id=os.environ["ATMOS_STORE_ID"],
                    account=str(order.id),
                    amount=str(order.total_price * 100),  # in tiins
                    duration=duration,
                    card_token=card_token,
                    card_number=card_number,
                    card_expiry=card_expiry,
                )
        except Exception as e:
            return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)
        
        if data.get("result", {}).get("code") != "OK":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        # save hold_id to order
        order.hold_id = data["hold_id"]
        order.save()

        return Response({
            "hold_id": data["hold_id"],
            "message": "OTP sent to card holder"
        }, status=status.HTTP_200_OK)


class AtmosApplyHoldView(APIView):
    @swagger_auto_schema(
        operation_summary="Atmos Apply Hold",
        operation_description="Atmos Apply Hold API endpoint",
        request_body=ApplyHoldSerializer(),
        responses={200:"Apply", 400:"Bad Request"},
        tags=["Atmos"]
    )
    def post(self, request):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)

        order_id = request.data.get("order_id")
        otp = request.data.get("otp")

        if not order_id or not otp:
            return Response({"error": "order_id and otp are required"}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.get(id=order_id)
        if not order:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if not order.hold_id:
            return Response({"error": "No hold found for this order, create hold first"}, status=status.HTTP_400_BAD_REQUEST)

        if order.payment_status != 0:
            return Response(
                {"error": f"Order is already in {order.payment_status} state"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = AtmosHoldService.apply_hold(
                access_token=access_token,
                hold_id=order.hold_id,
                otp=otp,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if data.get("result", {}).get("code") != "OK":
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        # funds are now frozen
        order.payment_status = 1
        order.save()

        return Response({
            "message": "Funds frozen successfully",
            "hold_till": data.get("hold_till"),
        }, status=status.HTTP_200_OK)


class AtmosChargeHoldView(APIView):
    @swagger_auto_schema(
        operation_summary="Atmos Charge Hold",
        operation_description="Atmos Charge Hold API endpoint",
        request_body=ChargeHoldSerializer(),
        responses={200:"Charge", 400:"Bad Request"},
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

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
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

        # money moved, order is paid
        order.payment_status = 2
        order.save()

        return Response({
            "message": "Payment successful",
            "ofd_url": data.get("ofd_url"),
            "transaction": data.get("store_transaction"),
        }, status=status.HTTP_200_OK)


class AtmosCancelHoldView(APIView):
    @swagger_auto_schema(
        operation_summary="Atmos Cancel Hold",
        operation_description="Atmos Cancel Hold API endpoint",
        request_body=CancelHoldSerializer(),
        responses={200:"Cancel", 400:"Bad Request"},
        tags=["Atmos"]
    )
    def post(self, request):
        access_token = AtmosAuthService.get_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate"}, status=status.HTTP_400_BAD_REQUEST)

        order_id = request.data.get("order_id")

        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.get(id=order_id)
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
