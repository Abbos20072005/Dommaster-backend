from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from authorization.models import CustomerAddresses
from .paginations.get_comments_me import get_comments_me_paginator
from .paginations.get_question_replies import get_question_replies_paginator
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .paginations.get_orders import get_orders_paginator
from rest_framework import status
from django.db.models import Q, Sum, Exists, OuterRef, Value, BooleanField
from .paginations.get_products_pagination import get_products_paginator
from .paginations.get_comments import get_comments_paginator
from .paginations.get_question import get_questions_paginator
from .paginations.get_comment_replies import get_comment_replies_paginator
from django.db.models import Count
from django.core.cache import cache
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Greatest
import secrets
from django.db import transaction
from base.models import Promocodes
from datetime import date
from base.models import Banner
from base.serializers import BannerSerializer
from utils.pyment_link import generate_link
from .models import ProductCategory, ProductSubCategory, ProductItemCategory, Product, Comment, Brand, Sale, AddsBrands, \
    Favourites, Cart, CartItem, Questions, Order, OrderItem, RecentlyViewedProducts, Service, CommentReply, \
    CommentImages, QuestionsReply
from .serializers import ProductCategorySerializer, ProductCategoryListSerializer, ProductSubCategorySerializer, \
    ProductItemCategorySerializer, ProductSerializer, CommentSerializer, BrandSerializer, FilterSerializer, \
    PaginationSerializer, BrandDetailSerializer, SaleSerializer, AddsBrandsSerializer, AddsBrandsDetailSerializer, \
    SearchByNameSerializer, CommentUpdateSerializer, FavouriteSerializer, FavouriteListSerializer, CartSerializer, \
    CartItemSerializer, CartItemUpdateSerializer, CartItemBulkUpdateSerializer, CommentParamSerializer, \
    CommentCreateSerializer, CartItemCreateSerializer, QuestionsSerializer, QuestionsUpdateSerializer, \
    QuestionsCreateSerializer, FavouriteCreateSerializer, FavouriteResponseSerializer, RecentlyViewedProductsSerializer, \
    OrderSerializer, SaleMainSerializer, ServiceSerializer, ServiceDetailSerializer, OrderDetailSerializer, \
    CommentReplySerializer, CommentReplyCreateSerializer, CommentReplyUpdateSerializer, QuestionsReplySerializer, \
    QuestionsReplyCreateSerializer, QuestionsReplyUpdateSerializer, OrderCancelSerializer, OrderPaySerializer, \
    OrderCreateSerializer, ProductCategorySearchSerializer, ProductCharacteristicsCreateSerializer, ProductSubCategoryCreateSerializer, \
    ProductItemCategoryCreateSerializer, ProductCreateSerializer, BrandByItemCategoriesSerializer, ProductCategoryFilterSerializer, \
    ProductShortSerializer
    

class MainPageViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Main page informations",
        operation_description="Main page informations",
        responses={200: "Result"},
        tags=["Main"]
    )
    def homepage_data(self, request):
        cache_key = f"home:main:data"

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(data={"result": cached_data, "ok": True}, status=status.HTTP_200_OK)
        
        result = []
        banners = list(Banner.objects.filter(is_visible=True).order_by("id"))
        addsbrands_list = AddsBrands.objects.filter(is_visible=True).prefetch_related("products")

        banner_index = 0

        for addsbrand in addsbrands_list:
            result.append({
                "type": "addsbrands",
                "data": AddsBrandsSerializer(addsbrand, context={"request": request}).data
            })

            if banner_index < len(banners):
                banner = banners[banner_index]
                result.append({
                    "type": "banner",
                    "data": BannerSerializer(banner, context={"request": request}).data
                })
                banner_index += 1

        cache.set(cache_key, result, timeout=1000)
        return Response(data={"result": result, "ok": True}, status=status.HTTP_200_OK)


class ProductViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Product create",
        operation_description="Product create",
        request_body=ProductCreateSerializer(),
        responses={200: ProductCreateSerializer()},
        tags=["Product"]
    )
    def product_create(self, request):
        serializer = ProductCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
        
        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_summary="Product sub categories create",
        operation_description="Product sub categories create",
        request_body=ProductSubCategoryCreateSerializer(),
        responses={200: ProductSubCategoryCreateSerializer()},
        tags=["Product"]
    )
    def sub_categories_create(self, request):
        serializer = ProductSubCategoryCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
        
        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_summary="Product categories create",
        operation_description="Product categories create",
        request_body=ProductItemCategoryCreateSerializer(),
        responses={200: ProductItemCategoryCreateSerializer()},
        tags=["Product"]
    )
    def item_categories_create(self, request):
        serializer = ProductItemCategoryCreateSerializer(data=request.data, context={"request": request}) 
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
        
        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product characteristics",
        operation_description="Product characteristics",
        request_body=ProductCharacteristicsCreateSerializer(),
        responses={200: ProductCharacteristicsCreateSerializer()},
        tags=["Product"]
    )
    def product_characteristics(self, request):
        serializer = ProductCharacteristicsCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
        
        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Most searched products",
        operation_description="Most searched products",
        responses={200: "Products name list"},
        tags=["Product"]
    )
    def most_search(self, request):
        products = Product.objects.annotate(most_solds=Sum("product_order_item__quantity")).exclude(
            most_solds=0).order_by(
            "-most_solds").values_list("name", flat=True)[:7]
        return Response(data={"result": products, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Recently viewed products",
        operation_description="Recently viewed products",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: RecentlyViewedProductsSerializer(many=True)},
        tags=["Product"]
    )
    def recently_viewed(self, request):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        recently_viewed_products = Product.objects.filter(recently_viewed_products__customer_id=request.user.id)
        return Response(data={"result": get_products_paginator(response_data=recently_viewed_products,
                                                               page=param_serializer.validated_data.get("page"),
                                                               page_size=param_serializer.validated_data.get(
                                                                   "page_size"), context={"request": request}),
                              "ok": True},
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Search products by name",
        operation_description="Search products by name",
        manual_parameters=[
            openapi.Parameter(name="q", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Search param")
        ],
        responses={200: SearchByNameSerializer(many=True)},
        tags=["Product"]
    )
    def search_by_name(self, request):
        param = request.query_params.get("q")
        if not param:
            return Response(data={"result": [], "ok": True}, status=status.HTTP_200_OK)

        param_data = param.strip()
        cache_key = f"{param_data}"

        query = cache.get(cache_key)
        if not query:
            product = Product.objects.annotate(
                similarity=Greatest(
                    TrigramSimilarity("name", param_data),
                    TrigramSimilarity("name_uz", param_data),
                    TrigramSimilarity("name_ru", param_data),
                    TrigramSimilarity("name_en", param_data)
                )
            ).filter(similarity__gt=0.01).order_by('-similarity').values_list("name", flat=True)[:5]

            category = ProductCategory.objects.annotate(
                similarity=Greatest(
                    TrigramSimilarity("name", param_data),
                    TrigramSimilarity("name_uz", param_data),
                    TrigramSimilarity("name_ru", param_data),
                    TrigramSimilarity("name_en", param_data)
                )
            ).filter(similarity__gt=0.01).order_by('-similarity')[:6]
            category_serializer = ProductCategorySearchSerializer(category, many=True,
                                                                  context={"request": request}).data

            brand = Brand.objects.annotate(
                similarity=Greatest(
                    TrigramSimilarity("name", param_data),
                    TrigramSimilarity("name_uz", param_data),
                    TrigramSimilarity("name_ru", param_data),
                    TrigramSimilarity("name_en", param_data)
                )
            ).filter(similarity__gt=0.01).order_by('-similarity')[:6]
            brand_serializer = BrandSerializer(brand, many=True, context={"request": request}).data

            cache.set(cache_key, {"products": product,
                                  "categories": category_serializer,
                                  "brands": brand_serializer}, timeout=240)

        return Response(data={"result": cache.get(cache_key), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Most sold products",
        operation_description="Most sold products",
        responses={200: ProductShortSerializer(many=True)},
        tags=["Product"]
    )
    def most_sold(self, request):
        products = Product.objects.annotate(most_solds=Sum("product_order_item__quantity")).exclude(
            most_solds=0).order_by(
            "-most_solds")[:10]
        serializer = ProductShortSerializer(products, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    #TODO: need to check if brand id receive string is it working or not
    @swagger_auto_schema(
        operation_summary="Product categories list",
        operation_description="Product categories list",
        manual_parameters=[
            openapi.Parameter(
                name='brand_id', in_=openapi.IN_QUERY, description='Brand id', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='is_main', in_=openapi.IN_QUERY, description='Is main category', type=openapi.TYPE_BOOLEAN)
        ],
        responses={200: ProductCategoryListSerializer(many=True)},
        tags=["Product"]
    )
    def categories_list(self, request):
        brand_id = request.query_params.get("brand_id")
        is_main = request.query_params.get("is_main", False)

        if is_main == "true" or is_main == "True" or brand_id:
            cache_key = f"categories:list:brand={brand_id or 'all'}"

            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(data={"result": cached_data, "ok": True}, status=status.HTTP_200_OK)

            if not brand_id:
                categories = ProductCategory.objects.all()
                serializer = ProductCategoryListSerializer(categories, many=True, context={"request": request})
            else:
                categories = ProductCategory.objects.filter(
                    product_category__product_sub_category__product_item_category__brand_id=brand_id,
                    product_category__product_sub_category__product_item_category__id__isnull=False
                ).distinct()
                serializer = ProductCategoryFilterSerializer(categories, many=True, context={"request": request})

            data = serializer.data
            cache.set(cache_key, data, timeout=1000)

            return Response(data={"result": data, "ok": True}, status=status.HTTP_200_OK)
        
        cache_key_main = f"categories:list"
        cached_data = cache.get(cache_key_main)
        if cached_data:
            return Response(data={"result": cached_data, "ok": True}, status=status.HTTP_200_OK)
        
        categories = ProductCategory.objects.filter()
        serializer = ProductCategorySerializer(categories, many=True, context={"request": request})
        data = serializer.data
        cache.set(cache_key_main, data, timeout=1000)
        return Response(data={"result": data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product category detail and sub categories list",
        operation_description="Product category detail and sub categories list",
        manual_parameters=[
            openapi.Parameter(
                name='brand_id', in_=openapi.IN_QUERY, description='Brand id', type=openapi.TYPE_INTEGER)
        ],
        responses={200: ProductCategorySerializer()},
        tags=["Product"]
    )
    def sub_category_list(self, request, pk):
        brand_id = request.query_params.get("brand_id")
        if not brand_id:
            category = ProductCategory.objects.filter(id=pk).first()
            if not category:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)
            

            serializer = ProductCategorySerializer(category, context={"request": request})
            return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)
        
        categories = ProductCategory.objects.filter(
            product_category__product_sub_category__product_item_category__brand_id=brand_id, 
            product_category__product_sub_category__product_item_category__id__isnull=False
        ).distinct().first()

        serializer = ProductCategorySerializer(categories, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product sub category detail and item category list",
        operation_description="Product sub category detail and item category list",
        responses={200: ProductSubCategorySerializer()},
        tags=["Product"]
    )
    def item_category_list(self, request, pk):
        sub_category = ProductSubCategory.objects.filter(id=pk).first()
        if not sub_category:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ProductSubCategorySerializer(sub_category, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="",
        operation_description="",
        responses={200: ProductItemCategorySerializer()},
        tags=["Product"]
    )
    def item_category_detail(self, request, pk):
        item_category = ProductItemCategory.objects.filter(id=pk).first()
        if not item_category:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ProductItemCategorySerializer(item_category, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product detail",
        operation_description="Product detail",
        responses={200: ProductSerializer()},
        tags=["Product"]
    )
    def product_detail(self, request, pk):
        products = Product.objects.filter(id=pk).first()
        if not products:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        customer = request.user.id
        if not customer:
            serializer = ProductSerializer(products, context={"request": request})
            return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

        recently_viewed_products = RecentlyViewedProducts.objects.filter(customer_id=customer,
                                                                         product_id=products.id).first()
        if not recently_viewed_products:
            RecentlyViewedProducts.objects.create(customer_id=customer, product_id=products.id)

        serializer = ProductSerializer(products, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Products filter",
        operation_description="Products filter",
        request_body=FilterSerializer(),
        responses={200: FilterSerializer(many=True)},
        tags=["Product"]
    )
    def product_filter(self, request):
        data = request.data
        serializer = FilterSerializer(data=data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        page = serializer.validated_data.get("page")
        page_size = serializer.validated_data.get("page_size")
        q = serializer.validated_data.get("q")
        price_from = serializer.validated_data.get("price_from", 0)
        price_to = serializer.validated_data.get("price_to", 0)
        sort_by = serializer.validated_data.get("sort_by")
        brand = serializer.validated_data.get("brand")
        item_category = serializer.validated_data.get("item_category")
        sale_id = serializer.validated_data.get("sale_id")

        filters = Q()

        sort = "created_at"
        if sort_by:
            sort = {
                "newest": "-created_at",
                "price": "price",
                "rating": "-rating"
            }.get(sort_by, "-created_at")

        if price_from or price_to:
            filters &= Q(price__gte=price_from)
            filters &= Q(price__lte=price_to)

        if brand:
            filters &= Q(brand=brand)

        if item_category:
            filters &= Q(product_item_category=item_category)

        if sale_id:
            filters &= Q(sale_products__id=sale_id)

        if q:
            similarity = Greatest(
                TrigramSimilarity("name", q),
                TrigramSimilarity("name_uz", q),
                TrigramSimilarity("name_ru", q),
                TrigramSimilarity("name_en", q),
            )
            products = Product.objects.annotate(similarity=similarity).filter(filters).filter(similarity__gt=0.3).order_by("-similarity", sort)
        else:
            products = Product.objects.filter(filters).order_by(sort)

        return Response(data={"result": get_products_paginator(response_data=products, page=page, page_size=page_size,
                                                               context={"request": request}), "ok": True},
                        status=status.HTTP_200_OK)


class CommentViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Comment reply delete",
        operation_description="Comment reply delete",
        responses={204: "Comment successfully deleted"},
        tags=["Comment"]
    )
    def reply_delete(self, request, pk):
        comment_reply = CommentReply.objects.filter(id=pk, customer_id=request.user.id).first()
        if not comment_reply:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        comment_reply.delete()
        return Response(data={"result": "Comment successfully deleted", "ok": True}, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary="Comment reply create",
        operation_description="Comment reply create",
        request_body=CommentReplyCreateSerializer(),
        responses={200: CommentReplyCreateSerializer()},
        tags=["Comment"]
    )
    def reply_create(self, request, pk):
        data = request.data
        comment = Comment.objects.filter(id=pk).first()
        if not comment:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        data["comment"] = pk
        data["customer"] = request.user.id
        serializer = CommentReplyCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Replies list",
        operation_description="Replies list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: CommentReplySerializer(many=True)},
        tags=["Comment"]
    )
    def reply_list(self, request, pk):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        comment_reply = CommentReply.objects.filter(comment_id=pk, is_visible=True)
        return Response(data={
            "result": get_comment_replies_paginator(response_data=comment_reply, context={"request": request},
                                                    page=param_serializer.validated_data.get("page"),
                                                    page_size=param_serializer.validated_data.get("page_size")),
            "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Comment reply update",
        operation_description="Comment reply update",
        request_body=CommentReplyUpdateSerializer(),
        responses={202: CommentReplyUpdateSerializer()},
        tags=["Comment"]
    )
    def reply_update(self, request, pk):
        comment_reply = CommentReply.objects.filter(id=pk, customer_id=request.user.id).first()
        serializer = CommentReplyUpdateSerializer(comment_reply, data=request.data, partial=True,
                                                  context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        operation_summary="My comments list",
        operation_description="My comments list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: CommentSerializer(many=True)},
        tags=["Comment"]
    )
    def my_comments(self, request):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        comments = Comment.objects.filter(customer=request.user.id)
        return Response(data={
            "result": get_comments_me_paginator(response_data=comments,
                                                page=param_serializer.validated_data.get("page"),
                                                page_size=param_serializer.validated_data.get("page_size"),
                                                context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Get product comments",
        operation_description="Get product comments",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='product_id', in_=openapi.IN_QUERY, description='Product id', type=openapi.TYPE_INTEGER),
        ],
        responses={200: CommentSerializer(many=True)},
        tags=["Comment"]
    )
    def product_comments(self, request):
        params = request.query_params
        param_serializer = CommentParamSerializer(data=params)
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        comments = Comment.objects.annotate(reply_count=Count("comment_reply")).filter(
            product=param_serializer.validated_data.get("product_id")).order_by("-created_at")

        return Response(data={
            "result": get_comments_paginator(
                response_data={"comments": comments, "product_id": param_serializer.validated_data.get("product_id")},
                page=param_serializer.validated_data.get("page"),
                page_size=param_serializer.validated_data.get("page_size"),
                context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    #TODO: need to optimize
    @swagger_auto_schema(
        operation_summary="Write comment to product",
        operation_description="Write comment to product",
        manual_parameters=[
            openapi.Parameter(name="product_id", in_=openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                              description="Product id")
        ],
        request_body=CommentCreateSerializer(),
        responses={201: CommentCreateSerializer()},
        tags=["Comment"]
    )
    def comment_create(self, request):
        param = request.query_params
        product = Product.objects.filter(id=param.get("product_id")).first()
        if not product:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        comment = Comment.objects.filter(customer_id=request.user.id, product_id=product.id).first()
        if comment:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Your comment already exist")

        data = request.data.copy()                              # <- we need here copy() to avoid "request data is immutable" error
        data["customer"] = request.user.id
        data["product"] = param.get("product_id")
        serializer = CommentCreateSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
        
        images = None
        if serializer.validated_data.get("images"):
            images = serializer.validated_data.pop("images")
        
        comment = serializer.save()
        if images:
            for image in images:
                CommentImages.objects.create(customer_id=request.user.id, comment_id=comment.id, image=image)

        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Comment update",
        operation_description="Comment update",
        request_body=CommentUpdateSerializer(),
        responses={200: CommentSerializer()},
        tags=["Comment"]
    )
    def comment_update(self, request, pk):
        comment = Comment.objects.filter(id=pk).first()
        if not comment:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        if comment.customer.id != request.user.id:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="You could not update this comment")

        serializer = CommentUpdateSerializer(comment, data=request.data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Comment delete",
        operation_description="Comment delete",
        responses={204: "Your comment successfully deleted"},
        tags=["Comment"]
    )
    def comment_delete(self, request, pk):
        comment = Comment.objects.filter(id=pk).first()
        if not comment:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        if comment.customer.id != request.user.id:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="You could not delete the comment")

        comment.delete()
        return Response(data={"result": "Your comment successfully deleted", "ok": True},
                        status=status.HTTP_204_NO_CONTENT)


class BrandViewSet(ViewSet):
    #TODO: need to check if category id receive string is it working or not
    @swagger_auto_schema(
        operation_summary="Brands list",
        operation_description="Brands list",
        manual_parameters=[
            openapi.Parameter(
                name="item_category_id", in_=openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Item category id"
            ),
        ],
        responses={200: BrandSerializer(many=True)},
        tags=["Brand"]
    )
    def brand_list(self, request):
        category_id = request.query_params.get("item_category_id")
        cache_key = f"categories:list:item:category={category_id or 'all'}"

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(data={"result": cached_data, "ok": True}, status=status.HTTP_200_OK)
        
        if not category_id:
            brands = Brand.objects.filter(is_visible=True)
            serializer = BrandSerializer(brands, many=True, context={"request": request})
        else:
            brands = Brand.objects.filter(product_brand__product_item_category_id=category_id).distinct()
            serializer = BrandByItemCategoriesSerializer(brands, many=True, context={"request": request})
        data = serializer.data
        cache.set(cache_key, data, timeout=1000)
        return Response(data={"result": data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Brand detail",
        operation_description="Brand detail",
        responses={200: BrandDetailSerializer()},
        tags=["Brand"]
    )
    def brand_detail(self, request, pk):
        brand = Brand.objects.annotate(products_count=Count("product_brand")).filter(id=pk).first()
        if not brand:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = BrandDetailSerializer(brand, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

class SaleViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Sale list",
        operation_description="Sale list",
        responses={200: SaleSerializer(many=True)},
        tags=["Sale"]
    )
    def sale_list(self, request):
        sale = Sale.objects.filter(is_visible=True)
        serializer = SaleSerializer(sale, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Sale main",
        operation_description="Sale main",
        responses={200: SaleMainSerializer()},
        tags=["Sale"]
    )
    def sale_main(self, request):
        sale = Sale.objects.filter(is_main=True, is_visible=True).first()
        if not sale:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = SaleMainSerializer(sale, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Sale detail, pk receive sale id",
        operation_description="Sale detail, pk receive sale id",
        responses={200: SaleSerializer()},
        tags=["Sale"]
    )
    def sale_detail(self, request, pk):
        sale = Sale.objects.filter(id=pk, is_visible=True).first()
        if not sale:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = SaleSerializer(sale, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class AddsBrandsViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Adds brands list",
        operation_description="Adds brands list",
        responses={200: AddsBrandsSerializer(many=True)},
        tags=["AddsBrands"]
    )
    def adds_brands(self, request):
        adds_brands = AddsBrands.objects.filter(is_visible=True).prefetch_related("products")
        serializer = AddsBrandsSerializer(adds_brands, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Adds brands detail, pk receive adds brands id",
        operation_description="Adds brands detail, pk receive adds brands id",
        responses={200: AddsBrandsDetailSerializer()},
        tags=["AddsBrands"]
    )
    def adds_brands_detail(self, request, pk):
        adds_brands = AddsBrands.objects.filter(id=pk).first()
        serializer = AddsBrandsDetailSerializer(adds_brands, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class FavouriteViewSet(ViewSet):
    #TODO: need to check if user delete account and send request with old token it's returning error
    @swagger_auto_schema(
        operation_summary="Create favourite product or delete it from favourite",
        operation_description="Create favourite product or delete it from favourite",
        request_body=FavouriteCreateSerializer(),
        responses={201: FavouriteSerializer(), 204: "Product successfully removed from favourite"},
        tags=["Favourite"]
    )
    def create_favourite(self, request):
        data = request.data
        customer = request.user.id

        data_serializer = FavouriteCreateSerializer(data=data, context={"request": request})
        if not data_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=data_serializer.errors)

        if not customer:
            token = request.COOKIES.get("favourite_token")
            if not token:
                token = secrets.token_hex(16)

            favourite = Favourites.objects.filter(favourite_token=token,
                                                  product_id=data_serializer.validated_data.get("product")).first()
            if favourite:
                favourite.delete()
                return Response(data={"result": "Product successfully removed from favourite", "ok": True},
                                status=status.HTTP_204_NO_CONTENT)

            data["favourite_token"] = token
            favourite_serializer = FavouriteSerializer(data=data, context={"request": request})

            if not favourite_serializer.is_valid():
                raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=favourite_serializer.errors)
            
            favourite_serializer.save()
            resp = Response(data={"result": favourite_serializer.data, "ok": True}, status=status.HTTP_200_OK)
            resp.set_cookie("favourite_token", favourite_serializer.validated_data.get("favourite_token"),
                            httponly=False,
                            secure=True, samesite="None")

            return resp

        favourite = Favourites.objects.filter(customer_id=customer,
                                              product_id=data_serializer.validated_data.get("product")).first()
        if favourite:
            favourite.delete()
            return Response(data={"result": "Product successfully removed from favourite", "ok": True},
                            status=status.HTTP_204_NO_CONTENT)

        data["customer"] = customer
        serializer = FavouriteSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Favourite products list",
        operation_description="Favourite products list",
        responses={200: FavouriteListSerializer(many=True)},
        tags=["Favourite"]
    )
    def favourite_list(self, request):
        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("favourite_token")
            if not token:
                token = secrets.token_hex(16)

            favourite = Favourites.objects.filter(favourite_token=token)
            serializer = FavouriteResponseSerializer(favourite, many=True, context={"request": request})

            resp = Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)
            resp.set_cookie("favourite_token", token,
                            httponly=False,
                            secure=True, samesite="None")

            return resp

        token = request.COOKIES.get("favourite_token")
        guest_favourite = None
        if token:
            guest_favourite = Favourites.objects.filter(favourite_token=token, customer__isnull=True)

        if guest_favourite:
            with transaction.atomic():
                for item in guest_favourite.all():
                    favourite_item = Favourites.objects.filter(customer_id=customer, product=item.product).first()

                    if not favourite_item:
                        Favourites.objects.create(customer_id=customer, product=item.product)
                        item.delete()
        favourites = Favourites.objects.filter(customer_id=customer)
        resp = Response(
            data={"result": FavouriteResponseSerializer(favourites, many=True, context={"request": request}).data,
                  "ok": True},
            status=status.HTTP_200_OK)

        resp.delete_cookie("cart_token")
        return resp


class CartViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Get cart",
        operation_description="Get cart",
        responses={200: CartSerializer(many=True)},
        tags=["Cart"]
    )
    def get_cart(self, request):
        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("cart_token")
            if not token:
                token = secrets.token_hex(16)

            cart = Cart.objects.filter(cart_token=token).first()
            if not cart:
                cart = Cart.objects.create(cart_token=token)

            resp = Response(data={"result": CartSerializer(cart, context={"request": request}).data, "ok": True},
                            status=status.HTTP_200_OK)

            resp.set_cookie("cart_token", cart.cart_token, httponly=False,
                            secure=True, samesite="None")

            return resp

        cart = Cart.objects.filter(customer_id=customer).first()
        if not cart:
            cart = Cart.objects.create(customer_id=customer)

        token = request.COOKIES.get("cart_token")
        guest_cart = None
        if token:
            guest_cart = Cart.objects.filter(cart_token=token, customer__isnull=True).first()

        if guest_cart:
            with transaction.atomic():
                for item in guest_cart.cart_item.all():
                    cart_item = CartItem.objects.filter(cart_id=cart.id, product=item.product).first()

                    if not cart_item:
                        CartItem.objects.create(cart_id=cart.id, product=item.product,
                                                quantity=item.quantity)
                        item.delete()
                        continue

                    cart_item.quantity += item.quantity
                    cart_item.save(update_fields=["quantity"])
                    item.delete()

                guest_cart.delete()

        resp = Response(data={"result": CartSerializer(cart, context={"request": request}).data, "ok": True},
                        status=status.HTTP_200_OK)

        resp.delete_cookie("cart_token")
        return resp

    @swagger_auto_schema(
        operation_summary="Create cart item",
        operation_description="Create cart item",
        request_body=CartItemCreateSerializer(),
        responses={200: CartSerializer()},
        tags=["Cart"]
    )
    def create_cart_item(self, request):
        data = request.data
        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("cart_token")
            if not token:
                token = secrets.token_hex(16)
                cart = Cart.objects.create(cart_token=token)
                data["cart"] = cart.id
                serializer = CartItemCreateSerializer(data=data, context={"request": request})
                if not serializer.is_valid():
                    raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

                serializer.save()
                resp = Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)
                resp.set_cookie("cart_token", token, httponly=False,
                                secure=True, samesite="None")
                return resp

            cart = Cart.objects.filter(cart_token=token).first()
        else:
            cart = Cart.objects.filter(customer=customer).first()

        data["cart"] = cart.id
        serializer = CartItemCreateSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update cart item",
        operation_description="Update cart item",
        request_body=CartItemUpdateSerializer(),
        responses={202: CartItemSerializer(), 204: "Product successfully deleted from cart"},
        tags=["Cart"]
    )
    def update_cart_item(self, request):
        data = request.data
        data_serializer = CartItemUpdateSerializer(data=data, context={"request": request})
        if not data_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=data_serializer.errors)

        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("cart_token")
            cart_item = CartItem.objects.filter(cart__cart_token=token,
                                                product=data_serializer.validated_data.get("product").id).first()

            if not cart_item:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Product does not exist")
            
            if cart_item and data_serializer.validated_data.get("quantity") == 0:
                cart_item.delete()
                return Response(data={"result": "Product successfully deleted from cart", "ok": True},
                                status=status.HTTP_204_NO_CONTENT)
            
        else:
            cart_item = CartItem.objects.filter(cart__customer=customer,
                                                product=data_serializer.validated_data.get("product").id).first()
            
            if not cart_item:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Product does not exist")

            if cart_item and data_serializer.validated_data.get("quantity") == 0:
                cart_item.delete()
                return Response(data={"result": "Product successfully deleted from cart", "ok": True},
                                status=status.HTTP_204_NO_CONTENT)

        data["cart"] = cart_item.cart.id
        serializer = CartItemUpdateSerializer(cart_item, data=data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        operation_summary="Cart item bulk update",
        operation_description="Cart item bulk update",
        request_body=CartItemBulkUpdateSerializer(),
        responses={200: CartItemSerializer()},
        tags=["Cart"]
    )
    def cart_bulk_update(self, request):
        bulk_serializer = CartItemBulkUpdateSerializer(data=request.data)
        if not bulk_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=bulk_serializer.errors)

        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("cart_token")
            cart_items = CartItem.objects.filter(cart__cart_token=token)
        else:
            cart_items = CartItem.objects.filter(cart__customer=customer)

        is_delete = bulk_serializer.validated_data.get("is_delete")
        

        for cart_item in cart_items:
            if is_delete is True:
                cart_item.delete()
                continue

            cart_item.is_checked = bulk_serializer.validated_data.get("is_checked")
            cart_item.save(update_fields=["is_checked"])

        return Response(data={"result": "All products is_checked status successfully updated", "ok": True},
                        status=status.HTTP_202_ACCEPTED)


class ServiceViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Service list",
        operation_description="Service list",
        responses={200: ServiceSerializer(many=True)},
        tags=["Service"]
    )
    def service_list(self, request):
        services = Service.objects.all()
        serializer = ServiceSerializer(services, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Service detail",
        operation_description="Service detail",
        responses={200: ServiceDetailSerializer()},
        tags=["Service"]
    )
    def service_detail(self, request, pk):
        service = Service.objects.filter(id=pk).first()
        serializer = ServiceDetailSerializer(service, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class QuestionsViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Question reply delete",
        operation_description="Question reply delete",
        responses={204: "Question reply successfully deleted"},
        tags=["Question"]
    )
    def reply_delete(self, request, pk):
        question_reply = QuestionsReply.objects.filter(id=pk, customer_id=request.user.id).first()
        if not question_reply:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        question_reply.delete()
        return Response(data={"result": "Question reply successfully deleted", "ok": True},
                        status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary="Question reply update",
        operation_description="Question reply update",
        request_body=QuestionsReplyUpdateSerializer(),
        responses={202: QuestionsReplyUpdateSerializer()},
        tags=["Question"]
    )
    def reply_update(self, request, pk):
        question_reply = QuestionsReply.objects.filter(id=pk, customer_id=request.user.id).first()
        serializer = QuestionsReplyUpdateSerializer(question_reply, data=request.data, partial=True,
                                                    context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        operation_summary="Question reply create",
        operation_description="Question reply create",
        request_body=QuestionsReplyCreateSerializer(),
        responses={200: QuestionsReplyCreateSerializer()},
        tags=["Question"]
    )
    def reply_create(self, request, pk):
        data = request.data
        question_reply = Questions.objects.filter(id=pk).first()
        if not question_reply:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        data["question"] = pk
        data["customer"] = request.user.id
        serializer = QuestionsReplyCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Questions replies list",
        operation_description="Question replies list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: QuestionsSerializer(many=True)},
        tags=["Question"]
    )
    def reply_list(self, request, pk):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        questions_replies = QuestionsReply.objects.filter(question_id=pk)
        return Response(data={"result": get_question_replies_paginator(response_data=questions_replies,
                                                                       page=param_serializer.validated_data.get("page"),
                                                                       page_size=param_serializer.validated_data.get(
                                                                           "page_size"), context={"request": request}),
                              "ok": True},
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="My questions list",
        operation_description="My questions list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: QuestionsSerializer(many=True)},
        tags=["Question"]
    )
    def my_questions(self, request):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        questions = Questions.objects.filter(customer=request.user.id)
        return Response(data={
            "result": get_questions_paginator(response_data=questions, page=param_serializer.validated_data.get("page"),
                                              page_size=param_serializer.validated_data.get("page_size"),
                                              context={"request": request}), "ok": True},
            status=status.HTTP_200_OK)

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

        questions = Questions.objects.annotate(reply_count=Count("question_reply")).filter(
            product=param_serializer.validated_data.get("product_id"))
        return Response(data={
            "result": get_questions_paginator(response_data=questions, page=param_serializer.validated_data.get("page"),
                                              page_size=param_serializer.validated_data.get("page_size"),
                                              context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create product question",
        operation_description="Create product question",
        manual_parameters=[
            openapi.Parameter(name="product_id", in_=openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                              description="Product id")
        ],
        request_body=QuestionsCreateSerializer(),
        responses={201: QuestionsCreateSerializer()},
        tags=["Question"]
    )
    def question_create(self, request):
        param = request.query_params
        data = request.data
        data["customer"] = request.user.id
        data["product"] = param.get("product_id")
        serializer = QuestionsCreateSerializer(data=data, context={"reqeust": request})
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


class OrderViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Order pay",
        operation_description="Order pay",
        request_body=OrderPaySerializer(),
        responses={200: OrderSerializer()},
        tags=["Order"]
    )
    def order_pay(self, request):
        data = request.data
        data_serializer = OrderPaySerializer(data=data)
        if not data_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=data_serializer.errors)

        order = Order.objects.filter(id=data_serializer.validated_data.get("order_id"), customer_id=request.user.id,
                                     status=0).first()
        if not order:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        payment_link = generate_link(order_id=order.id, total_price=order.total_price,
                                     type_pyment=data_serializer.validated_data.get("payment_type"),
                                     is_web=data_serializer.validated_data.get("is_web"))
        return Response(data={"result": payment_link, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Order cancel",
        operation_description="Order cancel",
        responses={200: OrderSerializer()},
        tags=["Order"]
    )
    def cancel_order(self, request, pk):
        order = Order.objects.filter(id=pk, customer_id=request.user.id).first()
        if not order:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)
        
        if order.status != 0:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="You could not cancel this order")

        order.status = 4
        order.save(update_fields=["status"])
        return Response(data={"result": OrderSerializer(order, context={"request": request}).data, "ok": True},
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create order",
        operation_description="Create order",
        request_body=OrderCreateSerializer(),
        responses={201: OrderSerializer()},
        tags=["Order"]
    )
    def create_order(self, request):
        cart = Cart.objects.filter(customer_id=request.user.id).first()
        if not cart:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Cart not found")

        data = request.data
        serializer = OrderCreateSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
        
        customer_address_id = serializer.validated_data.get("address_id")
        if customer_address_id:
            customer_location = CustomerAddresses.objects.filter(customer_id=request.user.id, id=customer_address_id).first()
            if not customer_location:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Customer location not found")
            
            customer_locatioins = CustomerAddresses.objects.filter(customer_id=request.user.id).exclude(id=customer_address_id)
            for location in customer_locatioins:
                location.is_default = False
                location.save(update_fields=["is_default"])
            
            customer_location.is_default = True
            customer_location.save(update_fields=["is_default"])

        else:
            customer_location = CustomerAddresses.objects.filter(customer_id=request.user.id, is_default=True).first()
            if not customer_location:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Customer location not found")

        promocode = Promocodes.objects.filter(name=serializer.validated_data.get("promocode")).first()
        if promocode:
            if promocode.expires_at < date.today():
                raise CustomApiException(error_code=ErrorCodes.PROMOCODE_EXPIRED)

            promocode_discount_price = 0
            if not promocode.discount_precent and promocode.discount_price:
                promocode_discount_price = cart.total_price - promocode.discount_price
            elif not promocode.discount_price and promocode.discount_precent:
                promocode_discount_price = cart.total_price * (1 - (promocode.discount_precent / 100))

            order = Order.objects.create(customer_id=request.user.id, promocode_id=promocode.id,
                                         total_price=promocode_discount_price, order_location=customer_location)
        else:
            order = Order.objects.create(customer_id=request.user.id, total_price=cart.products_total_price,
                                         order_location=customer_location)

        cart_items = CartItem.objects.filter(cart_id=cart.id).exclude(is_checked=False)
        for cart_item in cart_items:
            OrderItem.objects.create(order=order, product=cart_item.product, quantity=cart_item.quantity)
            cart_item.delete()

        payment_link = generate_link(order_id=order.id, total_price=order.total_price,
                                     type_pyment=serializer.validated_data.get("payment_type"),
                                     is_web=serializer.validated_data.get("is_web"))
        return Response(data={"result": payment_link, "order_id": order.id, "ok": True},
                        status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Order detail",
        operation_description="Order detail",
        responses={201: OrderDetailSerializer()},
        tags=["Order"]
    )
    def order_detail(self, request, pk):
        order = Order.objects.filter(id=pk, customer_id=request.user.id).first()
        if not order:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = OrderDetailSerializer(order, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Orders history list",
        operation_description="Orders history list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: OrderSerializer(many=True)},
        tags=["Order"]
    )
    def orders_history_list(self, request):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        orders = Order.objects.filter(Q(status=3) | Q(status=4), customer_id=request.user.id).order_by("-created_at")
        return Response(data={
            "result": get_orders_paginator(response_data=orders, page=param_serializer.validated_data.get("page"),
                                           page_size=param_serializer.validated_data.get("page_size"),
                                           context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Orders active list",
        operation_description="Orders active list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: OrderSerializer(many=True)},
        tags=["Order"]
    )
    def orders_active_list(self, request):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params, context={"request": request})
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        orders = Order.objects.filter(customer_id=request.user.id).exclude(Q(status=3) | Q(status=4)).order_by(
            "-created_at")
        return Response(data={
            "result": get_orders_paginator(response_data=orders, page=param_serializer.validated_data.get("page"),
                                           page_size=param_serializer.validated_data.get("page_size"),
                                           context={"request": request}), "ok": True}, status=status.HTTP_200_OK)
