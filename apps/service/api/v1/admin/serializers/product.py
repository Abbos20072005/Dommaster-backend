from django.db import transaction
from rest_framework import serializers
from apps.service.models import Product, Brand, ProductBadge, ProductImage, ProductCharacteristics
from utils.admin_serializers import RelationSerializer
from .category import ProductItemCategorySerializer


class ProductBrandSerializer(RelationSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name")


class ProductBadgeShortSerializer(RelationSerializer):
    class Meta:
        model = ProductBadge
        fields = ("id", "name")


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "created_at")


class ProductCharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCharacteristics
        fields = ("id", "name_uz", "name_ru", "name_en", "value_uz", "value_ru", "value_en",
                  "unit_uz", "unit_ru", "unit_en")
        extra_kwargs = {
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "value_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }


class ProductListSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(read_only=True)
    badge = ProductBadgeShortSerializer(read_only=True)
    product_item_category = ProductItemCategorySerializer(read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "images", "product_code", "articul_code", "barcode", "brand", "badge",
                  "product_item_category", "price", "discount_price", "discount", "unit", "quantity", "rating", "comments_quantity",
                  "is_active", "erp_active", "publish_status", "purchasable", "created_at", "updated_at")


class ProductSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(required=False, allow_null=True)
    badge = ProductBadgeShortSerializer(required=False, allow_null=True)
    product_item_category = ProductItemCategorySerializer(required=False, allow_null=True)
    characteristics = ProductCharacteristicSerializer(source="product_characteristics", many=True, required=False)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "short_description",
                  "description_uz", "description_ru", "description_en",
                  "brand", "badge", "product_item_category", "price", "discount_price", "discount", "unit",
                  "quantity",
                  "is_active", "erp_active", "publish_status", "purchasable", "product_code", "articul_code", "barcode", "weight", "length", "width", "height",
                  "rating", "comments_quantity", "questions_quantity", "filter_data", "characteristics", "images",
                  "created_at", "updated_at")
        # filter_data is built from 1C data
        read_only_fields = ("name", "rating", "comments_quantity", "questions_quantity", "filter_data",
                            "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "description_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "price": {"min_value": 0},
            "discount_price": {"min_value": 0},
            "discount": {"min_value": 0, "max_value": 100},
            "quantity": {"min_value": 0},
        }

    def validate_product_code(self, value):
        # unique column: store empty codes as NULL
        return value or None

    def validate(self, attrs):
        price = attrs.get("price", self.instance.price if self.instance else 0.0)
        discount_price = attrs.get("discount_price", self.instance.discount_price if self.instance else None)
        if discount_price is not None and discount_price > price:
            raise serializers.ValidationError({"discount_price": "Must not be greater than price."})
        return attrs

    @staticmethod
    def _set_characteristics(product, characteristics):
        product.product_characteristics.all().delete()
        ProductCharacteristics.objects.bulk_create(
            ProductCharacteristics(product=product, **item) for item in characteristics
        )

    @transaction.atomic
    def create(self, validated_data):
        characteristics = validated_data.pop("product_characteristics", [])
        product = super().create(validated_data)
        self._set_characteristics(product, characteristics)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        characteristics = validated_data.pop("product_characteristics", None)
        product = super().update(instance, validated_data)
        if characteristics is not None:
            self._set_characteristics(product, characteristics)
        return product


class ProductStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()
    out_of_stock = serializers.IntegerField(help_text="quantity <= 0")
    discounted = serializers.IntegerField(help_text="Has discount price")
