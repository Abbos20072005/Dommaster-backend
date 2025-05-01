from rest_framework import serializers

from service.serializers import SaleSerializer
from .models import Banner, Chat, LoyaltyCard, AboutUs, Messages, Promocodes, News, Articles, Reviews, Video
from service.models import Sale


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "image",
            "created_at"
        )

class NewsDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "description",
            "created_at"
        )

class ArticlesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Articles
        fields = (
            "id",
            "title",
            "short_description",
            "created_at"
        )

class ArticlesDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Articles
        fields = (
            "id",
            "title",
            "description",
            "created_at"
        )

class ReviewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reviews
        fields = (
            "id",
            "title",
            "short_description",
            "created_at"
        )

class ReviewsDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reviews
        fields = (
            "id",
            "title",
            "description",
            "created_at"
        )

class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = (
            "id",
            "name",
            "url",
            "created_at"
        )

class PromocodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocodes
        fields = (
            "id",
            "customer",
            "name",
            "code",
            "discount_precent",
            "expires_at"
        )


class PromocodeRequestSerializer(serializers.Serializer):
    promocode = serializers.CharField(max_length=15)


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "desktop_image",
            "mobile_image",
        )

class BannerDetailSerializer(serializers.ModelSerializer):
    content_object = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "content_object"
        )

    def get_content_object(self, obj):
        if isinstance(obj.content_object, News):
            return NewsDetailSerializer(obj.content_object).data
        elif isinstance(obj.content_object, Sale):
            return SaleSerializer(obj.content_object).data
        return None


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
