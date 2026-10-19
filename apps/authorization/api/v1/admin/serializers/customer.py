from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.authorization.models import Customer, CustomerAddresses, CustomerAccountTypeChange


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddresses
        fields = ("id", "name", "location_name", "latitude", "longitude", "is_default",
                  *CustomerAddresses.DETAIL_FIELDS, "created_at")


class CustomerSerializer(serializers.ModelSerializer):
    orders_count = serializers.IntegerField(read_only=True, default=0)
    total_purchase = serializers.FloatField(read_only=True, default=0)

    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number", "email", "role", "account_type", "verified", "is_blocked",
                  "avatar", "last_login", "orders_count", "total_purchase", "created_at", "updated_at")
        # account_type is changed only by the account-type/ action, so that every change is in the history
        read_only_fields = ("account_type", "avatar", "last_login", "created_at", "updated_at")

    def validate_phone_number(self, value):
        qs = Customer.objects.filter(phone_number=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("Customer with this phone number already exists")
        return value


class CustomerDetailSerializer(CustomerSerializer):
    addresses = CustomerAddressSerializer(source="customeraddresses_set", many=True, read_only=True)

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ("addresses",)


class CustomerStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField(help_text="Logged in within the last 30 days")
    b2b = serializers.IntegerField(help_text="Role prorab")
    pro = serializers.IntegerField(help_text="Account type PRO")
    blocked = serializers.IntegerField()


class AccountTypeChangeSerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(choices=Customer.AccountType.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="",
                                   help_text="Required when PRO is revoked")

    def validate(self, attrs):
        attrs["reason"] = attrs["reason"].strip()
        customer = self.context["customer"]
        if attrs["account_type"] == customer.account_type:
            raise serializers.ValidationError({"account_type": f"Already {customer.account_type}."})
        if customer.is_pro and not attrs["reason"]:
            raise serializers.ValidationError({"reason": "Required to revoke PRO."})
        return attrs


class AccountTypeChangeAuthorSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "full_name")

    def get_full_name(self, obj) -> str:
        profile = getattr(obj, "staff_profile", None)
        return (profile.full_name if profile else "") or obj.get_full_name() or obj.get_username()


class AccountTypeHistorySerializer(serializers.ModelSerializer):
    changed_by = AccountTypeChangeAuthorSerializer(read_only=True, allow_null=True)

    class Meta:
        model = CustomerAccountTypeChange
        fields = ("id", "old_value", "new_value", "changed_by", "reason", "created_at")
