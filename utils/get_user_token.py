from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from authorization.models import Customer


def decode_jwt_token(token):
    try:
        # Verify and decode the token
        payload = UntypedToken(token)
        return payload
    except TokenError as e:
        return
    except InvalidToken as e:
        return


def validate_token(request):
    token = request.headers.get('Authorization')
    if token is None:
        return
    if len(token.split()) < 2 or token.split()[0] != 'Bearer':
        return
    payload = decode_jwt_token(token.split()[1])
    if payload is None:
        return
    customer_id = payload.get('user_id')
    # login_time = payload.get('login_time')
    if customer_id is None:
        return
    if Customer.objects.filter(id=customer_id).exists():
        return payload
    return