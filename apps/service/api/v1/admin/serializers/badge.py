from rest_framework import serializers
from apps.service.models import ProductBadge


class ProductBadgeSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ProductBadge
        fields = ("id", "name", "name_uz", "name_ru", "is_active", "products_count",
                  "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }
