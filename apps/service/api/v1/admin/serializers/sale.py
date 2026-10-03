from django.db import transaction
from rest_framework import serializers
from apps.service.models import Sale, Product
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


class SaleSerializer(serializers.ModelSerializer):
    products = SaleProductSerializer(many=True, allow_empty=True)

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
        products = validated_data.pop("products")
        instance = super().create(validated_data)
        instance.products.set(products)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        products = validated_data.pop("products", None)
        instance = super().update(instance, validated_data)
        if products is not None:
            instance.products.set(products)
        return instance
