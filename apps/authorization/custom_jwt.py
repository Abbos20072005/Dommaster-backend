from django.contrib.auth import get_user_model
from django.utils import translation
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication, AuthUser
from rest_framework_simplejwt.exceptions import InvalidToken
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .models import Customer
from .visits import record_visit


class CustomJwtAuthentication(JWTAuthentication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer_model = Customer

    def authenticate(self, request):
        result = super().authenticate(request)
        if result and isinstance(result[0], Customer):
            # the dashboard active users chart + the customer's language (only when the client sent one)
            language = translation.get_language() if request.headers.get('Accept-Language') else None
            record_visit(result[0], language)
        return result

    def get_user(self, validated_token):
        user_id = validated_token.get('user_id')

        if user_id:
            customer = Customer.objects.filter(id=user_id).first()
            if customer and customer.is_deleted:
                raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)
            if customer and customer.token_revoked(validated_token.get('iat')):  # logout-all by staff
                raise CustomApiException(error_code=ErrorCodes.INVALID_TOKEN)
            if customer and customer.is_blocked:
                raise CustomApiException(error_code=ErrorCodes.USER_BLOCKED)
            return customer
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
