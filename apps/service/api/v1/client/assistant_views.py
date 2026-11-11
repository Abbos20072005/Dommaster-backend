from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.service import feed
from apps.service.assistant import service
from apps.service.assistant.gemini import AssistantError
from apps.service.attributes import request_language
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .assistant_serializers import AssistantChatSerializer, AssistantConversationSerializer, AssistantReplySerializer

TAGS = ["Assistant"]
ERRORS_NOTE = (
    " Errors: 41 switched off or the month's / day's budget is spent (503, show the operator contacts),"
    " 42 daily limit used up (429), 43 Gemini did not answer (503), 44 too many messages in a minute (429)."
    " Phone / card numbers in `message` are masked before saving: `result.question.text` is the saved text,"
    " `question.pii_masked` = something was masked (show the \"don't write card numbers\" notice)."
    " A guest is told apart by the `X-Device-Id` header (else the `cart_token` cookie, else the IP)."
)


class AssistantViewSet(ViewSet):
    """AI shopping assistant (Gemini): product search and advice. The WebSocket `ws/assistant/` streams
    the same answers."""

    @extend_schema(
        summary="Ask the assistant",
        description=(
            "One message to the AI assistant -> its answer and the recommended products (`ProductSerializer`"
            " cards, live price). Send `conversation_id` of the previous answer to continue the conversation."
            + ERRORS_NOTE
        ),
        request=AssistantChatSerializer,
        responses={200: AssistantReplySerializer},
        tags=TAGS,
    )
    def chat(self, request):
        serializer = AssistantChatSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
        data = serializer.validated_data
        language = request_language(request)
        try:
            conversation, question, answer = service.begin(
                feed.Viewer.of(request), service.client_ip(request.META), data["message"],
                data.get("conversation_id"), language, data.get("platform"))
            result = service.reply(conversation, question, answer, language, request)
        except service.AssistantDisabled:
            raise CustomApiException(error_code=ErrorCodes.ASSISTANT_DISABLED)
        except service.TooFrequent:
            raise CustomApiException(error_code=ErrorCodes.ASSISTANT_TOO_FREQUENT)
        except service.LimitExceeded:
            raise CustomApiException(error_code=ErrorCodes.ASSISTANT_LIMIT_EXCEEDED)
        except AssistantError:
            raise CustomApiException(error_code=ErrorCodes.ASSISTANT_UNAVAILABLE)
        return Response(data={"result": result, "ok": True}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Assistant conversation",
        description="The answered messages of the caller's conversation, oldest first, with their product cards."
                    " Another customer's / device's conversation -> 404.",
        responses={200: AssistantConversationSerializer},
        tags=TAGS,
    )
    def conversation(self, request, pk):
        viewer = feed.Viewer.of(request)
        conversation = service.owned_conversation(
            pk, viewer, service.identity(viewer, service.client_ip(request.META)))
        if conversation is None:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)
        return Response(data={"result": service.conversation_messages(conversation, request), "ok": True},
                        status=status.HTTP_200_OK)
