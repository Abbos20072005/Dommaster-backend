from rest_framework import serializers
from apps.service.models import ProductAttribute
from .category import ProductItemCategorySerializer


class ProductAttributeSerializer(serializers.ModelSerializer):
    item_category = ProductItemCategorySerializer()

    class Meta:
        model = ProductAttribute
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "value_type", "item_category", "is_active",
                  "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        # ru is the default (fallback) language
        extra_kwargs = {"name_ru": {"required": True, "allow_null": False, "allow_blank": False}}
