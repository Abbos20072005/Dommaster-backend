from rest_framework import serializers
from .models import Banner, Chat, LoyaltyCard, AboutUs, Messages, Promocodes, News, Articles, Reviews, Video
from config import settings



class NewsSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["title"] = serializers.CharField(source=f'title_{language}')

    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "image",
            "created_at"
        )

class NewsDetailSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["title"] = serializers.CharField(source=f'title_{language}')
        self.fields["description"] = serializers.CharField(source=f'description_{language}')


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["name"] = serializers.CharField(source=f'name_{language}')

    class Meta:
        model = Video
        fields = (
            "id",
            "name",
            "url",
            "created_at"
        )

class PromocodeSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["name"] = serializers.CharField(source=f'name_{language}')

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
    promocode = serializers.CharField(max_length=15, required=False)


class BannerSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["title"] = serializers.CharField(source=f'title_{language}')

    content_type_info = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "desktop_image",
            "mobile_image",
            "link",
            "content_type_info"
        )

    def get_content_type_info(self, obj):
        if obj.content_object:
            return {
                "model": obj.content_type.model,
                "id": obj.object_id
            }
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
            "image",
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
            "image"
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["description"] = serializers.CharField(source=f'description_{language}')

    class Meta:
        model = AboutUs
        fields = (
            "id",
            "description"
        )
