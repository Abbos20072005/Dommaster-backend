from django.db import transaction
from rest_framework import serializers
from apps.service.models import Sale, SaleProduct, Product
from utils.admin_serializers import RelationSerializer


class SaleProductSerializer(RelationSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "product_code", "price", "discount_price", "is_active")


class SaleListSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id", "name", "image", "bg_image",
            "discount_from", "discount_to",
            "is_main", "is_visible",
            "products_count",
            "created_at", "updated_at",
        )


def set_sale_products(sale, products):
    """The sale's products = `products` in this order (list index becomes `position`)."""
    links = {link.product_id: link for link in sale.product_links.all()}
    ids = [product.pk for product in products]
    SaleProduct.objects.filter(sale=sale).exclude(product_id__in=ids).delete()
    rows = []
    for position, pk in enumerate(ids, start=1):
        link = links.get(pk) or SaleProduct(sale=sale, product_id=pk)
        link.position = position
        rows.append(link)
    SaleProduct.objects.bulk_create([row for row in rows if not row.pk])
    SaleProduct.objects.bulk_update([row for row in rows if row.pk], ["position"])


class SaleSerializer(serializers.ModelSerializer):
    # list order = order of the products in the sale; the sent list replaces all
    products = SaleProductSerializer(many=True, allow_empty=True, source="ordered_products")

    class Meta:
        model = Sale
        fields = (
            "id", "name", "image", "bg_image",
            "discount_from", "discount_to",
            "is_main", "is_visible",
            "products",
            "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_products(self, products):
        ids = [product.pk for product in products]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Duplicate products.")
        return products

    def validate(self, attrs):
        is_main = attrs.get("is_main", getattr(self.instance, "is_main", False))
        if is_main:
            qs = Sale.objects.filter(is_main=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"is_main": "Faqat bitta asosiy aksiya bo'lishi mumkin."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        products = validated_data.pop("ordered_products")
        instance = super().create(validated_data)
        set_sale_products(instance, products)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        products = validated_data.pop("ordered_products", None)
        instance = super().update(instance, validated_data)
        if products is not None:
            set_sale_products(instance, products)
        return instance


class SaleProductReorderSerializer(serializers.Serializer):
    """`ids` = product ids of the sale in the new order (list index becomes `position`);
    products that were not sent keep their order after the sent ones."""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate_ids(self, ids):
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Duplicate ids.")
        existing = list(SaleProduct.objects.filter(sale=self.context["sale"]).values_list("product_id", flat=True))
        missing = set(ids) - set(existing)
        if missing:
            raise serializers.ValidationError(f"Not in the sale: {sorted(missing)}")
        return ids + [pk for pk in existing if pk not in ids]

    @transaction.atomic
    def save(self, **kwargs):
        sale = self.context["sale"]
        positions = {pk: position for position, pk in enumerate(self.validated_data["ids"], start=1)}
        links = list(SaleProduct.objects.select_for_update().filter(sale=sale))
        for link in links:
            link.position = positions.get(link.product_id, len(positions) + 1)
        SaleProduct.objects.bulk_update(links, ["position"])
