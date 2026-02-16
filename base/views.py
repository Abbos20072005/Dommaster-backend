from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from service.serializers import PaginationSerializer
from .paginations.get_news import get_news_paginator
from .paginations.get_articles import get_articles_paginator
from .paginations.get_reviews import get_reviews_paginator
from .serializers import BannerSerializer, MessageSerializer, MessageCreateSerializer, AboutUsSerializer, \
    ChatCreateSerializer, PromocodeRequestSerializer, NewsSerializer, NewsDetailSerializer, ArticlesSerializer, \
    ArticlesDetailSerializer, ReviewsSerializer, ReviewsDetailSerializer, VideoSerializer, PromocodeSerializer, DeleteButtonSerializer
from .models import Banner, Chat, AboutUs, Messages, Promocodes, News, Articles, Reviews, Video, DeleteButton
from service.models import Cart
from drf_yasg import openapi
from datetime import date
import secrets
from django.core.cache import cache


class VideoViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Video list",
        operation_description="Video list",
        responses={200: VideoSerializer(many=True)},
        tags=["Video"]
    )
    def video_list(self, request):
        video = Video.objects.all()
        serializer = VideoSerializer(video, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Video detail",
        operation_description="Video detail",
        responses={200: VideoSerializer()},
        tags=["Video"]
    )
    def video_detail(self, request, pk):
        video = Video.objects.filter(id=pk).first()
        if not video:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = VideoSerializer(video, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class ReviewsViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Reviews list",
        operation_description="Reviews list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: ReviewsSerializer(many=True)},
        tags=["Reviews"]
    )
    def reviews_list(self, request):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        reviews = Reviews.objects.all()
        return Response(data={
            "result": get_reviews_paginator(response_data=reviews, page=param_serializer.validated_data.get("page"),
                                            page_size=param_serializer.validated_data.get("page_size"),
                                            context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Reviews detail",
        operation_description="Reviews detail",
        responses={200: ReviewsDetailSerializer()},
        tags=["Reviews"]
    )
    def reviews_detail(self, request, pk):
        reviews = Reviews.objects.filter(id=pk).first()
        if not reviews:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ReviewsDetailSerializer(reviews, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class ArticlesViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Articles list",
        operation_description="Articles list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: ArticlesSerializer(many=True)},
        tags=["Articles"]
    )
    def articles_list(self, request):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        articles = Articles.objects.all()
        return Response(data={
            "result": get_articles_paginator(response_data=articles, page=param_serializer.validated_data.get("page"),
                                             page_size=param_serializer.validated_data.get("page_size"),
                                             context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Articles detail",
        operation_description="Articles detail",
        responses={200: ArticlesDetailSerializer()},
        tags=["Articles"]
    )
    def articles_detail(self, request, pk):
        articles = Articles.objects.filter(id=pk).first()
        if not articles:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ArticlesDetailSerializer(articles, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class NewsViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="News list",
        operation_description="News list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: NewsSerializer(many=True)},
        tags=["News"]
    )
    def news_list(self, request):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        news = News.objects.all()
        return Response(data={
            "result": get_news_paginator(response_data=news, page=param_serializer.validated_data.get("page"),
                                         page_size=param_serializer.validated_data.get("page_size"),
                                         context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="News detail",
        operation_description="News detail",
        responses={200: NewsDetailSerializer()},
        tags=["News"]
    )
    def news_detail(self, request, pk):
        news = News.objects.filter(id=pk).first()
        if not news:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = NewsDetailSerializer(news, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class PromocodeViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Promocodes list",
        operation_description="Promocodes list",
        responses={200: PromocodeSerializer(many=True)},
        tags=["Order"]
    )
    def promocode_list(self, request):
        promocode = Promocodes.objects.filter(customer_id=request.user.id)
        serializer = PromocodeSerializer(promocode, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Promocode checker",
        operation_description="Promocode checker",
        request_body=PromocodeRequestSerializer(),
        responses={},
        tags=["Order"]
    )
    def promocode_checker(self, request):
        cart = Cart.objects.filter(customer_id=request.user.id).first()
        if not cart:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Cart not found")
        
        promocode_owner = Promocodes.objects.filter(code=serializer.validated_data.get("promocode").lower(), customer_id=request.user.id).first()
        if not promocode_owner:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Promocode does not found")

        data = request.data
        serializer = PromocodeRequestSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        promocode = Promocodes.objects.filter(code=serializer.validated_data.get("promocode").lower()).first()
        if not promocode:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Promocode does not found")

        if promocode.expires_at < date.today():
            raise CustomApiException(error_code=ErrorCodes.PROMOCODE_EXPIRED)

        promocode_discount_price = 0
        if not promocode.discount_precent and promocode.discount_price:
            promocode_discount_price = cart.total_price - promocode.discount_price
        elif not promocode.discount_price and promocode.discount_precent:
            promocode_discount_price = cart.total_price * (1 - (promocode.discount_precent / 100))

        return Response(
            data={"result": {"total_price": promocode_discount_price,
                             "saved_price": cart.total_price - promocode_discount_price,
                             "discount_precent": promocode.discount_precent,
                             "promocode": serializer.validated_data.get("promocode")},
                  "ok": True}, status=status.HTTP_200_OK)


class BannerViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Banner",
        operation_description="Banner",
        responses={200: BannerSerializer(many=True)},
        tags=["Base"]
    )
    def banner_list(self, request):
        # cache_key = f"banner:list"
        # cached_data = cache.get(cache_key)
        # if cached_data:
        #     return Response(data={"result": cached_data, "ok": True}, status=status.HTTP_200_OK)
        
        banner = Banner.objects.filter(is_visible=True)
        serializer = BannerSerializer(banner, many=True, context={"request": request}).data
        # cache.set(cache_key, serializer, timeout=1000)
        return Response(data={"result": serializer, "ok": True}, status=status.HTTP_200_OK)


class ChatViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Chat messages list",
        operation_description="Chat messages list",
        responses={200: MessageSerializer(many=True)},
        tags=["Chat"]
    )
    def message_list(self, request):
        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("chat_token")
            if not token:
                token = secrets.token_hex(16)

            chat = Chat.objects.filter(chat_token=token).first()
            if not chat:
                chat = Chat.objects.create(chat_token=token)

            messages = Messages.objects.filter(chat=chat.id)
            serializer = MessageSerializer(messages, many=True, context={"request": request})

            resp = Response(data={"result": serializer.data, "ok": True},
                            status=status.HTTP_200_OK)

            resp.set_cookie("chat_token", chat.chat_token, httponly=False,
                            secure=True, samesite="None")

            return resp

        chat = Chat.objects.filter(customer_id=customer).first()
        if not chat:
            create_serializer = ChatCreateSerializer(data={"customer": customer},
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
        customer = request.user.id
        data = request.data.copy()

        if not customer:
            token = request.COOKIES.get("chat_token")
            if not token:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND,
                                         message="You could not write to chat because you don't have any chat")
            chat = Chat.objects.filter(chat_token=token).first()
            if not chat:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

            data["chat"] = chat.id
            serializer = MessageCreateSerializer(data=data, context={"request": request})
            if not serializer.is_valid():
                raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

            serializer.save()
            return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

        chat = Chat.objects.filter(customer_id=request.user.id).first()
        if not chat:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        data["chat"] = chat.id
        serializer = MessageCreateSerializer(data=data,
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
    
class DeleteButtonViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Delete Button",
        operation_description="Delete Button",
        responses={200: DeleteButtonSerializer()},
        tags=["Delete Button"]
    )
    def delete_button(self, request):
        delete_button = DeleteButton.objects.last()
        return Response(data={"result": DeleteButtonSerializer(delete_button).data, "ok": True}, status=status.HTTP_200_OK)
