from rest_framework_simplejwt.authentication import JWTAuthentication, AuthUser
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from utils.check_user_token import get_role
from .models import Customer


class CustomJwtAuthentication(JWTAuthentication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer_model = Customer

    def get_user(self, validated_token):
        user_role = get_role(f"Bearer {validated_token}")
        user_id = validated_token['user_id']

        if user_id:
            return Customer.objects.filter(id=user_id).first()
        raise CustomApiException(error_code=ErrorCodes.USER_DOES_NOT_EXIST)

