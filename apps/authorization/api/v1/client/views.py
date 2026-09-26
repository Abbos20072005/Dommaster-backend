import uuid
from rest_framework.viewsets import ViewSet
from django.db.models import Q
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from utils.send_notification import send_notification
from apps.authorization.models import Customer, OTP, FcmToken, CustomerAddresses, PasswordResetToken
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from datetime import datetime, timedelta
from django.contrib.auth.hashers import check_password, make_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from apps.authorization.utils import otp_code_generator
from .serializers import CustomerSerializer, LoginSerializer, RegisterSerializer, OTPVerifySerializer, \
    OTPResendSerializer, ChangePasswordSerializer, ForgotPasswordSerializer, CustomerAddressesSerializer, \
    CustomerAddressesUpdateSerializer, CustomerAddressesCreateSerializer, ResetPasswordSerializer, FCMTokenSerializer, \
    FCMTokenRequestSerializer, FCMTokenDeleteSerializer, TokenRefreshSerializer, PhoneAuthSerializer, \
    TelegramOTPSerializer
from django.utils import timezone
from apps.integration.eskiz import EskizOTP
from utils.send_notification import send_notification_to_customer
from apps.authorization.services import create_otp, check_otp_limit
from apps.authorization.telegram_services import request_telegram_otp, is_telegram_linked, unlink_telegram, handle_telegram_update
from apps.authorization.models import TelegramLink
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def issue_customer_tokens(customer):
    """Blocked customers get no tokens; `last_login` feeds the admin "active (30 days)" stat."""
    if customer.is_blocked:
        raise CustomApiException(error_code=ErrorCodes.USER_BLOCKED)

    customer.last_login = timezone.now()
    customer.save(update_fields=["last_login"])

    refresh = RefreshToken.for_user(customer)
    refresh['role'] = customer.role
    access_token = refresh.access_token
    access_token['role'] = customer.role
    return str(access_token), str(refresh)


