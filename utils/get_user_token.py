from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken


def decode_jwt_token(token):
    """
    Given a JWT token, decode it and return the payload.

    :param token: JWT token as a string
    :return: payload of the token
    """
    try:
        # Verify and decode the token
        payload = UntypedToken(token)
        return payload
    except TokenError as e:
        return
    except InvalidToken as e:
        return