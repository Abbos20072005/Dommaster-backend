from rest_framework.viewsets import ViewSet
from django.db.models import Q
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from utils.send_notification import send_notification
from .models import Customer, OTP, FcmToken
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from datetime import datetime, timedelta
from django.contrib.auth.hashers import check_password, make_password
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import otp_code_generator, generate_random_password
from .serializers import CustomerSerializer, LoginSerializer, RegisterSerializer, OTPVerifySerializer, \
    OTPResendSerializer, ChangePasswordSerializer, ForgotPasswordSerializer


class AuthViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Customer login",
        operation_description="Customer login",
        request_body=LoginSerializer(),
        responses={200: LoginSerializer()},
        tags=["Auth"]
    )
    def login(self, request):
        login_serializer = LoginSerializer(data=request.data, context={'request': request})
        if not login_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=login_serializer.errors)

        customer = Customer.objects.filter(Q(email=login_serializer.validated_data.get('email')) | Q(
            phone_number=login_serializer.validated_data.get("phone_number"))).first()

        if not customer:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

        if check_password(login_serializer.validated_data.get('password'), customer.password) is False:
            raise CustomApiException(error_code=ErrorCodes.INCORRECT_PASSWORD)

        refresh = RefreshToken.for_user(customer)
        access_token = refresh.access_token
        customer.save()

        return Response(data={'access_token': str(access_token), 'refresh_token': str(refresh), 'ok': True},
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Customer Register",
        operation_description="Customer Register",
        request_body=RegisterSerializer(),
        responses={201: RegisterSerializer()},
        tags=["Auth"]
    )
    def register(self, request):
        serializer = RegisterSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        customer = Customer.objects.filter(
            Q(email=request.data.get("email")) | Q(phone_number=request.data.get('phone_number')),
            verified=True).first()
        if customer:
            raise CustomApiException(error_code=ErrorCodes.ALREADY_EXISTS)

        customer_none = Customer.objects.filter(
            Q(email=request.data.get("email")) | Q(phone_number=request.data.get('phone_number')),
            verified=False).first()

        if customer_none is None:
            customer_save = serializer.save()
            if customer_save.id is None:
                raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

            otp_code = otp_code_generator()
            otp = OTP.objects.create(customer_id=customer_save.id, otp_code=otp_code, resend=False)
            otp.expire_at = otp.created_at + timedelta(minutes=1)
            otp.save()
            message = (
                f' Project: Dommaster \nuser: {customer_save.id} \nphone_number: {customer_save.phone_number}\ncode: {otp.otp_code} '
                f'\notp_key: {otp.otp_key} '
                f'\nReset: {otp.resend}'
                f'\nexpires: {otp.expire_at}')
            send_notification(message)
            # fcm_token = FcmToken.objects.create(cusomer=customer_save, fcm_token=request.data.get("device_id", ""))
            # fcm_token.save()
            return Response(data={"result": {"otp_key": otp.otp_key}, "ok": True}, status=status.HTTP_201_CREATED)

        serializer_customer = CustomerSerializer(customer_none, data=serializer.validated_data, partial=True,
                                                 context={"request": request})
        if not serializer_customer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer_customer.errors)

        serializer_customer.save()
        all_otp = OTP.objects.filter(customer_id=customer_none.id)
        last_otp = all_otp.order_by("-created_at").first()
        if len(all_otp) >= 3 and last_otp.created_at > datetime.now() - timedelta(hours=12):
            raise CustomApiException(error_code=ErrorCodes.ATTEMPT_ALREADY_EXISTS,
                                     time=last_otp.created_at + timedelta(hours=12))

        if customer_none.id is None:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

        otp_code = otp_code_generator()
        otp = OTP.objects.create(customer_id=customer_none.id, otp_code=otp_code, resend=False)
        otp.expire_at = otp.created_at + timedelta(minutes=1)
        otp.save()

        latest_otp = all_otp.order_by("-created_at").exclude(otp_key=otp.otp_key).first()
        if latest_otp and latest_otp.created_at < datetime.now() - timedelta(hours=12) and len(all_otp) >= 2:
            all_otp.exclude(otp_key=otp.otp_key).delete()

        message = (
            f' Project: Dommaster \nuser: {customer_none.id} \nphone_number: {customer_none.phone_number}\ncode: {otp.otp_code} '
            f'\notp_key: {otp.otp_key} '
            f'\nReset: {otp.resend}'
            f'\nexpires: {otp.expire_at}')
        send_notification(message)
        # fcm_token = FcmToken.objects.create(cusomer=customer_none, fcm_token=request.data.get("device_id", ""))
        # fcm_token.save()
        return Response(data={'result': {"otp_key": otp.otp_key}, 'ok': True}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Auth me",
        operation_description="Auth me",
        responses={200: CustomerSerializer()},
        tags=["Auth"]
    )
    def auth_me(self, request):
        customer = Customer.objects.filter(id=request.user.id).first()
        serializer = CustomerSerializer(customer, context={'request': request})
        return Response(data={'result': serializer.data, 'ok': True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Change password",
        operation_description="Change password",
        request_body=ChangePasswordSerializer(),
        responses={202: "Password successfully changed"},
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

    @swagger_auto_schema(
        operation_summary="Forgot password",
        operation_description="Forgot password",
        request_body=ForgotPasswordSerializer(),
        responses={202: "Password successfully changed"},
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

        random_password = generate_random_password()
        customer.password = make_password(random_password)

        customer.save(update_fields=["password"])

        message = (
            f' Project: Dommaster \nuser: {customer.id} \nphone_number: {customer.phone_number} '
            f'\nmessage: Your new password is {random_password} '
        )

        send_notification(message)
        return Response(data={"result": "Password successfully changed", "ok": True}, status=status.HTTP_202_ACCEPTED)


class OTPViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="OTP verification",
        operation_description="OTP verification",
        request_body=OTPVerifySerializer(),
        responses={200: "User verified"},
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

        refresh = RefreshToken.for_user(otp_check.customer)
        access_token = str(refresh.access_token)
        return Response(data={"result": {"access_token": access_token, "refresh_token": str(refresh)}, "ok": True},
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="OTP resend",
        operation_description="OTP resend",
        request_body=OTPResendSerializer(),
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

        all_otp = otp_check.customer.otp_set.all()

        last_otp = all_otp.order_by("-created_at").first()
        if len(all_otp) >= 3 and last_otp.created_at > datetime.now() - timedelta(hours=12):
            raise CustomApiException(error_code=ErrorCodes.ATTEMPT_ALREADY_EXISTS,
                                     time=last_otp.created_at + timedelta(hours=12))

        if last_otp.otp_key != otp_key:
            raise CustomApiException(error_code=ErrorCodes.OTP_KEY_NOT_FOUND)

        first_otp = OTP.objects.filter(customer_id=all_otp.first().customer.id).order_by("-created_at").first()
        if first_otp and first_otp.created_at + timedelta(minutes=1) > datetime.now():
            raise CustomApiException(error_code=ErrorCodes.OTP_NOT_EXPIRED, time=(
                    (first_otp.created_at + timedelta(minutes=1)) - datetime.now()).total_seconds())

        old_otp = all_otp.filter(otp_key=otp_key).first()
        if otp_check.customer.id is None:
            raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

        otp_code = otp_code_generator()
        otp = OTP.objects.create(customer_id=otp_check.customer.id, otp_code=otp_code, resend=old_otp.resend)
        otp.expire_at = otp.created_at + timedelta(minutes=1)
        otp.save()

        latest_otp = all_otp.order_by("-created_at").exclude(otp_key=otp.otp_key).first()
        if latest_otp and latest_otp.created_at < datetime.now() - timedelta(hours=12) and len(all_otp) >= 2:
            all_otp.exclude(otp_key=otp.otp_key).delete()

        message = (
            f' Project: Dommaster \nuser: {otp_check.customer.id} \nphone_number: {otp_check.customer.phone_number}\ncode: {otp.otp_code} '
            f'\notp_key: {otp.otp_key} '
            f'\nReset: {otp.resend}'
            f'\nexpires: {otp.expire_at}')
        send_notification(message)

        return Response(data={"result": {"otp_key": otp.otp_key}, "ok": True}, status=status.HTTP_200_OK)