class AuthViewSet(ViewSet):
    @extend_schema(
        summary="Login / Register by phone",
        description="Phone number + role (optional, default user). Sends OTP; verify via otp/verify/ "
                              "to get tokens. Role is applied only when a new customer is created.",
        request=PhoneAuthSerializer(),
        responses={200: OpenApiResponse(description="otp_key, is_new, telegram_linked")},
        tags=["Auth"]
    )
    def phone_auth(self, request):
        serializer = PhoneAuthSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        phone = serializer.validated_data["phone_number"]
        customer = Customer.objects.filter(phone_number=phone).order_by("-verified", "-created_at").first()
        is_new = customer is None
        if is_new:
            customer = Customer.objects.create(phone_number=phone, role=serializer.validated_data["role"])

        otp = create_otp(customer)
        EskizOTP.send_otp_service(phone, f"Код подтверждения для входа в приложение Buildex Go: {otp.otp_code}")

        device_id = serializer.validated_data.get("device_id")
        if device_id:
            FcmToken.objects.get_or_create(customer=customer, device_id=device_id,
                                           defaults={"fcm_token": device_id})

        return Response(data={"result": {"otp_key": otp.otp_key, "is_new": is_new,
                                          "telegram_linked": is_telegram_linked(phone)}, "ok": True},
                        status=status.HTTP_200_OK)

    @extend_schema(
        summary="Account delete",
        description="Account delete",
        responses={204: OpenApiResponse(description="Account successfully deleted")},
        tags=["Auth"]
    )
    def delete_account(self, request):
        customer = Customer.objects.filter(id=request.user.id).first()
        if not customer:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)
        
        customer.delete()
        return Response(data={"result": "Account successfully deleted", "ok": True},
                        status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        summary="Customer login",
        description="Customer login",
        request=LoginSerializer(),
        responses={200: LoginSerializer()},
        tags=["Auth"]
    )
    def login(self, request):
        login_serializer = LoginSerializer(data=request.data, context={'request': request})
        if not login_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=login_serializer.errors)

        login_email = login_serializer.validated_data.get("email")
        login_phone = login_serializer.validated_data.get("phone_number")

        lookup = Q(phone_number=login_phone)
        if login_email:
            lookup |= Q(email=login_email)

        customer = Customer.objects.filter(lookup).first()

        if not customer:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

        if check_password(login_serializer.validated_data.get('password'), customer.password) is False:
            raise CustomApiException(error_code=ErrorCodes.INCORRECT_PASSWORD)

        access_token, refresh = issue_customer_tokens(customer)

        return Response(data={'access_token': access_token, 'refresh_token': refresh, 'ok': True},
                        status=status.HTTP_200_OK)

    @extend_schema(
        summary="Refresh token",
        description="Get new access and refresh tokens using refresh token",
        request=TokenRefreshSerializer(),
        responses={200: TokenRefreshSerializer()},
        tags=["Auth"]
    )
    def refresh_token(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        refresh_token = serializer.validated_data.get("refresh")
        try:
            refresh = RefreshToken(refresh_token)
        except (TokenError, InvalidToken):
            raise CustomApiException(error_code=ErrorCodes.REFRESH_TOKEN_INVALID)

        customer = Customer.objects.filter(id=refresh.payload.get("user_id")).first()
        if not customer:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

        new_access, new_refresh = issue_customer_tokens(customer)

        return Response(data={"access_token": new_access, "refresh_token": new_refresh, "ok": True},
                        status=status.HTTP_200_OK)

    @extend_schema(
        summary="Customer Register",
        description="Customer Register",
        request=RegisterSerializer(),
        responses={201: RegisterSerializer()},
        tags=["Auth"]
    )
    def register(self, request):
        serializer = RegisterSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        email = request.data.get("email")
        phone = request.data.get("phone_number")

        lookup = Q(phone_number=phone)
        if email:
            lookup |= Q(email=email)

        customer = Customer.objects.filter(lookup, verified=True).first()
        if customer:
            raise CustomApiException(error_code=ErrorCodes.ALREADY_EXISTS)

        customer_none = Customer.objects.filter(lookup, verified=False).first()

        if customer_none is None:
            customer_save = serializer.save()
            if customer_save.id is None:
                raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

            otp = create_otp(customer_save)
            # message = (
            #     f' Project: Dommaster \nuser: {customer_save.id} \nphone_number: {customer_save.phone_number}\ncode: {otp.otp_code} '
            #     f'\notp_key: {otp.otp_key} '
            #     f'\nReset: {otp.resend}'
            #     f'\nexpires: {otp.expire_at}')
            # send_notification(message)
            EskizOTP.send_otp_service(customer_save.phone_number, f"Код подтверждения для регистрации в приложение Buildex Go: {otp.otp_code}")
            fcm_token = FcmToken.objects.create(customer=customer_save, fcm_token=request.data.get("device_id", ""))
            fcm_token.save()
            return Response(data={"result": {"otp_key": otp.otp_key}, "ok": True}, status=status.HTTP_201_CREATED)

        serializer_customer = CustomerSerializer(customer_none, data=serializer.validated_data, partial=True,
                                                 context={"request": request})
        if not serializer_customer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer_customer.errors)

        serializer_customer.save()
        otp = create_otp(customer_none)

        # message = (
        #     f' Project: Dommaster \nuser: {customer_none.id} \nphone_number: {customer_none.phone_number}\ncode: {otp.otp_code} '
        #     f'\notp_key: {otp.otp_key} '
        #     f'\nReset: {otp.resend}'
        #     f'\nexpires: {otp.expire_at}')
        # send_notification(message)
        EskizOTP.send_otp_service(customer_none.phone_number, f"Код подтверждения для регистрации в приложение Buildex Go: {otp.otp_code}")
        fcm_token = FcmToken.objects.create(customer=customer_none, fcm_token=request.data.get("device_id", ""))
        fcm_token.save()
        return Response(data={"result": {"otp_key": otp.otp_key}, 'ok': True}, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Auth me",
        description="Auth me",
        responses={200: CustomerSerializer()},
        tags=["Auth"]
    )
    def auth_me(self, request):
        customer = Customer.objects.filter(id=request.user.id).first()
        if not customer:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = CustomerSerializer(customer, context={'request': request})
        return Response(data={'result': serializer.data, 'ok': True}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update user information",
        description="Update user information",
        request=CustomerSerializer(),
        responses={202: CustomerSerializer()},
        tags=["Auth"]
    )
    def update_customer_info(self, request):
        data = request.data
        customer = Customer.objects.filter(id=request.user.id).first()
        if not customer:
            raise CustomApiException(error_code=ErrorCodes.FORBIDDEN)

        serializer = CustomerSerializer(customer, data=data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        summary="Change password",
        description="Change password",
        request=ChangePasswordSerializer(),
        responses={202: OpenApiResponse(description="Password successfully changed")},
        tags=["Auth"]
    )
    def change_password(self, request):
        data = request.data
        customer = Customer.objects.filter(id=request.user.id).first()
        if not customer:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

        serializer = ChangePasswordSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        old_password = serializer.validated_data.get("old_password")
        new_password = serializer.validated_data.get("new_password")
        confirm_new_password = serializer.validated_data.get("confirm_new_password")

        if new_password != confirm_new_password:
            raise CustomApiException(error_code=ErrorCodes.NEW_PASSWORD_NOT_MATCH)

        if not check_password(old_password, customer.password):
            raise CustomApiException(error_code=ErrorCodes.OLD_PASSWORD_NOT_MATCH)

        customer.password = make_password(new_password)
        customer.save(update_fields=["password"])
        return Response(data={"result": "Password successfully updated", "ok": True}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        summary="Forgot password",
        description="Forgot password",
        request=ForgotPasswordSerializer(),
        responses={200: OpenApiResponse(description="Message sent to {}")},
        tags=["Auth"]

    )
    def forgot_password(self, request):
        data = request.data
        serializer = ForgotPasswordSerializer(data=data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        customer = Customer.objects.filter(phone_number=data.get("phone_number")).first()
        if not customer:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

        all_otp = OTP.objects.filter(customer_id=customer.id)
        last_otp = all_otp.order_by("-created_at").first()
        if all_otp.count() >= 3 and last_otp.created_at > datetime.now() - timedelta(hours=12):
            raise CustomApiException(error_code=ErrorCodes.ATTEMPT_ALREADY_EXISTS,
                                     time=last_otp.created_at + timedelta(hours=12))

        otp_code = otp_code_generator()
        otp = OTP.objects.create(customer_id=customer.id, otp_code=otp_code, resend=False)
        otp.expire_at = otp.created_at + timedelta(minutes=1)
        otp.save()

        latest_otp = all_otp.order_by("-created_at").exclude(otp_key=otp.otp_key).first()
        if latest_otp and latest_otp.created_at < datetime.now() - timedelta(hours=12) and all_otp.count() >= 2:
            all_otp.exclude(otp_key=otp.otp_key).delete()

        # message = (
        #     f' Project: Dommaster \nuser: {customer.id} \nphone_number: {customer.phone_number}\ncode: {otp.otp_code} '
        #     f'\notp_key: {otp.otp_key} '
        #     f'\nReset: {otp.resend}'
        #     f'\nexpires: {otp.expire_at}')
        # send_notification(message)
        EskizOTP.send_otp_service(customer.phone_number, f"Код подтверждения для регистрации в приложение Buildex Go: {otp.otp_code}")
        return Response(data={"result": {"otp_key": otp.otp_key}, "ok": True},
                        status=status.HTTP_200_OK)

    @extend_schema(
        summary="Verify reset otp",
        description="Verify reset otp",
        request=OTPVerifySerializer(),
        responses={200: OpenApiResponse(description="OTP successfully verified")},
        tags=["Auth"]
    )
    def verify_reset_otp(self, request):
        data = request.data
        data_serializer = OTPVerifySerializer(data=data)
        if not data_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=data_serializer.errors)

        otp = OTP.objects.filter(otp_key=data_serializer.validated_data.get("otp_key")).order_by(
            "-created_at").first()
        if not otp:
            raise CustomApiException(error_code=ErrorCodes.OTP_KEY_NOT_FOUND, message="OTP not found")

        otp.count_attempts += 1
        otp.save(update_fields=["count_attempts"])
        if otp.otp_code != data_serializer.validated_data.get("otp_code"):
            raise CustomApiException(error_code=ErrorCodes.INCORRECT_OTP)

        if otp.expire_at < datetime.now() - timedelta(minutes=1):
            raise CustomApiException(error_code=ErrorCodes.OTP_EXPIRED)

        reset_token = uuid.uuid4().hex
        PasswordResetToken.objects.create(
            customer=otp.customer,
            token=reset_token,
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        return Response(data={"result": {"reset_token": reset_token}, "ok": True}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="",
        description="",
        request=ResetPasswordSerializer(),
        responses={200: OpenApiResponse(description="Password successfully changed")},
        tags=["Auth"]
    )
    def reset_password(self, request):
        data = request.data
        data_serializer = ResetPasswordSerializer(data=data)
        if not data_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=data_serializer.errors)

        reset_password = PasswordResetToken.objects.filter(token=data_serializer.validated_data.get("reset_token"),
                                                           is_used=False).first()
        if not reset_password:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Reset password information not found")

        if reset_password.expires_at < datetime.now() - timedelta(minutes=10):
            raise CustomApiException(error_code=ErrorCodes.INVALID_TOKEN, message="Reset token expired")

        customer = Customer.objects.filter(id=reset_password.customer_id).first()
        if not customer:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="User not found")

        new_password = data_serializer.validated_data.get("new_password")
        confirm_new_password = data_serializer.validated_data.get("confirm_new_password")

        if new_password != confirm_new_password:
            raise CustomApiException(error_code=ErrorCodes.NEW_PASSWORD_NOT_MATCH)

        customer.password = make_password(new_password)
        customer.save(update_fields=["password"])

        return Response(data={"result": "Password successfully changed", "ok": True}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Get customer address",
        description="Get customer address",
        responses={200: CustomerAddressesSerializer(many=True)},
        tags=["Auth"]
    )
    def addresses_list(self, request):
        addresses = CustomerAddresses.objects.filter(customer=request.user.id)
        serializer = CustomerAddressesSerializer(addresses, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update customer address",
        description="Update customer address",
        request=CustomerAddressesUpdateSerializer(),
        responses={202: CustomerAddressesUpdateSerializer()},
        tags=["Auth"]
    )
    def addresses_update(self, request, pk):
        data = request.data
        addresses = CustomerAddresses.objects.filter(id=pk, customer=request.user.id).first()
        if not addresses:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = CustomerAddressesUpdateSerializer(addresses, data=data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()

        #TODO: need to add the .exclude() to CustomerAddresses query on line 338
        if data.get("is_default") and data.get("is_default") is True:
            CustomerAddresses.objects.filter(
                customer=request.user.id
            ).exclude(id=pk).update(is_default=False)

        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        summary="Delete customer address",
        description="Delete customer address",
        responses={204: OpenApiResponse(description="Customer address successfully deleted")},
        tags=["Auth"]
    )
    def delete_address(self, request, pk):
        address = CustomerAddresses.objects.filter(id=pk, customer=request.user.id).first()
        if not address:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        address.delete()
        return Response(data={"result": "Customer address successfully deleted", "ok": True},
                        status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Create customer address",
        description="Create customer address",
        request=CustomerAddressesCreateSerializer(),
        responses={201: CustomerAddressesCreateSerializer()},
        tags=["Auth"]
    )
    def address_create(self, request):
        data = request.data
        data["customer"] = request.user.id
        serializer = CustomerAddressesCreateSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_201_CREATED)


