import math
from typing import Optional
from django.db import transaction
from rest_framework import serializers
from apps.service.models import Product, Brand, ProductModel, ProductBadge, ProductImage, ProductAttribute, \
    ProductAttributeValue, RelatedProduct, AlternativeProduct, CrossSellProduct, ProductModeration
from apps.service.moderation import on_publish_status_change
from apps.service.product_filters import clear_category_filter_cache
from utils.admin_serializers import RelationSerializer
from .attribute import AttributeShortSerializer
from .category import ProductItemCategorySerializer


class ProductBrandSerializer(RelationSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name")


class ProductModelShortSerializer(RelationSerializer):
    class Meta:
        model = ProductModel
        fields = ("id", "name")


class ProductBadgeShortSerializer(RelationSerializer):
    class Meta:
        model = ProductBadge
        fields = ("id", "name", "kind", "color")


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "position", "created_at")
        read_only_fields = ("position",)


class ProductImageReorderSerializer(serializers.Serializer):
    """`ids` = the product's images in the new order (list index becomes `position`), the first one is the main image."""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate_ids(self, ids):
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Duplicate ids.")
        existing = [image.id for image in self.context["product"].product_image.all()]
        missing = set(ids) - set(existing)
        if missing:
            raise serializers.ValidationError(f"Not found: {sorted(missing)}")
        # images that were not sent keep their order after the sent ones
        return ids + [pk for pk in existing if pk not in ids]

    def save(self, **kwargs):
        ProductImage.objects.bulk_update(
            [ProductImage(id=pk, position=position) for position, pk in enumerate(self.validated_data["ids"], start=1)],
            ["position"],
        )


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    # by the attribute's value type: number -> "2.5", boolean -> "true" / "false" (same in both languages),
    # list -> value_uz / value_ru of one of the attribute's options, text -> free text
    attribute = AttributeShortSerializer()

    class Meta:
        model = ProductAttributeValue
        fields = ("id", "attribute", "value_uz", "value_ru")
        extra_kwargs = {
            "value_uz": {"required": True, "allow_null": False, "allow_blank": False},
            "value_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }

    def validate(self, attrs):
        attribute, value_uz, value_ru = attrs["attribute"], attrs["value_uz"], attrs["value_ru"]
        if attribute.value_type == ProductAttribute.LIST:
            if not attribute.options.filter(value_uz=value_uz, value_ru=value_ru).exists():
                raise serializers.ValidationError({"value_ru": "Must be one of the attribute's options."})
        elif attribute.value_type in (ProductAttribute.NUMBER, ProductAttribute.BOOLEAN):
            if value_uz != value_ru:
                raise serializers.ValidationError(
                    {"value_uz": f"Must be the same as value_ru for the {attribute.value_type} type."})
            if attribute.value_type == ProductAttribute.BOOLEAN and value_ru not in ("true", "false"):
                raise serializers.ValidationError({"value_ru": '"true" or "false" is required.'})
            if attribute.value_type == ProductAttribute.NUMBER and not self._is_number(value_ru):
                raise serializers.ValidationError({"value_ru": 'A number is required, e.g. "2.5".'})
        return attrs

    @staticmethod
    def _is_number(value):
        try:
            return math.isfinite(float(value))
        except ValueError:
            return False


class ProductCharacteristicSerializer(serializers.ModelSerializer):
    """Deprecated `characteristics` of a product, kept read-only until the admin panel moves to `attribute_values`:
    the same attribute values in the shape of the old free-form characteristics."""
    name_uz = serializers.CharField(source="attribute.name_uz")
    name_ru = serializers.CharField(source="attribute.name_ru")
    unit_uz = serializers.CharField(source="attribute.unit")
    unit_ru = serializers.CharField(source="attribute.unit")

    class Meta:
        model = ProductAttributeValue
        fields = ("id", "name_uz", "name_ru", "value_uz", "value_ru",
                  "unit_uz", "unit_ru")


class LinkedProductListSerializer(serializers.ListSerializer):
    def to_representation(self, products):
        return super().to_representation(products.prefetch_related("product_image"))


class LinkedProductSerializer(RelationSerializer):
    """A product linked to another one (related / alternative / cross-sell)."""
    image = serializers.SerializerMethodField(help_text="The main image")

    class Meta:
        model = Product
        fields = ("id", "name", "image", "product_code", "articul_code", "price", "discount_price", "quantity",
                  "is_active")
        list_serializer_class = LinkedProductListSerializer

    def get_image(self, product) -> Optional[str]:
        images = product.product_image.all()
        return ProductImageSerializer(images[0], context=self.context).data["image"] if images else None


# product field -> model of its links
LINK_FIELDS = {
    "related_products": RelatedProduct,
    "alternative_products": AlternativeProduct,
    "cross_sell_products": CrossSellProduct,
}
MAX_LINKED_PRODUCTS = 20


class ProductListSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(read_only=True)
    product_model = ProductModelShortSerializer(read_only=True)
    badges = ProductBadgeShortSerializer(many=True, read_only=True)
    product_item_category = ProductItemCategorySerializer(read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "images", "product_code", "articul_code", "barcode", "brand", "product_model", "badges",
                  "product_item_category", "price", "discount_price", "discount", "unit", "quantity", "rating", "comments_quantity",
                  "is_active", "erp_active", "publish_status", "purchasable", "on_order", "created_at", "updated_at")


class ProductLastModerationSerializer(serializers.ModelSerializer):
    reviewed_by = serializers.CharField(source="reviewed_by.staff_profile.full_name", read_only=True, allow_null=True)

    class Meta:
        model = ProductModeration
        fields = ("id", "status", "submitted_at", "reviewed_by", "reviewed_at", "reason")


class ProductSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(required=False, allow_null=True)
    # a model of the product's brand (product-models/?brand=); changing the brand without it drops the model
    product_model = ProductModelShortSerializer(required=False, allow_null=True)
    # the sent list replaces the product's manual badges; auto badges are managed by their rules (ignored here)
    badges = ProductBadgeShortSerializer(many=True, required=False)
    product_item_category = ProductItemCategorySerializer(required=False, allow_null=True)
    # the product's characteristics: values of the item category's attributes (item-categories/{id}/attributes/);
    # the sent list replaces all
    attribute_values = ProductAttributeValueSerializer(many=True, required=False)
    # deprecated, read-only (a sent list is ignored): `attribute_values` in the old shape, for the old product form
    characteristics = ProductCharacteristicSerializer(source="attribute_values", many=True, read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)
    # products linked by hand, one-way; the sent list replaces the links of its kind, list order = position
    related_products = LinkedProductSerializer(many=True, required=False, max_length=MAX_LINKED_PRODUCTS)
    alternative_products = LinkedProductSerializer(many=True, required=False, max_length=MAX_LINKED_PRODUCTS)
    cross_sell_products = LinkedProductSerializer(many=True, required=False, max_length=MAX_LINKED_PRODUCTS)
    # publish_status=review puts the product into the moderation queue (moderation/); the latest submission
    last_moderation = serializers.SerializerMethodField(allow_null=True)

    class Meta:
        model = Product
        fields = ("id", "name", "name_uz", "name_ru", "short_description_uz", "short_description_ru",
                  "description_uz", "description_ru",
                  "brand", "product_model", "badges", "product_item_category", "price", "discount_price", "discount",
                  "unit", "quantity",
                  "is_active", "erp_active", "publish_status", "purchasable", "on_order", "product_code", "articul_code", "barcode", "weight", "length", "width", "height",
                  "rating", "comments_quantity", "questions_quantity", "characteristics",
                  "attribute_values", "images", "related_products", "alternative_products", "cross_sell_products",
                  "last_moderation", "created_at", "updated_at")
        read_only_fields = ("name", "rating", "comments_quantity", "questions_quantity", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "description_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "price": {"min_value": 0},
            "discount_price": {"min_value": 0},
            "discount": {"min_value": 0, "max_value": 100},
            "quantity": {"min_value": 0},
        }

    def get_last_moderation(self, product) -> ProductLastModerationSerializer:
        row = product.moderations.select_related("reviewed_by__staff_profile").first()
        return ProductLastModerationSerializer(row).data if row else None

    def _user(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def validate_product_code(self, value):
        # unique column: store empty codes as NULL
        return value or None

    def validate(self, attrs):
        price = attrs.get("price", self.instance.price if self.instance else 0.0)
        discount_price = attrs.get("discount_price", self.instance.discount_price if self.instance else None)
        if discount_price is not None and discount_price > price:
            raise serializers.ValidationError({"discount_price": "Must not be greater than price."})

        brand = attrs.get("brand", self.instance.brand if self.instance else None)
        if "product_model" in attrs:
            if attrs["product_model"] and attrs["product_model"].brand != brand:
                raise serializers.ValidationError({"product_model": "Model belongs to another brand."})
        elif self.instance and self.instance.product_model and self.instance.product_model.brand != brand:
            # the brand changed: drop the model of the old one
            attrs["product_model"] = None

        attribute_values = attrs.get("attribute_values")
        if attribute_values:
            category = attrs.get("product_item_category",
                                 self.instance.product_item_category if self.instance else None)
            allowed = set(category.attributes.values_list("id", flat=True)) if category else set()
            ids = [item["attribute"].pk for item in attribute_values]
            if len(ids) != len(set(ids)):
                raise serializers.ValidationError({"attribute_values": "Attributes must be unique."})
            foreign = sorted(set(ids) - allowed)
            if foreign:
                raise serializers.ValidationError(
                    {"attribute_values": f"Attributes {foreign} are not attached to the product's item category."})

        for field in LINK_FIELDS:
            ids = [product.pk for product in attrs.get(field) or ()]
            if len(ids) != len(set(ids)):
                raise serializers.ValidationError({field: "Products must be unique."})
            if self.instance and self.instance.pk in ids:
                raise serializers.ValidationError({field: "A product can't be linked to itself."})
        return attrs

    @staticmethod
    def _set_attribute_values(product, attribute_values):
        product.attribute_values.all().delete()
        # bulk_create skips save(): value_number is set here
        ProductAttributeValue.objects.bulk_create(
            ProductAttributeValue(
                product=product, value_number=ProductAttributeValue.number_of(item["attribute"], item["value_ru"]),
                **item,
            ) for item in attribute_values
        )

    @staticmethod
    def _set_badges(product, badges):
        manual = [badge for badge in badges if badge.kind == ProductBadge.MANUAL]
        product.badges.set([*manual, *product.badges.filter(kind=ProductBadge.AUTO)])

    @staticmethod
    def _set_links(product, links):
        # links: {link model: products}, only the sent lists
        for model, products in links.items():
            model.objects.filter(product=product).delete()
            model.objects.bulk_create(
                model(product=product, linked_product=linked, position=position)
                for position, linked in enumerate(products, start=1)
            )

    @staticmethod
    def _pop_links(validated_data):
        return {model: validated_data.pop(field) for field, model in LINK_FIELDS.items() if field in validated_data}

    @transaction.atomic
    def create(self, validated_data):
        attribute_values = validated_data.pop("attribute_values", [])
        badges = validated_data.pop("badges", [])
        links = self._pop_links(validated_data)
        product = super().create(validated_data)
        on_publish_status_change(product, None, self._user())
        self._set_attribute_values(product, attribute_values)
        self._set_badges(product, badges)
        self._set_links(product, links)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        attribute_values = validated_data.pop("attribute_values", None)
        badges = validated_data.pop("badges", None)
        links = self._pop_links(validated_data)
        old_category_id = instance.product_item_category_id
        old_publish_status = instance.publish_status
        product = super().update(instance, validated_data)
        on_publish_status_change(product, old_publish_status, self._user())
        # the product left its old category: the filters of that one change too (the new one is cleared on save)
        clear_category_filter_cache(old_category_id)
        self._set_links(product, links)
        if badges is not None:
            self._set_badges(product, badges)
        if attribute_values is not None:
            self._set_attribute_values(product, attribute_values)
        elif product.product_item_category_id != old_category_id:
            # drop the values of attributes the new category doesn't have
            stale = product.attribute_values.all()
            if product.product_item_category_id:
                stale = stale.exclude(attribute__category_links__item_category_id=product.product_item_category_id)
            stale.delete()
        return product


class ProductStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()
    out_of_stock = serializers.IntegerField(help_text="quantity <= 0")
    discounted = serializers.IntegerField(help_text="Has discount price")
