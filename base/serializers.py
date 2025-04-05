from rest_framework import serializers
from .models import Banner, Chat, LoyaltyCard, AboutUs


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
            "is_answer"
        )


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = (
            "id",
            "customer",
            "message"
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