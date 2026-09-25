from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication, AuthUser
from rest_framework_simplejwt.exceptions import InvalidToken
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .models import Customer


class CustomJwtAuthentication(JWTAuthentication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer_model = Customer

    def get_user(self, validated_token):
        user_id = validated_token.get('user_id')

        if user_id:
            return Customer.objects.filter(id=user_id).first()
        raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)


class AdminJwtAuthentication(JWTAuthentication):
    """Dashboard tokens: carry `admin_id` (django auth User), never `user_id` (Customer)."""

    def get_user(self, validated_token):
        admin_id = validated_token.get('admin_id')
        if not admin_id:
            raise InvalidToken('Token contained no recognizable admin identification')

        admin = get_user_model().objects.filter(id=admin_id, is_active=True, is_staff=True).first()
        if not admin:
            raise AuthenticationFailed('Admin not found', code='user_not_found')
        return admin
