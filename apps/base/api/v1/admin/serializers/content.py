from rest_framework import serializers
from apps.base.models import Articles, News, Video

# ru is the default (fallback) language
REQUIRED = {"required": True, "allow_null": False, "allow_blank": False}


class NewsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ("id", "title", "title_uz", "title_ru", "title_en", "image", "created_at", "updated_at")


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ("id", "title", "title_uz", "title_ru", "title_en", "description", "description_uz",
                  "description_ru", "description_en", "image", "created_at", "updated_at")
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


class ArticlesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Articles
        fields = ("id", "title", "short_description", "description", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "url", "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = {"name_ru": REQUIRED}
