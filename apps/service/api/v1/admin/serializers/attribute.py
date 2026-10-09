from django.db import transaction
from rest_framework import serializers
from apps.service.models import ProductAttribute, ProductAttributeOption, ProductItemCategory, \
    ProductItemCategoryAttribute
from utils.admin_serializers import RelationSerializer
from .category import ProductItemCategorySerializer


class ProductAttributeOptionSerializer(serializers.ModelSerializer):
    # sent -> that option is updated, omitted -> a new option is created
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProductAttributeOption
        fields = ("id", "value_uz", "value_ru", "value_en")
        extra_kwargs = {
            "value_uz": {"required": True, "allow_null": False, "allow_blank": False},
            "value_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }


class ProductAttributeSerializer(serializers.ModelSerializer):
    # allowed values of a `list` attribute; list order = position, options left out of the list are deleted
    options = ProductAttributeOptionSerializer(many=True, required=False)
    # attached on the category side: item-categories/{id}/attributes/
    item_categories = ProductItemCategorySerializer(many=True, read_only=True)
    item_categories_count = serializers.IntegerField(read_only=True, default=0)
    products_count = serializers.IntegerField(read_only=True, default=0, help_text="Products with a value")

    class Meta:
        model = ProductAttribute
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "value_type", "unit", "options", "is_filterable",
                  "is_active", "item_categories", "item_categories_count", "products_count", "created_at",
                  "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = {
            "name_uz": {"required": True, "allow_null": False, "allow_blank": False},
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }

    def validate(self, attrs):
        instance = self.instance
        value_type = attrs.get("value_type", instance.value_type if instance else ProductAttribute.LIST)
        type_changed = bool(instance) and value_type != instance.value_type
        if type_changed and (instance.category_links.exists() or instance.product_values.exists()):
            raise serializers.ValidationError(
                {"value_type": "Attribute is used in categories or products, its value type can't be changed."})

        if value_type == ProductAttribute.NUMBER:
            if not attrs.get("unit", instance.unit if instance else ""):
                raise serializers.ValidationError({"unit": "This field is required for the number type."})
        else:
            attrs["unit"] = ""

        if value_type != ProductAttribute.LIST:
            attrs["options"] = []
        elif "options" in attrs or not instance or type_changed:
            self._validate_options(attrs.get("options") or [])
        return attrs

    def _validate_options(self, options):
        if not options:
            raise serializers.ValidationError({"options": "At least one value is required for the list type."})

        ids = [item["id"] for item in options if "id" in item]
        own_ids = set(self.instance.options.values_list("id", flat=True)) if self.instance else set()
        if len(ids) != len(set(ids)) or set(ids) - own_ids:
            raise serializers.ValidationError({"options": "Option ids must be unique and belong to this attribute."})

        # product values keep a copy of the option's text (no FK)
        if self.instance:
            used = self.instance.options.exclude(id__in=ids).filter(
                value_ru__in=self.instance.product_values.values("value_ru"))
            if used.exists():
                names = ", ".join(used.values_list("value_ru", flat=True))
                raise serializers.ValidationError({"options": f"Options used in products can't be removed: {names}."})

        for field in ("value_uz", "value_ru"):
            values = [item[field].strip().lower() for item in options]
            if len(values) != len(set(values)):
                raise serializers.ValidationError({"options": f"Values must be unique ({field})."})

    @staticmethod
    def _set_options(attribute, options):
        existing = {option.id: option for option in attribute.options.all()}
        kept = [item["id"] for item in options if "id" in item]
        attribute.options.exclude(id__in=kept).delete()
        for position, item in enumerate(options):
            option = existing.get(item.get("id")) or ProductAttributeOption(attribute=attribute)
            if option.pk and (option.value_uz, option.value_ru) != (item["value_uz"], item["value_ru"]):
                # renamed: product values keep a copy of the option's text
                attribute.product_values.filter(value_ru=option.value_ru).update(
                    value_uz=item["value_uz"], value_ru=item["value_ru"])
            for field, value in item.items():
                if field != "id":
                    setattr(option, field, value)
            option.position = position
            option.save()

    @transaction.atomic
    def create(self, validated_data):
        options = validated_data.pop("options", [])
        attribute = super().create(validated_data)
        self._set_options(attribute, options)
        return attribute

    @transaction.atomic
    def update(self, instance, validated_data):
        options = validated_data.pop("options", None)
        attribute = super().update(instance, validated_data)
        if options is not None:
            self._set_options(attribute, options)
        return attribute


class AttributeShortSerializer(RelationSerializer):
    class Meta:
        model = ProductAttribute
        fields = ("id", "name", "value_type", "unit")


class CategoryAttributeSerializer(serializers.ModelSerializer):
    """An attribute of an item category: the attribute itself (picked by `id`, the rest is read-only: everything
    the product form needs to render its input) + its settings in this category (the quick filter)."""
    id = serializers.IntegerField(source="attribute_id")
    name = serializers.CharField(source="attribute.name", read_only=True)
    value_type = serializers.CharField(source="attribute.value_type", read_only=True)
    unit = serializers.CharField(source="attribute.unit", read_only=True)
    options = ProductAttributeOptionSerializer(source="attribute.options", many=True, read_only=True)
    is_filterable = serializers.BooleanField(source="attribute.is_filterable", read_only=True)
    is_active = serializers.BooleanField(source="attribute.is_active", read_only=True)

    class Meta:
        model = ProductItemCategoryAttribute
        fields = ("id", "name", "value_type", "unit", "options", "is_filterable", "is_active",
                  "is_quick_filter", "max_quick_filters")

    def to_internal_value(self, data):
        # a bare attribute id is accepted besides {"id": ...}
        return super().to_internal_value(data if isinstance(data, dict) else {"id": data})


class ItemCategoryAttributesSerializer(serializers.ModelSerializer):
    # the whole list is replaced; list order = order of the attributes in the category
    attributes = CategoryAttributeSerializer(many=True)

    class Meta:
        model = ProductItemCategory
        fields = ("id", "attributes")

    def validate_attributes(self, value):
        ids = [item["attribute_id"] for item in value]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Attributes must be unique.")

        missing = sorted(set(ids) - set(ProductAttribute.objects.filter(pk__in=ids).values_list("pk", flat=True)))
        if missing:
            raise serializers.ValidationError(f"Attributes {missing} do not exist.")

        # detaching would orphan the values of the category's products
        used = ProductAttribute.objects.filter(
            category_links__item_category=self.instance,
            product_values__product__product_item_category=self.instance,
        ).exclude(pk__in=ids).distinct()
        if used.exists():
            names = ", ".join(used.values_list("name_ru", flat=True))
            raise serializers.ValidationError(
                f"Attributes with values in the category's products can't be detached: {names}.")
        return value

    def to_representation(self, instance):
        # through rows are ordered by position, `instance.attributes` is not
        links = instance.attribute_links.select_related("attribute").prefetch_related("attribute__options")
        return {"id": instance.pk, "attributes": CategoryAttributeSerializer(links, many=True, context=self.context).data}

    @transaction.atomic
    def update(self, instance, validated_data):
        attributes = validated_data["attributes"]
        instance.attribute_links.exclude(attribute_id__in=[item["attribute_id"] for item in attributes]).delete()
        for position, item in enumerate(attributes):
            # the quick filter settings stay as they are unless sent
            attribute_id = item.pop("attribute_id")
            ProductItemCategoryAttribute.objects.update_or_create(
                item_category=instance, attribute_id=attribute_id, defaults={**item, "position": position})
        return instance
