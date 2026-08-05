import json
import logging
import re
import uuid
from datetime import datetime
from threading import local

logger = logging.getLogger(__name__)

_request_local = local()

SENSITIVE_KEYS = (
    "password",
    "passwd",
    "token",
    "secret",
    "key",
    "api_key",
    "access_token",
    "refresh_token",
    "authorization",
    "auth",
    "card_number",
    "card",
    "cvv",
    "otp",
    "otp_code",
    "fcm_token",
    "sign_string",
)

_MASK_PATTERN = re.compile(
    rf"(?i)([\s,{{\"'=](?:{'|'.join(SENSITIVE_KEYS)})[\"']?\s*[:=]\s*[\"']?)[^\"',\s}}]+"
)

_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-_.]+")

_MASK = "***"


def generate_request_id() -> str:
    return uuid.uuid4().hex[:16]


def set_request_context(request_id="-", user_id="-") -> None:
    _request_local.request_id = request_id
    _request_local.user_id = user_id


def clear_request_context() -> None:
    for attr in ("request_id", "user_id"):
        if hasattr(_request_local, attr):
            delattr(_request_local, attr)


def get_request_context() -> dict:
    return {
        "request_id": getattr(_request_local, "request_id", "-"),
        "user_id": getattr(_request_local, "user_id", "-"),
    }


class SensitiveDataFilter(logging.Filter):
    """Mask passwords, tokens and other secrets in log messages."""

    def filter(self, record):
        message = record.getMessage()
        message = _BEARER_PATTERN.sub(_MASK, message)
        message = _MASK_PATTERN.sub(rf"\g<1>{_MASK}", message)
        record.msg = message
        record.args = ()
        return True


class RequestContextFilter(logging.Filter):
    """Attach current request_id and user_id to every log record."""

    def filter(self, record):
        context = get_request_context()
        record.request_id = context["request_id"]
        record.user_id = context["user_id"]
        return True


class JsonFormatter(logging.Formatter):
    """Structured JSON output, ready for external log aggregators."""

    _CONTEXT_FIELDS = ("method", "path", "status", "duration_ms")

    def format(self, record):
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
        }
        for field in self._CONTEXT_FIELDS:
            value = getattr(record, field, "-")
            if value != "-":
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class VerboseFormatter(logging.Formatter):
    """Human readable output for local development."""

    def format(self, record):
        for field in ("request_id", "user_id", "method", "path", "status", "duration_ms"):
            record.__dict__.setdefault(field, "-")
        return super().format(record)
