import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")

    if response is None:
        logger.error(
            "Unhandled exception on %s %s: %s",
            getattr(request, "method", "-"),
            getattr(request, "path", "-"),
            exc,
            exc_info=True,
        )
        return None

    if response.status_code >= 500:
        logger.error(
            "Server error on %s %s: %s",
            getattr(request, "method", "-"),
            getattr(request, "path", "-"),
            exc,
            exc_info=True,
        )

    return response
