from rest_framework.viewsets import ViewSet
from django.db.models import Q
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from utils.send_notification import send_notification
from .models import Customer, OTP, FcmToken
from .serializers import CustomerSerializer, LoginSerializer, RegisterSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from datetime import datetime, timedelta
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import otp_code_generator


# TODO: Resend otp
# TODO: Reset password
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
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED)

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
                f' Project: Haq \nuser: {customer_save.id} \nphone_number: {customer_save.phone_number}\ncode: {otp.otp_code} '
                f'\notp_key: {otp.otp_key} '
                f'\nReset: {otp.resend}'
                f'\nexpires: {otp.expire_at}')
            send_notification(message)
            fcm_token = FcmToken.objects.create(cusomer=customer_save, fcm_token=request.data.get("device_id", ""))
            fcm_token.save()
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
            f' Project: Haq \nuser: {customer_none.id} \nphone_number: {customer_none.phone_number}\ncode: {otp.otp_code} '
            f'\notp_key: {otp.otp_key} '
            f'\nReset: {otp.resend}'
            f'\nexpires: {otp.expire_at}')
        send_notification(message)
        fcm_token = FcmToken.objects.create(cusomer=customer_none, fcm_token=request.data.get("device_id", ""))
        fcm_token.save()
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

    # @swagger_auto_schema(
    #     operation_summary="",
    #     operation_description="",
    #     request_body="",
    #     responses={200:}
    # )
    # def something(self, request):
    #     pass
