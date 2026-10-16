from rest_framework import serializers
from apps.service import filter_pages
from apps.service.models import FilterPage
from .category import ProductItemCategorySerializer
from .product import ProductBrandSerializer


class FilterPageSerializer(serializers.ModelSerializer):
    item_category = ProductItemCategorySerializer()
    brand = ProductBrandSerializer(required=False, allow_null=True)
    filters = serializers.JSONField(required=False)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = FilterPage
        fields = (
            "id", "slug", "item_category", "brand", "filters",
            "keyword_uz", "keyword_ru", "search_volume",
            "title_uz", "title_ru", "meta_title_uz", "meta_title_ru",
            "meta_description_uz", "meta_description_ru", "text_uz", "text_ru",
            "is_active", "is_open", "products_count", "counted_at", "created_at", "updated_at",
        )
        read_only_fields = ("products_count", "counted_at", "created_at", "updated_at")
        extra_kwargs = {"title_ru": {"required": True, "allow_blank": False, "allow_null": False}}

    def validate(self, attrs):
        instance = self.instance
        item_category = attrs.get("item_category", instance.item_category if instance else None)
        brand = attrs["brand"] if "brand" in attrs else (instance.brand if instance else None)
        try:
            # re-checked against the item category when only the category changes
            filters = filter_pages.clean_filters(
                item_category.id, attrs.get("filters", instance.filters if instance else {}))
        except filter_pages.FilterPageError as error:
            raise serializers.ValidationError({"filters": str(error)})
        if not brand and not filters:
            raise serializers.ValidationError(
                {"filters": "A brand or at least one filter is required, otherwise it is the item category page."})

        duplicates = FilterPage.objects.filter(
            combination_hash=filter_pages.combination_hash(item_category.id, brand.id if brand else None, filters))
        if instance:
            duplicates = duplicates.exclude(pk=instance.pk)
        duplicate = duplicates.first()
        if duplicate:
            raise serializers.ValidationError({"filters": f"Page \"{duplicate.slug}\" has the same combination."})
        attrs["filters"] = filters
        return attrs

    def create(self, validated_data):
        page = super().create(validated_data)
        filter_pages.refresh_counts([page])
        return page

    def update(self, instance, validated_data):
        page = super().update(instance, validated_data)
        filter_pages.refresh_counts([page])
        return page
