from django.utils import timezone
from rest_framework import serializers
from rest_framework.fields import empty
from apps.base.models import Articles, Banner, Notification, Video
from apps.base.notification_push import push_if_published
from apps.service.models import Product, ProductBadge, ProductCategory, ProductItemCategory, ProductSubCategory
from .banner import BannerTargetSerializer

# ru is the default (fallback) language
REQUIRED = {"required": True, "allow_null": False, "allow_blank": False}
# models a notification may lead to; key = ContentType.model (the client gets it in `content_type_info.model`)
NOTIFICATION_TARGET_MODELS = {
    model._meta.model_name: model
    for model in (ProductCategory, ProductSubCategory, ProductItemCategory, Product, ProductBadge, Banner,
                  Articles, Video)
}
# link types that lead to an object -> models `target` may be
LINK_TYPE_TARGET_MODELS = {
    Notification.CATEGORY: (ProductCategory, ProductSubCategory, ProductItemCategory),
    Notification.PRODUCT: (Product,),
    Notification.BADGE: (ProductBadge,),
    Notification.BANNER: (Banner,),
    Notification.ARTICLE: (Articles,),
    Notification.VIDEO: (Video,),
}
LINK_FIELDS = {"link_type", "content_object", "page", "deeplink"}
AUDIENCE_FIELDS = ("segment", "platform")
SCHEDULE_FIELDS = {"publish_at", "quiet_hours", "is_active"}


class NotificationTargetSerializer(BannerTargetSerializer):
    target_models = NOTIFICATION_TARGET_MODELS
    model = serializers.ChoiceField(choices=list(NOTIFICATION_TARGET_MODELS))


class NotificationSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=Notification.STATUS_CHOICES, read_only=True)
    reads_count = serializers.IntegerField(read_only=True, default=0, help_text="Customers who opened it")
    target = NotificationTargetSerializer(source="content_object", required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = ("id", "title", "title_uz", "title_ru", "description", "description_uz",
                  "description_ru", "image", "link_type", "target", "page", "deeplink",
                  "segment", "platform", "publish_at", "quiet_hours", "is_active", "status", "reads_count",
                  "push_sent_at", "push_devices", "push_to_topic", "created_at", "updated_at")
        read_only_fields = ("title", "description", "push_sent_at", "push_devices", "push_to_topic",
                            "created_at", "updated_at")
        extra_kwargs = {"title_ru": REQUIRED, "description_ru": REQUIRED}

    def get_fields(self):
        fields = super().get_fields()
        # multipart/form-data: a missing checkbox means "not sent" (model default), not False
        for name in ("is_active", "quiet_hours"):
            fields[name].default_empty_html = empty
        return fields

    def validate(self, attrs):
        def current(name, default=None):
            # the sent value, else the stored one (PATCH)
            if name in attrs:
                return attrs[name]
            return getattr(self.instance, name) if self.instance else default

        if self.instance and self.instance.push_sent_at:
            for name in AUDIENCE_FIELDS:
                if name in attrs and attrs[name] != getattr(self.instance, name):
                    raise serializers.ValidationError({name: "The push has been sent, the audience cannot change."})
        if not self.instance or LINK_FIELDS & attrs.keys():
            attrs.update(self.link_values(current))
        return attrs

    @staticmethod
    def link_values(current):
        """Checks the value `link_type` needs, empties the other link fields and builds `deeplink`."""
        link_type = current("link_type", "")
        if not link_type:
            # no typed link: `deeplink` stays free text
            return {"content_object": None, "page": ""}
        target_models = LINK_TYPE_TARGET_MODELS.get(link_type)
        if target_models:
            target = current("content_object")
            if not isinstance(target, target_models):
                names = ", ".join(model._meta.model_name for model in target_models)
                raise serializers.ValidationError({"target": f"link_type={link_type} needs a target: {names}."})
            return {"page": "", "deeplink": Notification.deeplink_of(link_type, target)}
        page = current("page") or ""
        if not page.startswith("/"):
            raise serializers.ValidationError({"page": "link_type=page needs a path starting with '/'."})
        return {"content_object": None, "deeplink": Notification.deeplink_of(link_type, page=page)}

    def create(self, validated_data):
        if validated_data.get("quiet_hours"):
            validated_data["publish_at"] = Notification.after_quiet_hours(
                validated_data.get("publish_at") or timezone.now())
        instance = super().create(validated_data)
        # a scheduled one is pushed by the periodic task when its time comes
        push_if_published(instance)
        return instance

    def update(self, instance, validated_data):
        # a draft published without a new time goes out now, not at its old (past) `publish_at`
        if validated_data.get("is_active") and not instance.is_active and "publish_at" not in validated_data:
            validated_data["publish_at"] = max(instance.publish_at, timezone.now())
        # a pushed one has gone out already: its time is history
        if not instance.push_sent_at and SCHEDULE_FIELDS & validated_data.keys() \
                and validated_data.get("quiet_hours", instance.quiet_hours):
            validated_data["publish_at"] = Notification.after_quiet_hours(
                validated_data.get("publish_at", instance.publish_at))
        old_image = instance.image if "image" in validated_data else None
        instance = super().update(instance, validated_data)
        # replaced / cleared image: remove the old file
        if old_image and old_image.name != (instance.image.name if instance.image else None):
            old_image.storage.delete(old_image.name)
        push_if_published(instance)
        return instance


class NotificationStatsSerializer(serializers.Serializer):
    published = serializers.IntegerField(help_text="Visible to customers right now")
    scheduled = serializers.IntegerField(help_text="publish_at is in the future")
    draft = serializers.IntegerField(help_text="is_active=false")
    published_30d = serializers.IntegerField(help_text="Published in the last 30 days")
    reads_30d = serializers.IntegerField(help_text="Opens (customer x notification) in the last 30 days")


class NotificationAudienceSerializer(serializers.Serializer):
    segment = serializers.ChoiceField(choices=Notification.SEGMENT_CHOICES)
    customers = serializers.IntegerField(help_text="Customers of the segment right now")
    devices = serializers.IntegerField(help_text="Their devices with a push token (platform=all)")
    devices_ios = serializers.IntegerField(help_text="platform=ios")
    devices_android = serializers.IntegerField(help_text="platform=android")
