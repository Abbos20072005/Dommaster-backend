from rest_framework import serializers
from .models import Banner, Chat


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "short_description",
            "image",
            "link"
        )


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = (
            "id",
            "customer",
            "message",
            "is_answer",
            "is_checked"
        )


class ChatMessageCreateSerializer(serializers.Serializer):
    customer = serializers.IntegerField(required=True)
    message = serializers.CharField(required=True)
