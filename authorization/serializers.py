from .models import Customer, CustomerAddresses, FcmToken
from rest_framework import serializers
from .utils import validate_number
from django.contrib.auth.hashers import make_password

class FCMTokenDeleteSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=300, required=True)

class FCMTokenRequestSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=300, required=True)
    device_id = serializers.CharField(max_length=300, required=True)

class FCMTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FcmToken
        fields = (
            "id",
            "customer",
            "device_id",
            "fcm_token",
        )

class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True, validators=[validate_number])


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)


class OTPResendSerializer(serializers.Serializer):
    otp_key = serializers.UUIDField()


class OTPVerifySerializer(serializers.Serializer):
    otp_key = serializers.UUIDField()
    otp_code = serializers.IntegerField()


class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=14, required=False, validators=[validate_number])
    password = serializers.CharField(max_length=30, required=False)


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "email", "phone_number", "password")
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            "id",
            "full_name",
            "phone_number",
            "email"
        )

class CustomerAddressesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddresses
        fields = (
            "id",
            "customer",
            "name",
            "location_name",
            "latitude",
            "longitude",
            "is_default"
        )

class CustomerAddressesCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddresses
        fields = (
            "id",
            "customer",
            "name",
            "location_name",
            "latitude",
            "longitude"
        )

class CustomerAddressesUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddresses
        fields = (
            "id",
            "name",
            "location_name",
            "latitude",
            "longitude",
            "is_default"
        )