from django.db.models import Max
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.utils import html
from apps.base.models import Banner
from apps.service.models import Brand, Product, ProductBadge, ProductCategory, ProductItemCategory,     ProductSubCategory

# models a banner may point to; key = ContentType.model (same value the client gets in `content_type_info.model`)
BANNER_TARGET_MODELS = {
    model._meta.model_name: model
    for model in (Product, ProductCategory, ProductSubCategory, ProductItemCategory, Brand, ProductBadge)
}
# link types that lead to an object -> models `target` may be
LINK_TYPE_TARGET_MODELS = {
    Banner.CATEGORY: (ProductCategory, ProductSubCategory, ProductItemCategory),
    Banner.PRODUCT: (Product,),
    Banner.BADGE: (ProductBadge,),
    Banner.BRAND: (Brand,),
}
LINK_FIELDS = {"link_type", "content_object", "page", "link"}
CHANNEL_FIELDS = ("show_on_site", "show_on_ios", "show_on_android")


class BannerTargetSerializer(serializers.Serializer):
    """Banner's generic relation (`content_type` + `object_id`) as one object:
    renders `{"model", "id", "name"}`, on write resolves `{"model": "product", "id": 5}` to the instance."""
    model = serializers.ChoiceField(choices=list(BANNER_TARGET_MODELS))
    id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(read_only=True)

    def get_value(self, dictionary):
        # multipart/form-data: `target.model` + `target.id` set it, an empty `target=` clears it
        if html.is_html_input(dictionary) and dictionary.get(self.field_name) == "":
            return None
        return super().get_value(dictionary)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        model = BANNER_TARGET_MODELS[attrs["model"]]
        try:
            return model.objects.get(pk=attrs["id"])
        except model.DoesNotExist:
            raise serializers.ValidationError({"id": f"Object with id={attrs['id']} does not exist."})

    def to_representation(self, instance):
        return {"model": instance._meta.model_name, "id": instance.pk, "name": str(instance)}


class BannerSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)
    status = serializers.ChoiceField(choices=Banner.STATUS_CHOICES, read_only=True)
    target = BannerTargetSerializer(source="content_object", required=False, allow_null=True)

    class Meta:
        model = Banner
        fields = ("id", "code", "title", "title_uz", "title_ru", "title_en", "desktop_image", "mobile_image",
                  "placement", "show_on_site", "show_on_ios", "show_on_android", "link_type", "target", "page", "link",
                  "starts_at", "ends_at", "position", "is_visible", "status", "created_at", "updated_at")
        read_only_fields = ("title", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "title_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "link_type": {"required": True},
            "starts_at": {"required": True},
        }

    def get_fields(self):
        fields = super().get_fields()
        # multipart/form-data: a missing checkbox means "not sent" (model default), not False
        for name in ("is_visible", *CHANNEL_FIELDS):
            fields[name].default_empty_html = empty
        return fields

    def validate(self, attrs):
        def current(name, default=None):
            # the sent value, else the stored one (PATCH)
            if name in attrs:
                return attrs[name]
            return getattr(self.instance, name) if self.instance else default

        if not any(current(name, True) for name in CHANNEL_FIELDS):
            raise serializers.ValidationError({"show_on_site": "Select at least one channel."})
        ends_at = current("ends_at")
        if ends_at and ends_at <= current("starts_at"):
            raise serializers.ValidationError({"ends_at": "Must be later than starts_at."})
        if not self.instance or LINK_FIELDS & attrs.keys():
            attrs.update(self.link_values(current))
        return attrs

    @staticmethod
    def link_values(current):
        """Checks the value `link_type` needs and returns the other link fields emptied."""
        link_type = current("link_type")
        target_models = LINK_TYPE_TARGET_MODELS.get(link_type)
        if target_models:
            if not isinstance(current("content_object"), target_models):
                names = ", ".join(model._meta.model_name for model in target_models)
                raise serializers.ValidationError({"target": f"link_type={link_type} needs a target: {names}."})
            return {"page": "", "link": ""}
        if link_type == Banner.PAGE:
            if not (current("page") or "").startswith("/"):
                raise serializers.ValidationError({"page": "link_type=page needs a path starting with '/'."})
            return {"content_object": None, "link": ""}
        if not current("link"):
            raise serializers.ValidationError({"link": "link_type=url needs a link."})
        return {"content_object": None, "page": ""}

    def create(self, validated_data):
        if "position" not in validated_data:
            # new banner goes to the end of its placement
            last = Banner.objects.filter(placement=validated_data.get("placement", Banner.SITE_HOME))                 .aggregate(last=Max("position"))["last"]
            validated_data["position"] = (last or 0) + 1
        return super().create(validated_data)

    def update(self, instance, validated_data):
        old_images = [(name, getattr(instance, name)) for name in ("desktop_image", "mobile_image")
                      if name in validated_data]
        instance = super().update(instance, validated_data)
        # replaced / cleared images: remove the old files
        for name, old in old_images:
            if old and old.name != getattr(instance, name).name:
                old.storage.delete(old.name)
        return instance


class BannerStatsSerializer(serializers.Serializer):
    active = serializers.IntegerField(help_text="Shown right now")
    scheduled = serializers.IntegerField(help_text="starts_at is in the future")
    expired = serializers.IntegerField(help_text="ends_at has passed, not archived yet")
    archived = serializers.IntegerField(help_text="is_visible=false")
    external = serializers.IntegerField(help_text="Not archived banners with link_type=url")
    site_home = serializers.IntegerField(help_text="Not archived banners of the placement")
    app_home = serializers.IntegerField(help_text="Not archived banners of the placement")
    catalog = serializers.IntegerField(help_text="Not archived banners of the placement")
