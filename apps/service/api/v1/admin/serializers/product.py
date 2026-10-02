import math
from django.db import transaction
from rest_framework import serializers
from apps.service.models import Product, Brand, ProductBadge, ProductImage, ProductCharacteristics, \
    ProductAttribute, ProductAttributeValue
from utils.admin_serializers import RelationSerializer
from .attribute import AttributeShortSerializer
from .category import ProductItemCategorySerializer


class ProductBrandSerializer(RelationSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name")


class ProductBadgeShortSerializer(RelationSerializer):
    class Meta:
        model = ProductBadge
        fields = ("id", "name", "kind", "color")


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


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    # by the attribute's value type: number -> "2.5", boolean -> "true" / "false" (same in both languages),
    # list -> value_uz / value_ru of one of the attribute's options, text -> free text
    attribute = AttributeShortSerializer()

    class Meta:
        model = ProductAttributeValue
        fields = ("id", "attribute", "value_uz", "value_ru")
        extra_kwargs = {
            "value_uz": {"required": True, "allow_null": False, "allow_blank": False},
            "value_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }

    def validate(self, attrs):
        attribute, value_uz, value_ru = attrs["attribute"], attrs["value_uz"], attrs["value_ru"]
        if attribute.value_type == ProductAttribute.LIST:
            if not attribute.options.filter(value_uz=value_uz, value_ru=value_ru).exists():
                raise serializers.ValidationError({"value_ru": "Must be one of the attribute's options."})
        elif attribute.value_type in (ProductAttribute.NUMBER, ProductAttribute.BOOLEAN):
            if value_uz != value_ru:
                raise serializers.ValidationError(
                    {"value_uz": f"Must be the same as value_ru for the {attribute.value_type} type."})
            if attribute.value_type == ProductAttribute.BOOLEAN and value_ru not in ("true", "false"):
                raise serializers.ValidationError({"value_ru": '"true" or "false" is required.'})
            if attribute.value_type == ProductAttribute.NUMBER and not self._is_number(value_ru):
                raise serializers.ValidationError({"value_ru": 'A number is required, e.g. "2.5".'})
        return attrs

    @staticmethod
    def _is_number(value):
        try:
            return math.isfinite(float(value))
        except ValueError:
            return False


class ProductListSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(read_only=True)
    badges = ProductBadgeShortSerializer(many=True, read_only=True)
    product_item_category = ProductItemCategorySerializer(read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "images", "product_code", "articul_code", "barcode", "brand", "badges",
                  "product_item_category", "price", "discount_price", "discount", "unit", "quantity", "rating", "comments_quantity",
                  "is_active", "erp_active", "publish_status", "purchasable", "created_at", "updated_at")


class ProductSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(required=False, allow_null=True)
    # the sent list replaces the product's manual badges; auto badges are managed by their rules (ignored here)
    badges = ProductBadgeShortSerializer(many=True, required=False)
    product_item_category = ProductItemCategorySerializer(required=False, allow_null=True)
    characteristics = ProductCharacteristicSerializer(source="product_characteristics", many=True, required=False)
    # values of the item category's attributes (item-categories/{id}/attributes/); the sent list replaces all
    attribute_values = ProductAttributeValueSerializer(many=True, required=False)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "short_description",
                  "description_uz", "description_ru", "description_en",
                  "brand", "badges", "product_item_category", "price", "discount_price", "discount", "unit",
                  "quantity",
                  "is_active", "erp_active", "publish_status", "purchasable", "product_code", "articul_code", "barcode", "weight", "length", "width", "height",
                  "rating", "comments_quantity", "questions_quantity", "filter_data", "characteristics",
                  "attribute_values", "images", "created_at", "updated_at")
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

        attribute_values = attrs.get("attribute_values")
        if attribute_values:
            category = attrs.get("product_item_category",
                                 self.instance.product_item_category if self.instance else None)
            allowed = set(category.attributes.values_list("id", flat=True)) if category else set()
            ids = [item["attribute"].pk for item in attribute_values]
            if len(ids) != len(set(ids)):
                raise serializers.ValidationError({"attribute_values": "Attributes must be unique."})
            foreign = sorted(set(ids) - allowed)
            if foreign:
                raise serializers.ValidationError(
                    {"attribute_values": f"Attributes {foreign} are not attached to the product's item category."})
        return attrs

    @staticmethod
    def _set_characteristics(product, characteristics):
        product.product_characteristics.all().delete()
        ProductCharacteristics.objects.bulk_create(
            ProductCharacteristics(product=product, **item) for item in characteristics
        )

    @staticmethod
    def _set_attribute_values(product, attribute_values):
        product.attribute_values.all().delete()
        ProductAttributeValue.objects.bulk_create(
            ProductAttributeValue(product=product, **item) for item in attribute_values
        )

    @staticmethod
    def _set_badges(product, badges):
        manual = [badge for badge in badges if badge.kind == ProductBadge.MANUAL]
        product.badges.set([*manual, *product.badges.filter(kind=ProductBadge.AUTO)])

    @transaction.atomic
    def create(self, validated_data):
        characteristics = validated_data.pop("product_characteristics", [])
        attribute_values = validated_data.pop("attribute_values", [])
        badges = validated_data.pop("badges", [])
        product = super().create(validated_data)
        self._set_characteristics(product, characteristics)
        self._set_attribute_values(product, attribute_values)
        self._set_badges(product, badges)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        characteristics = validated_data.pop("product_characteristics", None)
        attribute_values = validated_data.pop("attribute_values", None)
        badges = validated_data.pop("badges", None)
        old_category_id = instance.product_item_category_id
        product = super().update(instance, validated_data)
        if badges is not None:
            self._set_badges(product, badges)
        if characteristics is not None:
            self._set_characteristics(product, characteristics)
        if attribute_values is not None:
            self._set_attribute_values(product, attribute_values)
        elif product.product_item_category_id != old_category_id:
            # drop the values of attributes the new category doesn't have
            stale = product.attribute_values.all()
            if product.product_item_category_id:
                stale = stale.exclude(attribute__category_links__item_category_id=product.product_item_category_id)
            stale.delete()
        return product


class ProductStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()
    out_of_stock = serializers.IntegerField(help_text="quantity <= 0")
    discounted = serializers.IntegerField(help_text="Has discount price")
