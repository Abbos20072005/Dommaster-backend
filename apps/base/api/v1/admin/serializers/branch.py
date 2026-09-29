from rest_framework import serializers
from apps.base.models import MarketBranch


class MarketBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketBranch
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "location_name", "location_name_uz",
                  "location_name_ru", "location_name_en", "address", "branch_type", "latitude", "longitude",
                  "working_hours", "description_uz", "description_ru", "description_en", "phone_number", "image",
                  "is_active", "position", "code", "created_at", "updated_at")
        read_only_fields = ("name", "location_name", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "latitude": {"min_value": -90, "max_value": 90},
            "longitude": {"min_value": -180, "max_value": 180},
        }

    def validate_code(self, value):
        # unique column: store empty codes as NULL
        return value or None
