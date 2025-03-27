from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .serializers import BannerSerializer, ChatSerializer, ChatMessageCreateSerializer
from .models import Banner, Chat


class BannerViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Banner",
        operation_description="Banner",
        responses={200: BannerSerializer(many=True)},
        tags=["Base"]
    )
    def banner_list(self, request):
        banner = Banner.objects.filter(is_visible=True)
        serializer = BannerSerializer(banner, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class ChatViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Chat messages list",
        operation_description="Chat messages list",
        responses={200: ChatSerializer(many=True)},
        tags=["Chat"]
    )
    def message_list(self, request):
        chat = Chat.objects.filter(user_id=request.user.id)
        serializer = ChatSerializer(chat, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Chat message create",
        operation_description="Chat message create",
        request_body=ChatMessageCreateSerializer(),
        responses={201: ChatSerializer()},
        tags=["Chat"]
    )
    def message_create(self, request):
        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)
