from django.db.models import Max
from rest_framework import serializers
from apps.service.badges import sync_auto_badge
from apps.service.models import ProductBadge

RULE_FIELDS = ("rule_field", "rule_operator", "rule_value")


class ProductBadgeSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ProductBadge
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "kind", *RULE_FIELDS, "color", "position",
                  "is_active", "products_count", "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "rule_value": {"min_value": 0},
        }

    def validate(self, attrs):
        def current(name):
            return attrs.get(name, getattr(self.instance, name, None))

        if current("kind") == ProductBadge.AUTO:
            missing = {name: "Required for an auto badge." for name in RULE_FIELDS if current(name) in (None, "")}
            if missing:
                raise serializers.ValidationError(missing)
            if current("rule_field") == ProductBadge.DISCOUNT and current("rule_value") > 100:
                raise serializers.ValidationError({"rule_value": "Discount is a percent, 100 at most."})
        else:
            attrs.update(dict.fromkeys(RULE_FIELDS))
        return attrs

    @staticmethod
    def _sync(badge):
        # the rule may have changed: apply it right away, don't wait for the cron
        if badge.kind == ProductBadge.AUTO:
            sync_auto_badge(badge)
        badge.products_count = badge.products.count()
        return badge

    def create(self, validated_data):
        if "position" not in validated_data:
            validated_data["position"] = (ProductBadge.objects.aggregate(last=Max("position"))["last"] or 0) + 1
        return self._sync(super().create(validated_data))

    def update(self, instance, validated_data):
        return self._sync(super().update(instance, validated_data))
