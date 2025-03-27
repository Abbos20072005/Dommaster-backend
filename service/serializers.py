from rest_framework import serializers
from .models import Product, ProductCategory, ProductItemCategory, ProductSubCategory, ProductImage, Comment, \
    CommentReply, Order, OrderItem


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "product_item_category", "code", "name", "price")


class ProductCategoryListSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=True)
    image = serializers.ImageField(required=True)


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


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "product", "image")


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "product", "commentator_name", "product_rating", "comment")


class CommentReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentReply
        fields = ("id", "comment", "defendant_name", "reply")


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
