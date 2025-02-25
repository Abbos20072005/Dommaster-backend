from rest_framework.viewsets import ViewSet
from django.db.models import Q
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .models import Customer
from .serializers import CustomerSerializer, LoginSerializer, RegisterSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from datetime import datetime
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken


class AuthViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Customer login",
        operation_description="Customer login",
        request_body=LoginSerializer(),
        responses={200: LoginSerializer()},
        tags=["Auth"]
    )
    def login(self, request):
        login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
        access_token['login_time'] = login_time
        customer.login_time = login_time
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
        customer = Customer.objects.filter(
            Q(email=request.data.get("email")) | Q(phone_number=request.data.get('phone_number'))).first()
        if customer:
            raise CustomApiException(error_code=ErrorCodes.ALREADY_EXISTS)

        serializer = RegisterSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED)

        serializer.save()
        return Response(data={'result': serializer.data, 'ok': True}, status=status.HTTP_201_CREATED)

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
        operation_summary="",
        operation_description="",
        request_body="",
        responses={200:}
    )
    def something(self, request):
        pass