class OTPViewSet(ViewSet):
    @extend_schema(
        summary="OTP verification",
        description="OTP verification",
        request=OTPVerifySerializer(),
        responses={200: OpenApiResponse(description="User verified")},
        tags=["OTP"]
    )
    def otp_verify(self, request):
        data = request.data
        serializer = OTPVerifySerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        otp = OTP.objects.filter(otp_key=data.get("otp_key"), resend=False).first()
        if not otp:
            raise CustomApiException(error_code=ErrorCodes.OTP_KEY_NOT_FOUND)

        otp.count_attempts += 1
        otp.save(update_fields=["count_attempts"])
        if otp.otp_code != data.get("otp_code"):
            raise CustomApiException(error_code=ErrorCodes.INCORRECT_OTP)

        if otp.expire_at < datetime.now() - timedelta(minutes=1):
            raise CustomApiException(error_code=ErrorCodes.OTP_EXPIRED)

        if otp.count_attempts > 2:
            raise CustomApiException(error_code=ErrorCodes.OTP_ATTEMPTS_LIMITE)

        otp_check = OTP.objects.filter(otp_key=data.get("otp_key")).first()
        if not otp_check:
            raise CustomApiException(error_code=ErrorCodes.INVALID_TOKEN)

        if not otp_check.customer:
            raise CustomApiException(ErrorCodes.USER_DOES_NOT_EXIST)

        otp_check.customer.verified = True
        otp_check.customer.save(update_fields=["verified"])

        all_otp = OTP.objects.filter(customer_id=otp_check.customer.id)
        all_otp.delete()

        access_token, refresh = issue_customer_tokens(otp_check.customer)

        # send_notification_to_customer(otp_check.customer.id)
        return Response(data={"result": {"access_token": access_token, "refresh_token": refresh}, "ok": True},
                        status=status.HTTP_200_OK)

    @extend_schema(
        summary="OTP resend",
        description="OTP resend",
        request=OTPResendSerializer(),
        responses={200: OTPVerifySerializer()},
        tags=["OTP"]
    )
    def otp_resend(self, request):
        otp_key = request.data.get("otp_key")
        if not otp_key:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT)

        otp_check = OTP.objects.filter(otp_key=otp_key).first()
        if not otp_check:
            raise CustomApiException(error_code=ErrorCodes.INVALID_TOKEN)

        if not otp_check.customer:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

        check_otp_limit(otp_check.customer)

        last_otp = otp_check.customer.otp_set.order_by("-created_at").first()
        if last_otp.otp_key != otp_key:
            raise CustomApiException(error_code=ErrorCodes.OTP_KEY_NOT_FOUND)

        if last_otp.created_at + timedelta(minutes=1) > datetime.now():
            raise CustomApiException(error_code=ErrorCodes.OTP_NOT_EXPIRED, time=(
                    (last_otp.created_at + timedelta(minutes=1)) - datetime.now()).total_seconds())

        otp = create_otp(otp_check.customer, resend=last_otp.resend, check_limit=False)

        # message = (
        #     f' Project: Dommaster \nuser: {otp_check.customer.id} \nphone_number: {otp_check.customer.phone_number}\ncode: {otp.otp_code} '
        #     f'\notp_key: {otp.otp_key} '
        #     f'\nReset: {otp.resend}'
        #     f'\nexpires: {otp.expire_at}')
        # send_notification(message)
        EskizOTP.send_otp_service(otp_check.customer.phone_number, f"Код подтверждения для регистрации в приложение Buildex Go: {otp.otp_code}")

        return Response(data={"result": {"otp_key": otp.otp_key}, "ok": True}, status=status.HTTP_200_OK)


    @extend_schema(
        summary="OTP via Telegram (\"kod kelmadi\")",
        description=(
            "Fallback when SMS did not arrive. Pass the latest otp_key; a NEW otp_key is returned — verify with it "
            "via otp/verify/.\n\n"
            "- `linked=true`: code already sent to the linked Telegram chat.\n"
            "- `linked=false`: open `deep_link` (or build `https://t.me/<bot>?start=<link_token>`), valid `expires_in` seconds. The customer opens the bot, presses "
            "Start and shares their phone contact; then the code arrives in the bot.\n\n"
            "Telegram codes do not count toward the SMS limit (own limit: 1/min, 10 per 12h)."
        ),
        request=TelegramOTPSerializer(),
        responses={200: OpenApiResponse(description="otp_key, linked, deep_link, link_token, expires_in")},
        tags=["OTP"]
    )
    def otp_telegram(self, request):
        serializer = TelegramOTPSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        otp_check = OTP.objects.select_related("customer").filter(
            otp_key=str(serializer.validated_data["otp_key"])).first()
        if not otp_check:
            raise CustomApiException(error_code=ErrorCodes.OTP_KEY_NOT_FOUND)

        last_otp = otp_check.customer.otp_set.order_by("-created_at").first()
        if last_otp.otp_key != otp_check.otp_key:
            raise CustomApiException(error_code=ErrorCodes.OTP_KEY_NOT_FOUND)

        result = request_telegram_otp(otp_check)
        return Response(data={"result": result, "ok": True}, status=status.HTTP_200_OK)


