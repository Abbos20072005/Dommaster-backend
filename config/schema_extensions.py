"""drf-spectacular auth extensions (registered on import — imported from config/urls/swagger.py)."""
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class CustomerJwtScheme(OpenApiAuthenticationExtension):
    target_class = "apps.authorization.custom_jwt.CustomJwtAuthentication"
    name = "customerJwt"

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object("Authorization", "Bearer", "JWT")


class AdminJwtScheme(OpenApiAuthenticationExtension):
    target_class = "apps.authorization.custom_jwt.AdminJwtAuthentication"
    name = "adminJwt"

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object("Authorization", "Bearer", "JWT")


class UzumBankBasicScheme(OpenApiAuthenticationExtension):
    target_class = "apps.payment.authentication.UzumBankBasicAuthentication"
    name = "uzumBasic"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "basic"}
