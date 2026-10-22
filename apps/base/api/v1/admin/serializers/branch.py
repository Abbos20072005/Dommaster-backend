from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from apps.base.models import MarketBranch
from apps.base.stores import check_coordinates, clean_schedule, open_state


class ScheduleDaySerializer(serializers.Serializer):
    """Schema of one day; the schedule is validated as a whole by `stores.clean_schedule`."""
    day = serializers.IntegerField(min_value=0, max_value=6, help_text="0 = Monday .. 6 = Sunday")
    is_open = serializers.BooleanField()
    open_time = serializers.CharField(allow_null=True, help_text="HH:MM, null on a closed day")
    close_time = serializers.CharField(allow_null=True, help_text="HH:MM, after open_time; null on a closed day")


@extend_schema_field(ScheduleDaySerializer(many=True))
class ScheduleField(serializers.JSONField):
    def to_internal_value(self, data):
        try:
            return clean_schedule(super().to_internal_value(data))
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)


class MarketBranchSerializer(serializers.ModelSerializer):
    schedule = ScheduleField(required=False, help_text="7 days: [{day, is_open, open_time, close_time}]")
    is_open_now = serializers.SerializerMethodField(help_text="By the schedule, in Tashkent time")
    orders_count = serializers.IntegerField(read_only=True, default=0, help_text="Pickup orders of this branch")

    class Meta:
        model = MarketBranch
        fields = ("id", "name", "name_uz", "name_ru", "location_name", "location_name_uz",
                  "location_name_ru", "address", "address_uz", "address_ru", "landmark_uz", "landmark_ru",
                  "branch_type", "latitude", "longitude", "working_hours", "schedule", "is_open_now",
                  "description_uz", "description_ru", "phone_number", "image", "is_active", "position", "code",
                  "orders_count", "created_at", "updated_at")
        read_only_fields = ("name", "location_name", "address", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "address_uz": {"required": False, "allow_null": True, "allow_blank": True},
            "address_ru": {"required": False, "allow_null": True, "allow_blank": True},
            "landmark_uz": {"required": False, "allow_null": False, "allow_blank": True},
            "landmark_ru": {"required": False, "allow_null": False, "allow_blank": True},
            "latitude": {"min_value": -90, "max_value": 90},
            "longitude": {"min_value": -180, "max_value": 180},
        }

    def get_is_open_now(self, obj) -> bool:
        return open_state(obj.schedule)["is_open_now"]

    def validate_code(self, value):
        # unique column: store empty codes as NULL
        return value or None

    def validate(self, attrs):
        if "latitude" in attrs or "longitude" in attrs:
            errors = check_coordinates(attrs.get("latitude", getattr(self.instance, "latitude", None)),
                                       attrs.get("longitude", getattr(self.instance, "longitude", None)))
            if errors:
                raise serializers.ValidationError(errors)
        return attrs

    def update(self, instance, validated_data):
        old_image = instance.image if "image" in validated_data else None
        instance = super().update(instance, validated_data)
        if old_image and old_image.name != (instance.image.name if instance.image else None):
            old_image.storage.delete(old_image.name)
        return instance


class MarketBranchReorderSerializer(serializers.Serializer):
    """Drag & drop: `ids` in the new order, list index becomes `position`; branches not sent stay after them."""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate_ids(self, ids):
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Duplicate ids.")
        missing = set(ids) - set(MarketBranch.objects.filter(id__in=ids).values_list("id", flat=True))
        if missing:
            raise serializers.ValidationError(f"Not found: {sorted(missing)}")
        return ids

    def save(self, **kwargs):
        ids = self.validated_data["ids"]
        rest = MarketBranch.objects.exclude(id__in=ids).order_by("position", "id").values_list("id", flat=True)
        MarketBranch.objects.bulk_update(
            [MarketBranch(id=pk, position=position) for position, pk in enumerate([*ids, *rest], start=1)],
            ["position"],
        )
