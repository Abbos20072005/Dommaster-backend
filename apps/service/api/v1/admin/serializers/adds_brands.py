from django.db import transaction
from rest_framework import serializers
from apps.service.models import AddsBrands, Product
from utils.admin_serializers import RelationSerializer
from .product import ProductBrandSerializer

# ru is the default (fallback) language
REQUIRED = {"required": True, "allow_null": False, "allow_blank": False}


class AddsBrandsProductSerializer(RelationSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "product_code", "price", "discount_price", "is_active")


class AddsBrandsListSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(read_only=True)
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AddsBrands
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "title", "title_uz", "title_ru", "title_en", "brand",
                  "products_count", "is_visible", "created_at", "updated_at")


class AddsBrandsSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(required=False, allow_null=True)
    # the sent list replaces the block's products
    products = AddsBrandsProductSerializer(many=True, allow_empty=False)

    class Meta:
        model = AddsBrands
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "title", "title_uz", "title_ru", "title_en",
                  "description", "description_uz", "description_ru", "description_en", "brand", "products",
                  "is_visible", "created_at", "updated_at")
        read_only_fields = ("name", "title", "description", "created_at", "updated_at")
        extra_kwargs = {"name_ru": REQUIRED, "title_ru": REQUIRED, "description_ru": REQUIRED}

    def validate_brand(self, value):
        # AddsBrands.brand is one-to-one
        if value and AddsBrands.objects.filter(brand=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("This brand already has an ad block.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        products = validated_data.pop("products")
        instance = super().create(validated_data)
        instance.products.set(products)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        products = validated_data.pop("products", None)
        instance = super().update(instance, validated_data)
        if products is not None:
            instance.products.set(products)
        return instance
