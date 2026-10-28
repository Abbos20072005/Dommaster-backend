from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.authorization.activity import activity_text, mask_phone
from apps.authorization.models import Customer, CustomerActivity, CustomerAddresses, CustomerNote, \
    CustomerRoleChange


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddresses
        fields = ("id", "name", "location_name", "latitude", "longitude", "is_default",
                  *CustomerAddresses.DETAIL_FIELDS, *CustomerAddresses.RECIPIENT_FIELDS, "created_at")


class CustomerSerializer(serializers.ModelSerializer):
    """`phone_number` goes out masked (`+998 90 *** ** 67`); the full number = `POST customers/<id>/reveal-phone/`
    (written to the journal). It is still writable in full."""
    orders_count = serializers.IntegerField(read_only=True, default=0)
    total_purchase = serializers.FloatField(read_only=True, default=0)
    last_order_at = serializers.DateTimeField(read_only=True, default=None, allow_null=True)
    returns_count = serializers.IntegerField(read_only=True, default=0, help_text="Canceled orders")
    active_devices = serializers.IntegerField(read_only=True, default=0, help_text="Devices with a push token")
    tags = serializers.ListField(child=serializers.CharField(max_length=Customer.MAX_TAG_LENGTH), required=False,
                                 max_length=Customer.MAX_TAGS)

    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number", "email", "role", "verified", "is_blocked",
                  "avatar", "last_login", "last_login_platform", "registration_channel", "language", "segment",
                  "tags", "is_deleted", "deleted_at", "orders_count", "total_purchase", "last_order_at",
                  "returns_count", "active_devices", "created_at", "updated_at")
        # role (prorab = PRO) is changed only by the role/ action, so that every change is in the history
        read_only_fields = ("role", "avatar", "last_login", "last_login_platform", "registration_channel",
                            "is_deleted", "deleted_at", "created_at", "updated_at")

    def validate_phone_number(self, value):
        qs = Customer.objects.filter(phone_number=value, is_deleted=False)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("Customer with this phone number already exists")
        return value

    def validate_tags(self, value):
        tags = []
        for tag in value:
            tag = tag.strip()
            if tag and tag.casefold() not in {t.casefold() for t in tags}:
                tags.append(tag)
        return tags

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["phone_number"] = mask_phone(data.get("phone_number"))
        return data


class CustomerDetailSerializer(CustomerSerializer):
    addresses = CustomerAddressSerializer(source="customeraddresses_set", many=True, read_only=True)

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ("addresses",)


class CustomerStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="Not deleted")
    active = serializers.IntegerField(help_text="Logged in within the last 30 days")
    b2b = serializers.IntegerField(help_text="Role prorab (PRO)")
    blocked = serializers.IntegerField()
    ordered_30d = serializers.IntegerField(help_text="Placed an order (any status) within the last 30 days")
    deleted = serializers.IntegerField()


class RevealPhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class RoleChangeSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Customer.Role.choices, help_text="prorab = PRO")
    reason = serializers.CharField(required=False, allow_blank=True, default="",
                                   help_text="Required when PRO is revoked")

    def validate(self, attrs):
        attrs["reason"] = attrs["reason"].strip()
        customer = self.context["customer"]
        if attrs["role"] == customer.role:
            raise serializers.ValidationError({"role": f"Already {customer.role}."})
        if customer.is_pro and not attrs["reason"]:
            raise serializers.ValidationError({"reason": "Required to revoke PRO."})
        return attrs


class RoleChangeAuthorSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "full_name")

    def get_full_name(self, obj) -> str:
        profile = getattr(obj, "staff_profile", None)
        return (profile.full_name if profile else "") or obj.get_full_name() or obj.get_username()


class RoleHistorySerializer(serializers.ModelSerializer):
    changed_by = RoleChangeAuthorSerializer(read_only=True, allow_null=True)

    class Meta:
        model = CustomerRoleChange
        fields = ("id", "old_value", "new_value", "changed_by", "reason", "created_at")


class CustomerNoteSerializer(serializers.ModelSerializer):
    author = RoleChangeAuthorSerializer(read_only=True, allow_null=True)

    class Meta:
        model = CustomerNote
        fields = ("id", "author", "text", "created_at")
        read_only_fields = ("created_at",)

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Empty note.")
        return value


class CustomerActivitySerializer(serializers.ModelSerializer):
    text = serializers.SerializerMethodField()
    actor = RoleChangeAuthorSerializer(read_only=True, allow_null=True)

    class Meta:
        model = CustomerActivity
        fields = ("id", "kind", "text", "channel", "actor", "data", "created_at")

    def get_text(self, obj) -> str:
        return activity_text(obj)
