from rest_framework import serializers
from apps.service.models import ProductModel
from .product import ProductBrandSerializer


class ProductModelSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer()
    products_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ProductModel
        fields = ("id", "name", "brand", "is_active", "products_count", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")
        # (brand, name) is checked in validate(), case-insensitively
        validators = []

    def validate(self, attrs):
        instance = self.instance
        brand = attrs.get("brand", instance.brand if instance else None)
        name = attrs.get("name", instance.name if instance else "")
        # products of the model have its brand (ProductSerializer.validate)
        if instance and brand != instance.brand and instance.products.exists():
            raise serializers.ValidationError({"brand": "Model has products, its brand can't be changed."})
        duplicates = ProductModel.objects.filter(brand=brand, name__iexact=name)
        if instance:
            duplicates = duplicates.exclude(pk=instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError({"name": "This brand already has a model with this name."})
        return attrs
