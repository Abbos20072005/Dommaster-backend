from datetime import date
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from apps.authorization.models import Customer, CustomerAddresses
from apps.base.models import MarketBranch, Promocodes
from apps.payment.atmos_hold import HoldError, cancel_order_hold, charge_order_hold, has_hold
from apps.service.ikpu import is_confirmation, missing_items, set_item_codes
from apps.service.models import Manager, Order, OrderComment, OrderItem, Product, ProductCodeChange
from apps.service.models.product import IKPU_VALIDATOR
from apps.service.pro import money
from utils.admin_serializers import RelationSerializer

# ORDER_STATUS / DELIVERY_TYPE - the values live on the model, these are the short names the admin modules use
PENDING, CONFIRMED, COLLECTING, DELIVERING = Order.PENDING, Order.CONFIRMED, Order.COLLECTING, Order.DELIVERING
COMPLETED, CANCELED, READY_FOR_PICKUP = Order.COMPLETED, Order.CANCELED, Order.READY_FOR_PICKUP
DELIVERY, PICKUP = Order.DELIVERY, Order.PICKUP
# PAYMENT_TYPE / PAYMENT_STATUS
PAYMENT_ON_DELIVERY = 4
PAID = 2

# changing any of these recalculates the order prices
PRICE_FIELDS = {"order_items", "promocode", "delivery_type", "delivery_price"}


class OrderCustomerSerializer(RelationSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number")


class OrderAddressSerializer(RelationSerializer):
    class Meta:
        model = CustomerAddresses
        fields = ("id", "name", "location_name", "latitude", "longitude", *CustomerAddresses.DETAIL_FIELDS)


class OrderBranchSerializer(RelationSerializer):
    class Meta:
        model = MarketBranch
        fields = ("id", "name", "address", "phone_number")


class OrderStoreSnapshotSerializer(serializers.Serializer):
    """Read-only: `Order.pickup_store_snapshot` - the pickup branch as it was when it was chosen."""
    id = serializers.IntegerField()
    name_uz = serializers.CharField()
    name_ru = serializers.CharField()
    address_uz = serializers.CharField()
    address_ru = serializers.CharField()
    landmark_uz = serializers.CharField()
    landmark_ru = serializers.CharField()
    phone = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class OrderPromocodeSerializer(RelationSerializer):
    class Meta:
        model = Promocodes
        fields = ("id", "name", "code", "discount_precent", "discount_price", "expires_at")


class OrderProductSerializer(RelationSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "product_code", "price", "discount_price")


class OrderManagerSerializer(RelationSerializer):
    class Meta:
        model = Manager
        fields = ("id", "full_name", "is_active")


class OrderCommentAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "first_name", "last_name")


class OrderCommentShortSerializer(serializers.ModelSerializer):
    author = OrderCommentAuthorSerializer(read_only=True, allow_null=True, help_text="null for system comments")

    class Meta:
        model = OrderComment
        fields = ("id", "author", "text", "is_system", "created_at")


class OrderItemSerializer(serializers.ModelSerializer):
    product = OrderProductSerializer()

    class Meta:
        model = OrderItem
        fields = ("id", "product", "quantity", "unit_price", "ikpu_code")
        # unit_price = price of one unit when ordered (null = older item -> the panel shows product.price);
        # ikpu_code is set with orders/{id}/ikpu/; a new item takes the product's code ("" = none)
        read_only_fields = ("unit_price", "ikpu_code")
        extra_kwargs = {"quantity": {"min_value": 1}}


class IkpuMissingError(serializers.ValidationError):
    """400 of a confirmation refused for items without an IKPU code; `missing_ikpu` keeps the ids as numbers."""

    def __init__(self, items):
        super().__init__()
        self.detail = {
            "status": ["Order items without an IKPU code: set them before confirming the order."],
            "missing_ikpu": [{"item_id": item_id, "product": {"id": product.id, "name": product.name}}
                             for item_id, product in items],
        }


