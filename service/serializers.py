from rest_framework import serializers
from .models import Product, ProductCategory, ProductItemCategory, ProductSubCategory, ProductImage, Comment, \
    Order, OrderItem, Brand, Sale, AddsBrands
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from config import settings


class SearchByNameSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)


class AddsBrandsDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddsBrands
        fields = (
            "id",
            "title",
            "description"
        )


class PaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField(
        required=False,
        default=1
    )
    page_size = serializers.IntegerField(
        required=False,
        default=10
    )

    def validate(self, attrs):
        page = attrs.get('page')
        page_size = attrs.get('page_size')
        if page < 0 or page_size < 0:
            raise CustomApiException(ErrorCodes.INVALID_INPUT, message="page or page_size is invalid")
        return super().validate(attrs)


class FilterSerializer(PaginationSerializer):
    q = serializers.CharField(required=False)
    sort_by = serializers.CharField(required=False)
    price_from = serializers.FloatField(required=False)
    price_to = serializers.FloatField(required=False)

    def validate(self, attrs):
        price_from = attrs.get("price_from")
        price_to = attrs.get("price_to")
        if price_from and price_to and price_from > price_to:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT,
                                     message="Price_from could not be more than price_to")
        return attrs


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = (
            "id",
            "name",
            "image"
        )


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            "id",
            "customer",
            "product",
            "product_rating",
            "comment"
        )

class CommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            "id",
            "product_rating",
            "comment"
        )



class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "product", "image")


class ProductSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["name"] = serializers.CharField(source=f'name_{language}')
        self.fields["description"] = serializers.CharField(source=f'description_{language}')

    comments = CommentSerializer(source="product_comment", many=True, read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "product_item_category",
            "name",
            "description",
            "price",
            "quantity",
            "images",
            "comments"
        )


class AddsBrandsSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = AddsBrands
        fields = (
            "id",
            "name",
            "brand",
            "products"
        )


class SaleSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id",
            "name",
            "discount_from",
            "discount_to",
            "products"
        )


class ProductCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name",
            "image"
        )


class BrandDetailSerializer(serializers.ModelSerializer):
    categories = ProductCategoryListSerializer(source="brand_categories", many=True, read_only=True)
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        fields = (
            "id",
            "name",
            "image",
            "categories",
            "products_count"
        )


class ProductItemCategorySerializer(serializers.ModelSerializer):
    products = ProductSerializer(source="product_item_category", many=True, read_only=True)

    class Meta:
        model = ProductItemCategory
        fields = ("id", "product_sub_category", "name", "products")


class ProductSubCategorySerializer(serializers.ModelSerializer):
    product_item_category = ProductItemCategorySerializer(source="product_sub_category", many=True, read_only=True)

    class Meta:
        model = ProductSubCategory
        fields = ("id", "product_category", "name", "product_item_category")


class ProductCategorySerializer(serializers.ModelSerializer):
    sub_category = ProductSubCategorySerializer(source="product_category", many=True, read_only=True)

    class Meta:
        model = ProductCategory
        fields = ("id", "name", "image", "sub_category")


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "id",
            "customer",
            "status",
            "total_price"
        )


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "order",
            "product",
            "quantity"
        )