class TelegramViewSet(ViewSet):
    @extend_schema(
        summary="Telegram link status",
        description="Whether the customer's phone is linked to a Telegram account (for OTP delivery)",
        responses={200: OpenApiResponse(description="linked, username, first_name, linked_at")},
        tags=["Telegram"]
    )
    def link_status(self, request):
        link = TelegramLink.objects.filter(phone_number=request.user.phone_number).first()
        result = {
            "linked": bool(link),
            "username": link.username if link else None,
            "first_name": link.first_name if link else None,
            "linked_at": link.updated_at if link else None,
        }
        return Response(data={"result": result, "ok": True}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Telegram unlink",
        description="Remove the Telegram binding of the customer's phone",
        responses={200: OpenApiResponse(description="Unlinked")},
        tags=["Telegram"]
    )
    def unlink(self, request):
        if not unlink_telegram(request.user.phone_number):
            raise CustomApiException(error_code=ErrorCodes.TELEGRAM_LINK_NOT_FOUND)
        return Response(data={"result": "Telegram unlinked", "ok": True}, status=status.HTTP_200_OK)

    @extend_schema(exclude=True)
    def webhook(self, request):
        """Telegram Bot API webhook; authenticated by X-Telegram-Bot-Api-Secret-Token."""
        secret = settings.TELEGRAM_OTP_WEBHOOK_SECRET
        if not secret or request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            handle_telegram_update(request.data)
        except Exception:
            # always 200: otherwise Telegram keeps re-delivering the same update
            logger.exception("Telegram OTP webhook update failed")
        return Response(data={"ok": True}, status=status.HTTP_200_OK)