class OrderListSerializer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer(read_only=True)
    manager = OrderManagerSerializer(read_only=True)
    items_count = serializers.IntegerField(read_only=True, default=0)
    pickup_store = OrderStoreSnapshotSerializer(source="pickup_store_snapshot", read_only=True, allow_null=True,
                                                help_text="Pickup store as it was when chosen; null = delivery")
    pickup_expired = serializers.BooleanField(read_only=True, help_text="Ready for pickup and the deadline passed")

    class Meta:
        model = Order
        fields = ("id", "customer", "manager", "status", "channel", "payment_status", "payment_type", "payment_method",
                  "delivery_type", "pickup_store", "pickup_deadline", "pickup_expired",
                  "total_price", "products_total_price", "saved_price", "delivery_price",
                  "receiver_name", "receiver_phone", "items_count", "created_at", "updated_at")


class OrderSerializer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer()
    manager = OrderManagerSerializer(required=False, allow_null=True)
    order_location = OrderAddressSerializer(required=False, allow_null=True)
    pickup_branch = OrderBranchSerializer(required=False, allow_null=True,
                                          help_text="Pickup store (a branch): write `{\"id\"}`, read = the branch now")
    pickup_store = OrderStoreSnapshotSerializer(source="pickup_store_snapshot", read_only=True, allow_null=True,
                                                help_text="The pickup branch as it was when chosen")
    pickup_expired = serializers.BooleanField(read_only=True, help_text="Ready for pickup and the deadline passed")
    promocode = OrderPromocodeSerializer(required=False, allow_null=True)
    items = OrderItemSerializer(source="order_items", many=True, required=False)
    comments = OrderCommentShortSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "customer", "manager", "status", "channel", "payment_status", "payment_type", "payment_method",
                  "delivery_type", "order_location", *CustomerAddresses.DETAIL_FIELDS,
                  "pickup_branch", "pickup_store", "ready_for_pickup_at", "pickup_deadline", "pickup_expired",
                  "pickup_expired_at", "promocode", "items", "comments",
                  "total_price", "products_total_price", "saved_price", "delivery_price",
                  "receiver_name", "receiver_phone", "hold_id", "ofd_url", "yandex_claim_id", "yandex_claim_status",
                  "created_at", "updated_at")
        read_only_fields = ("total_price", "products_total_price", "saved_price", "hold_id",
                            "yandex_claim_id", "yandex_claim_status", "ready_for_pickup_at", "pickup_deadline",
                            "pickup_expired_at", "created_at", "updated_at")

    def _get(self, attrs, name, default=None):
        if name in attrs:
            return attrs[name]
        return getattr(self.instance, name, default) if self.instance else default

    def validate(self, attrs):
        items = attrs.get("order_items")
        if self.instance is None and not items:
            raise serializers.ValidationError({"items": "At least one item is required."})
        if items is not None:
            if self.instance and self.instance.status != PENDING:
                raise serializers.ValidationError({"items": "Items can only be changed while the order is pending."})
            if not items:
                raise serializers.ValidationError({"items": "At least one item is required."})
            product_ids = [item["product"].id for item in items]
            if len(product_ids) != len(set(product_ids)):
                raise serializers.ValidationError({"items": "Duplicate products."})

        customer = self._get(attrs, "customer")
        location = self._get(attrs, "order_location")
        if location and customer and location.customer_id != customer.id:
            raise serializers.ValidationError({"order_location": "Address does not belong to the customer."})

        delivery_type = self._get(attrs, "delivery_type", DELIVERY)
        if delivery_type == DELIVERY and not location:
            raise serializers.ValidationError({"order_location": "Required for delivery."})
        branch = attrs.get("pickup_branch")
        if delivery_type == DELIVERY and self._get(attrs, "pickup_branch"):
            attrs["pickup_branch"] = None
        elif delivery_type == PICKUP:
            if not self._get(attrs, "pickup_branch"):
                raise serializers.ValidationError({"pickup_branch": "Required for pickup."})
            if branch and not branch.is_active and branch.pk != getattr(self.instance, "pickup_branch_id", None):
                raise serializers.ValidationError({"pickup_branch": "The branch is inactive."})

        # a new address brings its delivery details along unless they are sent with it
        new_location = attrs.get("order_location")
        if (new_location and new_location != getattr(self.instance, "order_location", None)
                and not any(field in attrs for field in CustomerAddresses.DETAIL_FIELDS)):
            attrs.update(new_location.details())

        if self._get(attrs, "payment_method") and self._get(attrs, "payment_type") != PAYMENT_ON_DELIVERY:
            raise serializers.ValidationError({"payment_method": "Only for payment on delivery."})

        promocode = attrs.get("promocode")
        if promocode and promocode.expires_at < date.today():
            raise serializers.ValidationError({"promocode": "Promocode expired."})

        old_status = self.instance.status if self.instance else PENDING
        new_status = attrs.get("status", old_status)
        if new_status == READY_FOR_PICKUP and old_status != READY_FOR_PICKUP:
            if delivery_type != PICKUP:
                raise serializers.ValidationError({"status": "Ready for pickup is for pickup orders only."})
            if old_status != COLLECTING:
                raise serializers.ValidationError({"status": "Only a collecting order can become ready for pickup."})
        # a collected order waiting in the store only leaves by being handed over or cancelled
        if old_status == READY_FOR_PICKUP and new_status not in (READY_FOR_PICKUP, COMPLETED, CANCELED):
            raise serializers.ValidationError({"status": "A ready order can only be completed or canceled."})
        if attrs.get("status") == COLLECTING and old_status != COLLECTING:
            # the Order pre_save signal decrements stock on -> Collecting; fail here with a proper 400 instead
            self._check_stock(items)
        return attrs

    def _check_stock(self, items):
        if items is not None:
            pairs = [(item["product"], item["quantity"]) for item in items]
        else:
            pairs = [(item.product, item.quantity) for item in self.instance.order_items.select_related("product")]
        missing = [product.name for product, quantity in pairs if product.quantity < quantity]
        if missing:
            raise serializers.ValidationError({"status": f"Not enough stock: {', '.join(missing)}"})

    @staticmethod
    def _item_codes(order, items):
        """IKPU code of each sent item: the one its product already has in this order, else the product card's."""
        kept = dict(order.order_items.exclude(ikpu_code="").values_list("product_id", "ikpu_code")) if order else {}
        return {item["product"].id: kept.get(item["product"].id) or item["product"].ikpu_code for item in items}

    def _check_ikpu(self, order, items):
        if items is not None:
            codes = self._item_codes(order, items)
            missing = [(None, item["product"]) for item in items if not codes[item["product"].id]]
        else:
            missing = [(item.id, item.product) for item in missing_items(order)]
        if missing:
            raise IkpuMissingError(missing)

    @classmethod
    def _set_items(cls, order, items):
        # a product that stays in the order keeps its PRO project link and its IKPU code
        links = {item.product_id: (item.project_id, item.category_root_id)
                 for item in order.order_items.filter(project__isnull=False)}
        codes = cls._item_codes(order, items)
        order.order_items.all().delete()
        OrderItem.objects.bulk_create(
            OrderItem(order=order, product=item["product"], quantity=item["quantity"],
                      unit_price=OrderItem.unit_price_of(item["product"]), ikpu_code=codes[item["product"].id],
                      project_id=links.get(item["product"].id, (None, None))[0],
                      category_root_id=links.get(item["product"].id, (None, None))[1])
            for item in items
        )

    @staticmethod
    def _recalculate(order):
        """Same pricing as client checkout (cart totals + promocode + delivery)."""
        products_total = total = 0.0
        for item in order.order_items.select_related("product"):
            product = item.product
            products_total += product.price * item.quantity
            price = product.discount_price if product.discount_price is not None else product.price
            total += price * item.quantity

        order.products_total_price = products_total
        order.saved_price = products_total - total

        goods_total = total
        promocode = order.promocode
        if promocode:
            if promocode.discount_price and not promocode.discount_precent:
                total -= promocode.discount_price
            elif promocode.discount_precent and not promocode.discount_price:
                total *= 1 - promocode.discount_precent / 100
        order.promocode_discount = money(goods_total) - money(max(total, 0.0))
        delivery_cost = float(order.delivery_price or 0) if order.delivery_type == DELIVERY else 0.0
        order.total_price = max(total, 0.0) + delivery_cost

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("order_items")
        status = validated_data.pop("status", PENDING)
        if is_confirmation(PENDING, status):
            self._check_ikpu(None, items)
        order = Order.objects.create(**validated_data)
        self._set_items(order, items)
        self._recalculate(order)
        # status is applied on an update so the pre_save signal handles stock
        order.status = status
        order.save()
        return order

    def update(self, instance, validated_data):
        new_status = validated_data.get("status", instance.status)
        if is_confirmation(instance.status, new_status):
            # before the hold is charged
            self._check_ikpu(instance, validated_data.get("order_items"))
        if new_status != instance.status:
            self._settle_hold(instance, new_status, validated_data)
        return self._update(instance, validated_data)

    @staticmethod
    def _settle_hold(instance, new_status, validated_data):
        """Atmos card orders (BLD-486): the frozen money is charged when the order leaves Pending (Confirmed, or
        any later status when Confirmed is skipped) and released when it is cancelled. Runs and commits before
        the status is saved, so a charge Atmos refused leaves the status as it was."""
        if not has_hold(instance) or new_status == PENDING:
            return
        try:
            order = cancel_order_hold(instance.pk) if new_status == CANCELED else charge_order_hold(instance.pk)
        except HoldError as e:
            raise serializers.ValidationError({"status": str(e)})
        # the panel may send the whole form back with the old payment status
        validated_data.pop("payment_status", None)
        validated_data.pop("ofd_url", None)
        instance.payment_status, instance.ofd_url = order.payment_status, order.ofd_url

    @transaction.atomic
    def _update(self, instance, validated_data):
        recalculate = bool(PRICE_FIELDS & validated_data.keys())
        old_manager_id = instance.manager_id
        items = validated_data.pop("order_items", None)
        if items is not None:
            self._set_items(instance, items)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if recalculate:
            self._recalculate(instance)
        instance.save()
        if instance.manager_id != old_manager_id:
            manager = instance.manager
            text = f"Menejer o'zgartirildi: {manager.full_name}" if manager else "Menejer olib tashlandi"
            OrderComment.objects.create(order=instance, text=text, is_system=True)
        return instance


class OrderItemIkpuSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Order item id")
    ikpu_code = serializers.CharField(validators=[IKPU_VALIDATOR], help_text="17 digits")


class OrderIkpuSerializer(serializers.Serializer):
    """IKPU codes of the items of a pending order (context `order`, locked); the product cards take them too."""
    items = OrderItemIkpuSerializer(many=True, allow_empty=False)

    def validate_items(self, rows):
        order = self.context["order"]
        if order.status != PENDING:
            raise serializers.ValidationError("IKPU codes can only be changed while the order is pending.")
        ids = [row["id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Duplicate items.")
        items = order.order_items.select_related("product").in_bulk(ids)
        foreign = sorted(set(ids) - set(items))
        if foreign:
            raise serializers.ValidationError(f"Not items of the order: {foreign}")
        return {items[row["id"]]: row["ikpu_code"] for row in rows}

    def save(self, **kwargs):
        request = self.context.get("request")
        set_item_codes(self.context["order"], self.validated_data["items"], request.user if request else None)


class CodeChangeProductSerializer(RelationSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "product_code", "articul_code")


class CodeChangeOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("id", "status")


class CodeChangeUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="staff_profile.full_name", default="", read_only=True)

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "full_name")


class ProductCodeChangeSerializer(serializers.ModelSerializer):
    product = CodeChangeProductSerializer(read_only=True)
    order = CodeChangeOrderSerializer(read_only=True, allow_null=True, help_text="null = changed on the product card")
    changed_by = CodeChangeUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = ProductCodeChange
        fields = ("id", "product", "order", "field", "old_value", "new_value", "source", "changed_by", "created_at")


class ManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manager
        fields = ("id", "full_name", "is_active", "created_at", "updated_at")


class OrderCommentOrderSerializer(RelationSerializer):
    class Meta:
        model = Order
        fields = ("id",)


class OrderCommentSerializer(serializers.ModelSerializer):
    order = OrderCommentOrderSerializer()
    author = OrderCommentAuthorSerializer(read_only=True, allow_null=True, help_text="null for system comments")

    class Meta:
        model = OrderComment
        fields = ("id", "order", "author", "text", "is_system", "created_at")
        read_only_fields = ("is_system", "created_at")

    def create(self, validated_data):
        return OrderComment.objects.create(author=self.context["request"].user, **validated_data)


class OrderStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    confirmed = serializers.IntegerField()
    collecting = serializers.IntegerField()
    delivering = serializers.IntegerField()
    completed = serializers.IntegerField()
    canceled = serializers.IntegerField()
    ready_for_pickup = serializers.IntegerField()
    pickup_expired = serializers.IntegerField(help_text="Ready for pickup and the deadline passed")
    paid = serializers.IntegerField(help_text="Payment status Paid")
    revenue = serializers.FloatField(help_text="Sum of completed orders")
    average_check = serializers.FloatField(help_text="Average total of completed orders")
