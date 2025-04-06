from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .serializers import ProductCategorySerializer, ProductCategoryListSerializer, ProductSubCategorySerializer, \
    ProductItemCategorySerializer, ProductSerializer, CommentSerializer
from .models import ProductCategory, ProductSubCategory, ProductItemCategory, Product, Comment
from rest_framework import status


# TODO: need to add comment create and check if user already write comment to this project one user could write only one comment.
#TODO: add the most salled products list api
#TODO: add the new products list


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

#TODO: finish the comment logic
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