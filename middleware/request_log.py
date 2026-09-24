import logging
import time

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from utils.get_user_token import decode_jwt_token
from utils.logger import clear_request_context, generate_request_id, set_request_context

logger = logging.getLogger(__name__)


class RequestLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = request.headers.get("X-Request-ID") or generate_request_id()
        request._start_time = time.time()
        set_request_context(
            request_id=request.request_id,
            user_id=self._get_user_id(request),
        )

    def process_response(self, request, response):
        duration_ms = round((time.time() - request._start_time) * 1000, 2)
        if getattr(settings, "LOG_REQUEST", 1):
            logger.info(
                "%s %s -> %s (%sms)",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
        clear_request_context()
        return response

    def process_exception(self, request, exception):
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.path,
            exception,
            exc_info=True,
        )
        clear_request_context()
        return None

    @staticmethod
    def _get_user_id(request):
        auth = request.headers.get("Authorization")
        if not auth or len(auth.split()) < 2:
            return "-"
        payload = decode_jwt_token(auth.split()[1])
        if payload:
            return payload.get("user_id", "-")
        return "-"
