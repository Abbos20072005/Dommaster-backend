"""Which language modeltranslation reads and writes for a request.

`LocaleMiddleware` activates the language of `Accept-Language` for every request. That is what the client
API wants, but nothing else: a translated field read or written through its plain name (`name`, not
`name_ru`) uses the column of the ACTIVE language, so an admin panel request with `Accept-Language: uz`
would write the name into `name_uz` and leave `name_ru` as it was. The admin API, the 1C integration,
django admin, the payment callbacks and the schema pages therefore keep the default language.
"""
from django.conf import settings
from django.utils import translation

CLIENT_PREFIX = "/api/v1/"
# under the client prefix, but not the client API
STAFF_PREFIXES = ("/api/v1/admin/", "/api/v1/integration/")


def follows_accept_language(path):
    return path.startswith(CLIENT_PREFIX) and not path.startswith(STAFF_PREFIXES)


class RequestLanguageMiddleware:
    """Keeps the default language active outside the client API. Must come after `LocaleMiddleware`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not follows_accept_language(request.path):
            translation.activate(settings.MODELTRANSLATION_DEFAULT_LANGUAGE)
        return self.get_response(request)
