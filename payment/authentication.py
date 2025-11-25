import base64
from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings


class UzumBankBasicAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            raise exceptions.AuthenticationFailed('Authorization header is missing')

        try:
            auth_type, credentials = auth_header.split(' ')

            if auth_type.lower() != 'basic':
                raise exceptions.AuthenticationFailed('Invalid authorization type')

            decoded = base64.b64decode(credentials).decode('utf-8')
            username, password = decoded.split(':', 1)

            if (username == settings.SERVICE_UZUM_KEY and
                    password == settings.SERVICE_UZUM_PASSWORD):
                return (None, None)
            else:
                raise exceptions.AuthenticationFailed('Incorrect credentials')

        except (ValueError, UnicodeDecodeError):
            raise exceptions.AuthenticationFailed('Invalid authorization format')
        except Exception:
            raise exceptions.AuthenticationFailed('Authorization error')

    def authenticate_header(self, request):
        return 'Basic realm="Uzum Bank API"'