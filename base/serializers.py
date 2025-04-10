from rest_framework import serializers
from .models import Banner, Chat, LoyaltyCard, AboutUs, Messages


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

class ChatCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = (
            "id",
            "customer"
        )

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = (
            "id",
            "chat",
            "file",
            "message",
            "is_answer",
            "created_at"
        )


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = (
            "id",
            "chat",
            "message",
            "file"
        )

class LoyaltyCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyCard
        fields = (
            "id",
            "customer",
            "full_name",
            "card_number",
            "is_active"
        )

class AboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUs
        fields = (
            "id",
            "description"
        )