from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .serializers import ProductCategorySerializer, ProductCategoryListSerializer, ProductSubCategorySerializer, \
    ProductItemCategorySerializer, ProductSerializer
from .models import ProductCategory, ProductSubCategory, ProductItemCategory, Product
from rest_framework import status


class ProductViewSet(ViewSet):
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

    #TODO: need to add filter to this function
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
