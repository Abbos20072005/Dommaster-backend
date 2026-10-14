from typing import Optional
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from apps.service.models import Product, ProductAttribute, ProductModeration
from apps.service.moderation import CHECKS, NOT_PENDING, NOT_READY, readiness
from .product import ProductBrandSerializer, ProductCharacteristicSerializer, ProductImageSerializer
from .category import ProductItemCategorySerializer


class ModerationStaffSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="staff_profile.full_name", read_only=True, default="")

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "full_name")


class ModerationProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(help_text="The main image")

    class Meta:
        model = Product
        fields = ("id", "name", "name_uz", "name_ru", "product_code", "articul_code", "image", "publish_status",
                  "is_active")

    def get_image(self, product) -> Optional[str]:
        images = product.product_image.all()
        return ProductImageSerializer(images[0], context=self.context).data["image"] if images else None


class ModerationProductPreviewSerializer(ModerationProductSerializer):
    """The product as the customer will see it (preview of the site / app card)."""
    brand = ProductBrandSerializer(read_only=True)
    product_item_category = ProductItemCategorySerializer(read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)
    attribute_values = ProductCharacteristicSerializer(many=True, read_only=True)

    class Meta(ModerationProductSerializer.Meta):
        fields = ModerationProductSerializer.Meta.fields + (
            "description_uz", "description_ru", "brand", "product_item_category", "price", "discount_price",
            "discount", "unit", "quantity", "images", "attribute_values")


class ReadinessCheckSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=CHECKS)
    done = serializers.BooleanField()


class ReadinessAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = ("id", "name", "name_uz", "name_ru")


class ReadinessShortSerializer(serializers.Serializer):
    done = serializers.IntegerField(help_text="Checks passed")
    total = serializers.IntegerField()
    ready = serializers.BooleanField(help_text="Every check passed: the row can be approved")
    missing = serializers.ListField(child=serializers.ChoiceField(choices=CHECKS),
                                    help_text="Failed checks, in checklist order")


class ReadinessSerializer(ReadinessShortSerializer):
    checks = ReadinessCheckSerializer(many=True)
    missing_attributes = ReadinessAttributeSerializer(many=True,
                                                      help_text="Required attributes of the category without a value")


class ProductModerationListSerializer(serializers.ModelSerializer):
    product = ModerationProductSerializer(read_only=True)
    submitted_by = ModerationStaffSerializer(read_only=True, allow_null=True)
    reviewed_by = ModerationStaffSerializer(read_only=True, allow_null=True)
    waiting_seconds = serializers.SerializerMethodField(
        help_text="pending: since it was sent; reviewed: how long it waited for the review")
    readiness = serializers.SerializerMethodField()

    class Meta:
        model = ProductModeration
        fields = ("id", "status", "product", "submitted_by", "submitted_at", "waiting_seconds", "reviewed_by",
                  "reviewed_at", "reason", "readiness")
        read_only_fields = fields

    def get_waiting_seconds(self, row) -> int:
        end = row.reviewed_at or timezone.now()
        return max(int((end - row.submitted_at).total_seconds()), 0)

    def get_readiness(self, row) -> ReadinessShortSerializer:
        return ReadinessShortSerializer(readiness(row.product)).data


class ProductModerationSerializer(ProductModerationListSerializer):
    product = ModerationProductPreviewSerializer(read_only=True)

    def get_readiness(self, row) -> ReadinessSerializer:
        return ReadinessSerializer(readiness(row.product)).data


class ModerationRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, help_text="Why the product is returned (shown to the content team)")


class ModerationBulkApproveSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False, max_length=100,
                                help_text="Moderation row ids")


class ModerationSkippedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    reason = serializers.ChoiceField(choices=(NOT_PENDING, NOT_READY),
                                     help_text="not_pending: no such pending row; not_ready: failed checks")
    missing = serializers.ListField(child=serializers.ChoiceField(choices=CHECKS))


class ModerationBulkApproveResultSerializer(serializers.Serializer):
    approved = serializers.ListField(child=serializers.IntegerField())
    skipped = ModerationSkippedSerializer(many=True)


class ModerationStatsSerializer(serializers.Serializer):
    pending = serializers.IntegerField(help_text="In the queue now")
    approved = serializers.IntegerField(help_text="All time")
    rejected = serializers.IntegerField(help_text="All time")
    approved_today = serializers.IntegerField()
    rejected_today = serializers.IntegerField()
    avg_wait_seconds = serializers.IntegerField(allow_null=True, help_text="Average waiting of the queue so far")
    oldest_submitted_at = serializers.DateTimeField(allow_null=True, help_text="The oldest pending row")
    oldest_wait_seconds = serializers.IntegerField(allow_null=True)
