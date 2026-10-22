from rest_framework import serializers
from apps.base.models import Banner, Chat, LoyaltyCard, AboutUs, Messages, Promocodes, News, Articles, Reviews, Video, DeleteButton, \
    BaseInformation, MarketBranch, Notification, BRANCH_TYPE_CHOICES
from apps.base.api.v1.admin.serializers.branch import ScheduleDaySerializer
from apps.base.stores import localized_snapshot, open_state
from apps.service.attributes import request_language, translated
from config import settings


class DeleteButtonSerializer(serializers.Serializer):
    is_deleted = serializers.BooleanField()


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


class NotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    # annotated by the view
    is_read = serializers.BooleanField(read_only=True)
    content_type_info = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "description",
            "image",
            "deeplink",
            "link_type",
            "page",
            "content_type_info",
            "is_read",
            "publish_at"
        )

    def get_content_type_info(self, obj):
        # the same shape as in the banners
        if obj.content_object:
            return {
                "model": obj.content_type.model,
                "id": obj.object_id
            }
        return None

    def _translated(self, obj, field) -> str:
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        # only ru is required in the admin API -> fall back to it
        return getattr(obj, f'{field}_{language}') or getattr(obj, f'{field}_ru') or ""

    def get_title(self, obj) -> str:
        return self._translated(obj, "title")

    def get_description(self, obj) -> str:
        return self._translated(obj, "description")


class NotificationListParamsSerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=10, min_value=1)
    is_read = serializers.BooleanField(required=False, allow_null=True, default=None)


class NotificationUnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


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
            "placement",
            "link_type",
            "link",
            "page",
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


class BaseInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseInformation
        fields = (
            "id",
            "phone_number",
            "additional_phone_number",
            "email",
            "address",
            "working_hours",
            "telegram",
            "instagram",
            "facebook",
            "youtube",
            "telegram_support",
            "google_play_url",
            "app_store_url",
        )


class MarketBranchSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["name"] = serializers.CharField(source=f'name_{language}')
        self.fields["location_name"] = serializers.CharField(source=f'location_name_{language}')
        self.fields["description"] = serializers.CharField(source=f'description_{language}')

    class Meta:
        model = MarketBranch
        fields = (
            "id",
            "name",
            "location_name",
            "address",
            "branch_type",
            "latitude",
            "longitude",
            "working_hours",
            "description",
            "phone_number",
            "image",
            "position",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["branch_type"] = {
            "id": instance.branch_type,
            "name": dict(BRANCH_TYPE_CHOICES).get(instance.branch_type)
        }
        return data


class StoreNextOpenSerializer(serializers.Serializer):
    day = serializers.IntegerField(help_text="0 = Monday .. 6 = Sunday")
    time = serializers.CharField(help_text="HH:MM")
    date = serializers.DateField()


class StoreSerializer(serializers.ModelSerializer):
    """A store (`MarketBranch` of a pickup type) in the request language (an empty uz text falls back to ru);
    open state in Tashkent time."""
    name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    landmark = serializers.SerializerMethodField()
    phone = serializers.CharField(source="phone_number", allow_null=True)
    photo = serializers.ImageField(source="image", allow_null=True)
    sort_order = serializers.IntegerField(source="position")
    schedule = ScheduleDaySerializer(many=True, read_only=True, help_text="7 days, 0 = Monday .. 6 = Sunday")
    is_open_now = serializers.SerializerMethodField()
    closes_at = serializers.SerializerMethodField(help_text="HH:MM today while open, else null")
    next_open = serializers.SerializerMethodField(help_text="When it opens next while closed, else null")

    class Meta:
        model = MarketBranch
        fields = ("id", "name", "address", "landmark", "phone", "photo", "latitude", "longitude", "schedule",
                  "is_open_now", "closes_at", "next_open", "sort_order")

    def _language(self):
        return request_language(self.context.get("request"))

    def _open_state(self, obj):
        if getattr(obj, "_open_state", None) is None:
            obj._open_state = open_state(obj.schedule)
        return obj._open_state

    def get_name(self, obj) -> str:
        return translated(obj, "name", self._language())

    def get_address(self, obj) -> str:
        return translated(obj, "address", self._language()) or ""

    def get_landmark(self, obj) -> str:
        return translated(obj, "landmark", self._language()) or ""

    def get_is_open_now(self, obj) -> bool:
        return self._open_state(obj)["is_open_now"]

    def get_closes_at(self, obj) -> str | None:
        return self._open_state(obj)["closes_at"]

    def get_next_open(self, obj) -> StoreNextOpenSerializer(allow_null=True):
        return self._open_state(obj)["next_open"]


class OrderPickupStoreSerializer(serializers.Serializer):
    """The order's pickup store as it was when the order was placed (`Order.pickup_store_snapshot`)."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    landmark = serializers.CharField()
    phone = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

    def to_representation(self, instance):
        return localized_snapshot(instance, request_language(self.context.get("request")))
