from rest_framework import serializers

from apps.payment.atmos_refund import RefundError, refund_order
from apps.payment.models import AtmosRefund
from .order import OrderCommentAuthorSerializer


class RefundLineSerializer(serializers.Serializer):
    """A receipt line; `item_id` null = the delivery. Sums in tiyin."""
    item_id = serializers.IntegerField(allow_null=True)
    ofd_code = serializers.CharField()
    name = serializers.CharField()
    amount = serializers.IntegerField()
    quantity = serializers.IntegerField()
    package_code = serializers.CharField(allow_blank=True, required=False)


class RefundableLineSerializer(RefundLineSerializer):
    """`quantity` / `amount` = what can still be refunded, `charged_*` = what the charge receipt showed."""
    charged_quantity = serializers.IntegerField()
    charged_amount = serializers.IntegerField()


class OrderRefundableSerializer(serializers.Serializer):
    order = serializers.IntegerField()
    payment_status = serializers.IntegerField()
    can_refund = serializers.BooleanField()
    reason = serializers.CharField(allow_blank=True, help_text="why the order can't be refunded here; '' when it can")
    charged_amount = serializers.IntegerField(allow_null=True)
    refunded_amount = serializers.IntegerField()
    lines = RefundableLineSerializer(many=True)


class RefundItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderRefundSerializer(serializers.ModelSerializer):
    """POST = refund through Atmos at once: `items` (order item id + quantity), `delivery`, or `all` (whatever is
    left); sums are taken from the charge receipt, not sent."""
    items = RefundItemSerializer(many=True, write_only=True, required=False)
    delivery = serializers.BooleanField(write_only=True, default=False)
    all = serializers.BooleanField(write_only=True, default=False)
    lines = RefundLineSerializer(many=True, read_only=True)
    created_by = OrderCommentAuthorSerializer(read_only=True, allow_null=True)

    class Meta:
        model = AtmosRefund
        fields = ("id", "amount", "lines", "reason", "status", "partial_reverse_id", "reverted_amount",
                  "left_amount", "error", "created_by", "created_at", "items", "delivery", "all")
        read_only_fields = ("amount", "status", "partial_reverse_id", "reverted_amount", "left_amount", "error",
                            "created_at")

    def validate(self, attrs):
        if not attrs.get("all") and not attrs.get("items") and not attrs.get("delivery"):
            raise serializers.ValidationError("Send items, delivery or all")
        return attrs

    def create(self, validated_data):
        try:
            return refund_order(self.context["order"].id, items=validated_data.get("items") or (),
                                delivery=validated_data["delivery"], everything=validated_data["all"],
                                reason=validated_data.get("reason", ""), user=self.context["request"].user)
        except RefundError as e:
            # `refund` only when Atmos was called (the saved failed / pending row)
            raise serializers.ValidationError({"detail": str(e), **({"refund": e.refund.id} if e.refund else {})})
