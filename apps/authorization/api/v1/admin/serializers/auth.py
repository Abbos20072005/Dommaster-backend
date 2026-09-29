from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken


def generate_admin_tokens(admin):
    # `admin_id` instead of `user_id` so admin tokens never authenticate as a Customer (and vice versa)
    refresh = RefreshToken()
    refresh['admin_id'] = admin.id
    refresh['role'] = 'admin'
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "first_name", "last_name", "email", "is_superuser", "last_login")


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, write_only=True)
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, attrs):
        admin = authenticate(self.context.get("request"), username=attrs["username"], password=attrs["password"])
        if admin is None:
            raise AuthenticationFailed("Incorrect username or password")
        if not admin.is_staff:
            raise PermissionDenied()

        update_last_login(None, admin)
        return {**generate_admin_tokens(admin), "admin": AdminSerializer(admin).data}


class AdminTokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs["refresh"])
        except TokenError as e:
            raise InvalidToken(e.args[0])

        admin_id = refresh.payload.get("admin_id")
        admin = get_user_model().objects.filter(id=admin_id, is_active=True, is_staff=True).first() if admin_id else None
        if not admin:
            raise InvalidToken("Token contained no recognizable admin identification")

        return generate_admin_tokens(admin)
