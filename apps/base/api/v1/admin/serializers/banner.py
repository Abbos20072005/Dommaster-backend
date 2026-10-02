from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.utils import html
from apps.base.models import Banner
from apps.service.models import Brand, Product, ProductCategory, ProductItemCategory, ProductSubCategory

# models a banner may point to; key = ContentType.model (same value the client gets in `content_type_info.model`)
BANNER_TARGET_MODELS = {
    model._meta.model_name: model
    for model in (Product, ProductCategory, ProductSubCategory, ProductItemCategory, Brand)
}


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
    target = BannerTargetSerializer(source="content_object", required=False, allow_null=True)

    class Meta:
        model = Banner
        fields = ("id", "title", "title_uz", "title_ru", "title_en", "desktop_image", "mobile_image", "link",
                  "is_visible", "target", "created_at", "updated_at")
        read_only_fields = ("title", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "title_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }

    def get_fields(self):
        fields = super().get_fields()
        # multipart/form-data: a missing `is_visible` means "not sent" (model default), not False
        fields["is_visible"].default_empty_html = empty
        return fields

    def update(self, instance, validated_data):
        old_images = [(name, getattr(instance, name)) for name in ("desktop_image", "mobile_image")
                      if name in validated_data]
        instance = super().update(instance, validated_data)
        # replaced / cleared images: remove the old files
        for name, old in old_images:
            if old and old.name != getattr(instance, name).name:
                old.storage.delete(old.name)
        return instance
