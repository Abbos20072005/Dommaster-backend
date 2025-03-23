from rest_framework import serializers
from .models import Product, ProductCategory, ProductItemCategory, ProductSubCategory, ProductImage, Comment, CommentReply

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "product_item_category", "code", "name", "price")

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ("id", "name", "image")

class ProductItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductItemCategory
        fields = ("id", "product_sub_category", "name")

class ProductSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSubCategory
        fields = ("id", "product_category", "name")

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