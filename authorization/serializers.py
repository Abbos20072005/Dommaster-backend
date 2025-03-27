from .models import Customer
from rest_framework import serializers
from .utils import validate_number


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=14, required=False, validators=[validate_number])
    password = serializers.CharField(max_length=30, required=False)

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "email", "phone_number", "password")
        extra_kwargs = {
            'password': {'write_only': True}
        }

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number", "email")