class FCMTokenViewSet(ViewSet):
    @extend_schema(
        summary="FCMToken",
        description="FCMToken",
        request=FCMTokenRequestSerializer(),
        responses={200: FCMTokenSerializer()},
        tags=["FcmToken"]
    )
    def fcm_token(self, request):
        data = request.data
        serializer = FCMTokenRequestSerializer(data=data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        fcm_token = FcmToken.objects.filter(device_id=serializer.validated_data.get("device_id"),
                                            customer_id=request.user.id).first()
        if not fcm_token:
            fcm_token = FcmToken.objects.create(device_id=serializer.validated_data.get("device_id"),
                                                customer_id=request.user.id,
                                                fcm_token=serializer.validated_data.get("fcm_token"))
            create_serializer = FCMTokenSerializer(fcm_token, context={"request": request})
            return Response(data={"result": create_serializer.data, 'ok': True}, status=status.HTTP_200_OK)

        update_serializer = FCMTokenSerializer(fcm_token, data=data, partial=True, context={"request": request})
        if not update_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=update_serializer.errors)

        update_serializer.save()
        return Response(data={"result": update_serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)
    
    @extend_schema(
        summary="FCMToken delete",
        description="FCMToken delete",
        request=FCMTokenDeleteSerializer(),
        responses={204: OpenApiResponse(description="FCMToken successfully deleted")},
        tags=["FcmToken"]
    )
    def fcmtoken_delete(self, request):
        serializer = FCMTokenDeleteSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        fcm_token = FcmToken.objects.filter(device_id=serializer.validated_data.get("device_id"),
                                            customer_id=request.user.id).first()
        if not fcm_token:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="FCMToken not found")

        fcm_token.delete()
        return Response(data={"result": "FCMToken successfully deleted", "ok": True}, status=status.HTTP_204_NO_CONTENT)
