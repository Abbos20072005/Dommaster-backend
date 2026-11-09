"""WebSocket of the assistant: `ws/assistant/?token=<access JWT>&device_id=<id>&lang=uz|ru`.

client -> {"type": "message", "message", "conversation_id"?, "platform"?}
server -> {"type": "start", "conversation_id", "message_id"}, {"type": "tool", "name"}*, {"type": "delta", "text"}*,
          {"type": "done", "conversation_id", "message_id", "text", "products"} or
          {"type": "error", "error_code", "detail"}

One message at a time per socket: a message sent before the answer is done gets an error. The answer runs in a
worker thread (sync ORM + the SDK's sync stream) that is not the shared "thread sensitive" one, so sockets do not
wait for each other.
"""
import asyncio
import json
import logging
from urllib.parse import parse_qs

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.core.serializers.json import DjangoJSONEncoder
from django.http.cookie import parse_cookie
from django.utils import translation

from apps.authorization.custom_jwt import CustomJwtAuthentication
from apps.service import feed
from apps.service.api.v1.client.assistant_serializers import AssistantChatSerializer
from exceptions.error_messages import ErrorCodes, error_messages
from . import service
from .gemini import AssistantError

logger = logging.getLogger(__name__)

CLOSE_BAD_TOKEN = 4001
# False: every answer gets a worker thread of its own (True would queue all sockets in one shared thread);
# tests set True, so the answer sees the rows of the test transaction
THREAD_SENSITIVE = False


def customer_of_token(raw):
    """The customer of an access token; None for a bad / expired / revoked token or a deleted / blocked one."""
    auth = CustomJwtAuthentication()
    try:
        return auth.get_user(auth.get_validated_token(raw))
    except Exception:  # InvalidToken, CustomApiException of get_user
        return None


def language_of(query_language, accept_language):
    """The `lang` parameter, else the handshake's Accept-Language (uz-UZ -> uz), else ru."""
    for value in (query_language, (accept_language or "").split(",")[0]):
        value = (value or "").strip().lower()
        if value.startswith("uz"):
            return "uz"
        if value.startswith("ru"):
            return "ru"
    return "ru"


class ScopeRequest:
    """What `feed.Viewer.of` and the product serializers read of a request, made from the WebSocket scope."""

    def __init__(self, scope, customer, device_id):
        headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers", [])}
        self.user = customer or AnonymousUser()
        self.COOKIES = parse_cookie(headers.get("cookie", ""))
        self.META = {"HTTP_" + key.upper().replace("-", "_"): value for key, value in headers.items()}
        if device_id:
            self.META["HTTP_X_DEVICE_ID"] = device_id
        client = scope.get("client") or ("", 0)
        self.META["REMOTE_ADDR"] = client[0] or ""
        self.host = headers.get("x-forwarded-host") or headers.get("host", "")
        forwarded_proto = headers.get("x-forwarded-proto", "")
        self.scheme = forwarded_proto or ("https" if scope.get("scheme") == "wss" else "http")

    def build_absolute_uri(self, location):
        return f"{self.scheme}://{self.host}{location}"


def error_event(code, detail=None):
    return {"type": "error", "error_code": code.value, "detail": detail or error_messages[code.value]["result"]}


class AssistantConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        params = parse_qs(self.scope.get("query_string", b"").decode())
        token = (params.get("token") or [""])[0]
        self.customer = await database_sync_to_async(customer_of_token)(token) if token else None
        headers = dict(self.scope.get("headers", []))
        self.language = language_of((params.get("lang") or [""])[0],
                                    headers.get(b"accept-language", b"").decode("latin1"))
        self.device_id = (params.get("device_id") or [""])[0].strip()[:300]
        self.task = None
        await self.accept()
        if token and self.customer is None:
            await self.close(code=CLOSE_BAD_TOKEN)

    async def disconnect(self, code):
        # a running answer is not stopped: it finishes in its thread and is saved; sending to it fails quietly
        pass

    @classmethod
    async def encode_json(cls, content):
        return json.dumps(content, cls=DjangoJSONEncoder, ensure_ascii=False)

    async def send_event(self, event):
        try:
            await self.send_json(event)
        except Exception:  # the socket is closed
            logger.debug("assistant socket closed before %s", event.get("type"))

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict) or content.get("type") != "message":
            await self.send_event(error_event(ErrorCodes.VALIDATION_FAILED, "type must be \"message\""))
            return
        if self.task is not None and not self.task.done():
            await self.send_event(error_event(ErrorCodes.VALIDATION_FAILED, "the previous answer is not done"))
            return
        serializer = AssistantChatSerializer(data=content)
        if not serializer.is_valid():
            await self.send_event(error_event(ErrorCodes.VALIDATION_FAILED, serializer.errors))
            return
        self.task = asyncio.ensure_future(self.answer(serializer.validated_data))

    async def answer(self, data):
        try:
            await database_sync_to_async(self.answer_sync, thread_sensitive=THREAD_SENSITIVE)(data)
        except Exception:
            logger.exception("assistant socket answer failed")
            await self.send_event(error_event(ErrorCodes.ASSISTANT_UNAVAILABLE))

    def answer_sync(self, data):
        """Runs in a worker thread; sends through the consumer's event loop."""
        send = async_to_sync(self.send_event)
        request = ScopeRequest(self.scope, self.customer, self.device_id)
        with translation.override(self.language):
            try:
                conversation, answer = service.begin(
                    feed.Viewer.of(request), service.client_ip(request.META), data["message"],
                    data.get("conversation_id"), self.language, data.get("platform"))
            except service.AssistantDisabled:
                send(error_event(ErrorCodes.ASSISTANT_DISABLED))
                return
            except service.LimitExceeded:
                send(error_event(ErrorCodes.ASSISTANT_LIMIT_EXCEEDED))
                return
            send({"type": "start", "conversation_id": conversation.pk, "message_id": answer.pk})
            try:
                result = service.reply(conversation, answer, data["message"], self.language, request,
                                       on_event=lambda kind, event: send({"type": kind, **event}))
            except AssistantError:
                send(error_event(ErrorCodes.ASSISTANT_UNAVAILABLE))
                return
            send({"type": "done", **result})
