from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .serializers import BannerSerializer, MessageSerializer, MessageCreateSerializer, AboutUsSerializer, \
    ChatCreateSerializer
from .models import Banner, Chat, AboutUs, Messages


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
        responses={200: MessageSerializer(many=True)},
        tags=["Chat"]
    )
    def message_list(self, request):
        chat = Chat.objects.filter(customer_id=request.user.id).first()
        if not chat:
            create_serializer = ChatCreateSerializer(data={"customer": request.user.id},
                                                     context={"request": request})
            if not create_serializer.is_valid():
                raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=create_serializer.errors)

            create_serializer.save()
            return Response(data={"result": create_serializer.data, "ok": True}, status=status.HTTP_200_OK)

        messages = Messages.objects.filter(chat=chat.id)
        serializer = MessageSerializer(messages, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Chat message create",
        operation_description="Chat message create",
        request_body=MessageCreateSerializer(),
        responses={201: MessageSerializer()},
        tags=["Chat"]
    )
    def message_create(self, request):
        chat = Chat.objects.filter(customer_id=request.user.id).first()
        if not chat:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = MessageCreateSerializer(data={"chat": chat.id, **request.data},
                                             context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class AboutUsViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="About Us",
        operation_description="About Us",
        responses={200: AboutUsSerializer()},
        tags=["Base"]
    )
    def about_us(self, request):
        about_us = AboutUs.objects.last()
        serializer = AboutUsSerializer(about_us, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)
