from apps.authorization.models import Customer, CustomerAddresses, FcmToken
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.authorization.utils import validate_number, normalize_uz_phone
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


class TelegramOTPSerializer(serializers.Serializer):
    otp_key = serializers.UUIDField(help_text="otp_key of the latest OTP (from auth/phone/, otp/resend/ ...)")


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
    password = serializers.CharField(max_length=30, required=True)


class PhoneAuthSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, help_text="998XXXXXXXXX (12 digits)")
    device_id = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate_phone_number(self, value):
        try:
            return normalize_uz_phone(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "email", "phone_number", "password", "role")
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": False, "allow_blank": True, "allow_null": True},
            "role": {"required": False},
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
            "email",
            "role",
            "avatar",
        )
        # avatar is changed only via customer/avatar/ (validated upload)
        read_only_fields = ("avatar",)


AVATAR_MAX_SIZE_MB = 5
AVATAR_ALLOWED_FORMATS = {"JPEG": "jpg/jpeg", "PNG": "png", "WEBP": "webp"}


class CustomerAvatarSerializer(serializers.Serializer):
    avatar = serializers.ImageField(
        help_text=f"Image file ({', '.join(AVATAR_ALLOWED_FORMATS.values())}), max {AVATAR_MAX_SIZE_MB} MB"
    )

    def validate_avatar(self, value):
        if value.size > AVATAR_MAX_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(f"Image size must not exceed {AVATAR_MAX_SIZE_MB} MB.")
        # real content format (checked by Pillow), not the file extension
        image_format = getattr(getattr(value, "image", None), "format", None)
        if image_format not in AVATAR_ALLOWED_FORMATS:
            raise serializers.ValidationError(
                f"Unsupported image format. Allowed: {', '.join(AVATAR_ALLOWED_FORMATS.values())}."
            )
        return value

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

class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)


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