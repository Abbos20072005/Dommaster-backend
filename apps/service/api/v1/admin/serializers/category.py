from rest_framework import serializers
from apps.service.models import ProductCategory, ProductSubCategory, ProductItemCategory
from utils.admin_serializers import RelationSerializer


class ProductCategoryShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ("id", "name")


class ProductSubCategoryShortSerializer(serializers.ModelSerializer):
    product_category = ProductCategoryShortSerializer(read_only=True)

    class Meta:
        model = ProductSubCategory
        fields = ("id", "name", "product_category")


class ProductItemCategorySerializer(RelationSerializer):
    product_sub_category = ProductSubCategoryShortSerializer(read_only=True)

    class Meta:
        model = ProductItemCategory
        fields = ("id", "name", "product_sub_category")


class CategoryParentSerializer(RelationSerializer):
    class Meta:
        model = ProductCategory
        fields = ("id", "name")


class SubCategoryParentSerializer(RelationSerializer):
    product_category = ProductCategoryShortSerializer(read_only=True)

    class Meta:
        model = ProductSubCategory
        fields = ("id", "name", "product_category")


# uz + ru are required, ru is the default (fallback) language
NAME_REQUIRED = {"required": True, "allow_null": False, "allow_blank": False}
NAME_KWARGS = {"name_uz": NAME_REQUIRED, "name_ru": NAME_REQUIRED}
NAME_FIELDS = ("name", "name_uz", "name_ru", "name_en")
SEO_FIELDS = ("meta_title_uz", "meta_title_ru", "meta_title_en", "meta_description_uz", "meta_description_ru",
              "meta_description_en")
VISIBILITY_FIELDS = ("show_on_site", "show_in_app", "is_active")
COUNT_FIELDS = ("products_count", "filters_count")


class CategoryBaseSerializer(serializers.ModelSerializer):
    # `slug` is optional: left out / empty -> generated from the name (model `save`)
    products_count = serializers.IntegerField(read_only=True, default=0)
    filters_count = serializers.IntegerField(read_only=True, default=0, help_text="Distinct filterable attributes")

    def validate_code(self, value):
        # unique column: store empty codes as NULL
        return value or None


class ProductCategorySerializer(CategoryBaseSerializer):
    children_count = serializers.IntegerField(read_only=True, default=0, help_text="Sub categories")

    class Meta:
        model = ProductCategory
        fields = ("id", *NAME_FIELDS, "slug", "code", "icon", "image", "position", *SEO_FIELDS, *VISIBILITY_FIELDS,
                  "children_count", *COUNT_FIELDS, "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = NAME_KWARGS


class ProductSubCategoryAdminSerializer(CategoryBaseSerializer):
    product_category = CategoryParentSerializer()
    children_count = serializers.IntegerField(read_only=True, default=0, help_text="Item categories")

    class Meta:
        model = ProductSubCategory
        fields = ("id", *NAME_FIELDS, "slug", "code", "product_category", "image", "position", *SEO_FIELDS,
                  *VISIBILITY_FIELDS, "children_count", *COUNT_FIELDS, "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = NAME_KWARGS


class ProductItemCategoryAdminSerializer(CategoryBaseSerializer):
    product_sub_category = SubCategoryParentSerializer()

    class Meta:
        model = ProductItemCategory
        fields = ("id", *NAME_FIELDS, "slug", "code", "product_sub_category", "image", "position", *SEO_FIELDS,
                  *VISIBILITY_FIELDS, *COUNT_FIELDS, "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = NAME_KWARGS


class CategoryReorderSerializer(serializers.Serializer):
    """Drag & drop: `ids` in the new order, list index becomes `position` (model comes from the view)."""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate_ids(self, ids):
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Duplicate ids.")
        model = self.context["view"].get_queryset().model
        missing = set(ids) - set(model.objects.filter(id__in=ids).values_list("id", flat=True))
        if missing:
            raise serializers.ValidationError(f"Not found: {sorted(missing)}")
        return ids

    def save(self, **kwargs):
        model = self.context["view"].get_queryset().model
        model.objects.bulk_update(
            [model(id=pk, position=position) for position, pk in enumerate(self.validated_data["ids"], start=1)],
            ["position"],
        )
