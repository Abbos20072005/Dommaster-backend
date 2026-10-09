from rest_framework import serializers
from apps.service.models import Brand, PartnerBrand


class BrandSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Brand
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "description_uz", "description_ru", "description_en",
                  "country", "image", "is_visible", "show_on_home", "code", "products_count", "created_at",
                  "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }

    def validate_code(self, value):
        # unique column: store empty codes as NULL
        return value or None


class PartnerBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerBrand
        fields = ("id", "name", "is_active", "created_at", "updated_at")
