from rest_framework import serializers
from apps.authorization.models import Customer, CustomerAddresses


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddresses
        fields = ("id", "name", "location_name", "latitude", "longitude", "is_default", "created_at")


class CustomerSerializer(serializers.ModelSerializer):
    orders_count = serializers.IntegerField(read_only=True, default=0)
    total_purchase = serializers.FloatField(read_only=True, default=0)

    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number", "email", "role", "verified", "is_blocked",
                  "last_login", "orders_count", "total_purchase", "created_at", "updated_at")
        read_only_fields = ("last_login", "created_at", "updated_at")

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
    blocked = serializers.IntegerField()
