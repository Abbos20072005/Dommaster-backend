from rest_framework import serializers
from .models import Product, ProductCategory, ProductItemCategory, ProductSubCategory, ProductImage

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', "product_item_category", "code", "name", "price"]

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', "name", "image"]

class ProductItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductItemCategory
        fields = ['id', 'product_sub_category', "name"]

class ProductSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSubCategory
        fields = ['id', "product_category", "name"]

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', "product", "image"]