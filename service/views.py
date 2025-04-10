from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .serializers import ProductCategorySerializer, ProductCategoryListSerializer, ProductSubCategorySerializer, \
    ProductItemCategorySerializer, ProductSerializer, CommentSerializer, BrandSerializer, FilterSerializer, \
    PaginationSerializer, BrandDetailSerializer, SaleSerializer, AddsBrandsSerializer, AddsBrandsDetailSerializer, \
    SearchByNameSerializer
from .models import ProductCategory, ProductSubCategory, ProductItemCategory, Product, Comment, Brand, Sale, AddsBrands
from rest_framework import status
from django.db.models import Q
from .paginations.get_products_pagination import get_products_paginator
from django.db.models import Count
from django.core.cache import cache
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Greatest


# TODO: need to add comment create and check if user already write comment to this project one user could write only one comment.
# TODO: add the most salled products list api
# TODO: add the new products list


class ProductViewSet(ViewSet):
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
        param_data = request.query_params.get("q").strip().lower()
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
            ).filter(similarity__gt=0.1).order_by('-similarity').values_list("name", flat=True)
            cache.set(cache_key, product, timeout=300)

        return Response(data={"result": cache.get(cache_key), "ok": True}, status=status.HTTP_200_OK)


    @swagger_auto_schema(
        operation_summary="Product categories list",
        operation_description="Product categories list",
        responses={200: ProductCategoryListSerializer(many=True)},
        tags=["Product"]
    )
    def categories_list(self, request):
        category = ProductCategory.objects.all()
        serializer = ProductCategoryListSerializer(category, many=True)
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product category detail and sub categories list",
        operation_description="Product category detail and sub categories list",
        responses={200: ProductCategorySerializer()},
        tags=["Product"]
    )
    def sub_category_list(self, request, pk):
        category = ProductCategory.objects.filter(id=pk).first()
        if not category:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ProductCategorySerializer(category, context={"request": request})
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

    # TODO: need to add filter to this function
    @swagger_auto_schema(
        operation_summary="Product item detail and Products list",
        operation_description="Product item detail and Products list",
        responses={200: ProductItemCategorySerializer()},
        tags=["Product"]
    )
    def categories_product_list(self, request, pk):
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
        product = Product.objects.filter(id=pk).first()
        if not product:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ProductSerializer(product, context={"request": request})
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

        page = serializer.validated_data.get('page')
        page_size = serializer.validated_data.get('page_size')
        q = serializer.validated_data.get('q')
        price_from = serializer.validated_data.get('price_from', 0)
        price_to = serializer.validated_data.get('price_to', 0)

        filters = Q()
        if q:
            pass
        if price_from or price_to:
            filters &= Q(price__gte=price_from)
            filters &= Q(price__lte=price_to)

        products = Product.objects.filter(filters)
        return Response(data={"result": get_products_paginator(response_data=products, page=page, page_size=page_size,
                                                               context={"request": request}), "ok": True},
                        status=status.HTTP_200_OK)


# TODO: finish the comment logic
class CommentViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Write comment to product, pk receive product id",
        operation_description="Write comment to product, pk receive product id",
        request_body=CommentSerializer(),
        responses={201: CommentSerializer()},
        tags=["Product"]
    )
    def comment_create(self, request, pk):
        product = Product.objects.filter(id=pk).first()
        if not product:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        comment = Comment.objects.filter(customer_id=request.user.id).first()
        if not comment:
            pass

        data = request.data
        data["product"] = pk
        serializer = CommentSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_201_CREATED)


class BrandViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Brands list",
        operation_description="Brands list",
        responses={200: BrandSerializer(many=True)},
        tags=["Brand"]
    )
    def brand_list(self, request):
        brands = Brand.objects.filter(is_visible=True)
        serializer = BrandSerializer(brands, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

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

    @swagger_auto_schema(
        operation_summary="Brand products, pk receive brand id",
        operation_description="Brand products, pk receive brand id",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
        ],
        responses={200: ProductSerializer(many=True)},
        tags=["Brand"]
    )
    def brand_products(self, request, pk):
        params = request.query_params
        param_serializer = PaginationSerializer(data=params)
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        products = Product.objects.filter(brand_id=pk)
        return Response(data={
            "result": get_products_paginator(response_data=products, page=param_serializer.validated_data.get("page"),
                                             page_size=param_serializer.validated_data.get("page_size"),
                                             context={"request": request}), "ok": True},
            status=status.HTTP_200_OK)

class SaleViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Sale products list",
        operation_description="Sale products list",
        responses={200: SaleSerializer()},
        tags=["Sale"]
    )
    def sale_products(self, request):
        sale = Sale.objects.filter(is_visible=True).prefetch_related("products").order_by("-created_at").first()
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




