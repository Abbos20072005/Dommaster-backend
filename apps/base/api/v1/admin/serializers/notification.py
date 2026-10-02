from django.utils import timezone
from rest_framework import serializers
from apps.base.models import Notification

# ru is the default (fallback) language
REQUIRED = {"required": True, "allow_null": False, "allow_blank": False}


class NotificationSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=Notification.STATUS_CHOICES, read_only=True)
    reads_count = serializers.IntegerField(read_only=True, default=0, help_text="Customers who opened it")

    class Meta:
        model = Notification
        fields = ("id", "title", "title_uz", "title_ru", "title_en", "description", "description_uz",
                  "description_ru", "description_en", "deeplink", "publish_at", "is_active", "status",
                  "reads_count", "created_at", "updated_at")
        read_only_fields = ("title", "description", "created_at", "updated_at")
        extra_kwargs = {"title_ru": REQUIRED, "description_ru": REQUIRED}

    def update(self, instance, validated_data):
        # a draft published without a new time goes out now, not at its old (past) `publish_at`
        if validated_data.get("is_active") and not instance.is_active and "publish_at" not in validated_data:
            validated_data["publish_at"] = max(instance.publish_at, timezone.now())
        return super().update(instance, validated_data)


class NotificationStatsSerializer(serializers.Serializer):
    published = serializers.IntegerField(help_text="Visible to customers right now")
    scheduled = serializers.IntegerField(help_text="publish_at is in the future")
    draft = serializers.IntegerField(help_text="is_active=false")
    published_30d = serializers.IntegerField(help_text="Published in the last 30 days")
    reads_30d = serializers.IntegerField(help_text="Opens (customer x notification) in the last 30 days")
