from django.db import transaction
from rest_framework import serializers
from apps.base.content_push import notify_new_content
from apps.base.models import Articles, News, Video

# ru is the default (fallback) language
REQUIRED = {"required": True, "allow_null": False, "allow_blank": False}


class NewsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ("id", "title", "title_uz", "title_ru", "image", "created_at", "updated_at")


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ("id", "title", "title_uz", "title_ru", "description", "description_uz",
                  "description_ru", "image", "created_at", "updated_at")
        read_only_fields = ("title", "description", "created_at", "updated_at")
        extra_kwargs = {"title_ru": REQUIRED, "description_ru": REQUIRED}

    def update(self, instance, validated_data):
        old = instance.image if "image" in validated_data else None
        instance = super().update(instance, validated_data)
        # replaced image: remove the old file
        if old and old.name != instance.image.name:
            old.storage.delete(old.name)
        return instance


class ArticlesListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Articles
        fields = ("id", "title", "short_description", "created_at", "updated_at")


class NewContentPushMixin(serializers.Serializer):
    """`send_push` (create only, default true): a notification for everybody + a push to the FCM topic
    (`apps/base/content_push.py`). Ignored on update — an edit never pushes again."""
    send_push = serializers.BooleanField(
        write_only=True, required=False, default=True,
        help_text="Create: notify every customer (in-app list + push). Ignored on update.")

    def create(self, validated_data):
        send_push = validated_data.pop("send_push", True)
        with transaction.atomic():
            instance = super().create(validated_data)
            if send_push:
                notify_new_content(instance)
        return instance

    def update(self, instance, validated_data):
        validated_data.pop("send_push", None)
        return super().update(instance, validated_data)


class ArticlesSerializer(NewContentPushMixin, serializers.ModelSerializer):
    class Meta:
        model = Articles
        fields = ("id", "title", "short_description", "description", "send_push", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class VideoSerializer(NewContentPushMixin, serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ("id", "name", "name_uz", "name_ru", "url", "send_push", "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = {"name_ru": REQUIRED}
