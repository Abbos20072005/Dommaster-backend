from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from service.models import Product
from service.serializers import CommentParamSerializer
from .paginations.get_questions import get_questions_paginator
from .serializers import BannerSerializer, MessageSerializer, MessageCreateSerializer, AboutUsSerializer, \
    ChatCreateSerializer, QuestionsSerializer, QuestionsUpdateSerializer
from .models import Banner, Chat, AboutUs, Messages, Questions
from drf_yasg import openapi


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


class QuestionsViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Product questions list",
        operation_description="Product questions list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='product_id', in_=openapi.IN_QUERY, description='Product id', type=openapi.TYPE_INTEGER),
        ],
        responses={200: QuestionsSerializer(many=True)},
        tags=["Question"]
    )
    def questions_list(self, request):
        param = request.query_params
        param_serializer = CommentParamSerializer(data=param)
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        questions = Questions.objects.filter(product=param_serializer.validated_data.get("product_id"))
        return Response(data={
            "result": get_questions_paginator(response_data=questions, page=param_serializer.validated_data.get("page"),
                                              page_size=param_serializer.validated_data.get("page_size"),
                                              context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create product question",
        operation_description="Create product question",
        request_body=QuestionsSerializer(),
        responses={201: QuestionsSerializer()},
        tags=["Question"]
    )
    def question_create(self, request, pk):
        data = request.data
        data["customer"] = request.user.id
        data["product"] = pk
        serializer = QuestionsSerializer(data=data, context={"reqeust": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Update product question",
        operation_description="Update product question",
        request_body=QuestionsUpdateSerializer(),
        responses={204: QuestionsUpdateSerializer()},
        tags=["Question"]
    )
    def update_question(self, request, pk):
        data = request.data
        question = Questions.objects.filter(id=pk, customer_id=request.user.id).first()
        if not question:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = QuestionsUpdateSerializer(question, data=data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        operation_summary="Delete product question",
        operation_description="Delete product question",
        responses={204: "Question successfully deleted"},
        tags=["Question"]
    )
    def delete_question(self, request, pk):
        question = Questions.objects.filter(id=pk, customer=request.user.id).first()
        if not question:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        question.delete()
        return Response(data={"result": "Question successfully deleted", "ok": True}, status=status.HTTP_204_NO_CONTENT)
