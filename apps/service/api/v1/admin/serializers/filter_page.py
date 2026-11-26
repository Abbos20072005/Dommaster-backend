from rest_framework import serializers
from apps.service import filter_pages
from apps.service.models import FilterPage
from .category import CategoryParentSerializer, ProductItemCategorySerializer, SubCategoryParentSerializer
from .product import ProductBrandSerializer


class FilterPageSerializer(serializers.ModelSerializer):
    # exactly one of the three catalog levels; sending any of them replaces the page's level (the others -> null)
    category = CategoryParentSerializer(required=False, allow_null=True)
    sub_category = SubCategoryParentSerializer(required=False, allow_null=True)
    item_category = ProductItemCategorySerializer(required=False, allow_null=True)
    brand = ProductBrandSerializer(required=False, allow_null=True)
    filters = serializers.JSONField(required=False)
    level = serializers.CharField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = FilterPage
        fields = (
            "id", "slug", "level", "category", "sub_category", "item_category", "brand", "filters",
            "keyword_uz", "keyword_ru", "search_volume",
            "title_uz", "title_ru", "meta_title_uz", "meta_title_ru",
            "meta_description_uz", "meta_description_ru", "text_uz", "text_ru",
            "is_active", "is_open", "products_count", "counted_at", "created_at", "updated_at",
        )
        read_only_fields = ("products_count", "counted_at", "created_at", "updated_at")
        extra_kwargs = {"title_ru": {"required": True, "allow_blank": False, "allow_null": False}}

    def validate(self, attrs):
        instance = self.instance
        if any(level in attrs for level in FilterPage.LEVELS):
            nodes = {level: attrs.get(level) for level in FilterPage.LEVELS}
        else:
            nodes = {level: getattr(instance, level) if instance else None for level in FilterPage.LEVELS}
        chosen = [level for level, node in nodes.items() if node]
        if len(chosen) != 1:
            raise serializers.ValidationError(
                {"item_category": "Exactly one of category, sub_category, item_category is required."})
        level, node = chosen[0], nodes[chosen[0]]
        brand = attrs["brand"] if "brand" in attrs else (instance.brand if instance else None)
        try:
            # re-checked against the level when only the level changes
            filters = filter_pages.clean_page(level, node.id, brand.id if brand else None,
                                              attrs.get("filters", instance.filters if instance else {}))
        except filter_pages.FilterPageError as error:
            raise serializers.ValidationError({error.field: str(error)})

        duplicates = FilterPage.objects.filter(
            combination_hash=filter_pages.combination_hash(level, node.id, brand.id if brand else None, filters))
        if instance:
            duplicates = duplicates.exclude(pk=instance.pk)
        duplicate = duplicates.first()
        if duplicate:
            raise serializers.ValidationError({"filters": f"Page \"{duplicate.slug}\" has the same combination."})
        attrs.update(nodes, filters=filters)
        return attrs

    def create(self, validated_data):
        page = super().create(validated_data)
        filter_pages.refresh_counts([page])
        return page

    def update(self, instance, validated_data):
        page = super().update(instance, validated_data)
        filter_pages.refresh_counts([page])
        return page
