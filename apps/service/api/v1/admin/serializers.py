from datetime import date
from django.db import transaction
from rest_framework import serializers
from apps.authorization.models import Customer, CustomerAddresses
from apps.base.models import MarketBranch, Promocodes
from apps.service.models import Order, OrderItem, Product, Brand, ProductCategory, ProductSubCategory, \
    ProductItemCategory, ProductImage, ProductCharacteristics
from utils.admin_serializers import RelationSerializer

# ORDER_STATUS
PENDING, COLLECTING, DELIVERING, COMPLETED, CANCELED = 0, 1, 2, 3, 4
# DELIVERY_TYPE
DELIVERY, PICKUP = 0, 1
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
        fields = ("id", "name", "location_name", "latitude", "longitude")


class OrderBranchSerializer(RelationSerializer):
    class Meta:
        model = MarketBranch
        fields = ("id", "name", "address", "phone_number")


class OrderPromocodeSerializer(RelationSerializer):
    class Meta:
        model = Promocodes
        fields = ("id", "name", "code", "discount_precent", "discount_price", "expires_at")


class OrderProductSerializer(RelationSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "product_code", "price", "discount_price")


class OrderItemSerializer(serializers.ModelSerializer):
    product = OrderProductSerializer()

    class Meta:
        model = OrderItem
        fields = ("id", "product", "quantity")
        extra_kwargs = {"quantity": {"min_value": 1}}


class OrderListSerializer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer(read_only=True)
    items_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Order
        fields = ("id", "customer", "status", "payment_status", "payment_type", "payment_method", "delivery_type",
                  "total_price", "products_total_price", "saved_price", "delivery_price",
                  "receiver_name", "receiver_phone", "items_count", "created_at", "updated_at")


class OrderSerializer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer()
    order_location = OrderAddressSerializer(required=False, allow_null=True)
    pickup_branch = OrderBranchSerializer(required=False, allow_null=True)
    promocode = OrderPromocodeSerializer(required=False, allow_null=True)
    items = OrderItemSerializer(source="order_items", many=True, required=False)

    class Meta:
        model = Order
        fields = ("id", "customer", "status", "payment_status", "payment_type", "payment_method", "delivery_type",
                  "order_location", "pickup_branch", "promocode", "items",
                  "total_price", "products_total_price", "saved_price", "delivery_price",
                  "receiver_name", "receiver_phone", "hold_id", "ofd_url", "yandex_claim_id", "yandex_claim_status",
                  "created_at", "updated_at")
        read_only_fields = ("total_price", "products_total_price", "saved_price", "hold_id",
                            "yandex_claim_id", "yandex_claim_status", "created_at", "updated_at")

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
        if delivery_type == PICKUP and not self._get(attrs, "pickup_branch"):
            raise serializers.ValidationError({"pickup_branch": "Required for pickup."})

        if self._get(attrs, "payment_method") and self._get(attrs, "payment_type") != PAYMENT_ON_DELIVERY:
            raise serializers.ValidationError({"payment_method": "Only for payment on delivery."})

        promocode = attrs.get("promocode")
        if promocode and promocode.expires_at < date.today():
            raise serializers.ValidationError({"promocode": "Promocode expired."})

        old_status = self.instance.status if self.instance else PENDING
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
    def _set_items(order, items):
        order.order_items.all().delete()
        OrderItem.objects.bulk_create(
            OrderItem(order=order, product=item["product"], quantity=item["quantity"]) for item in items
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

        promocode = order.promocode
        if promocode:
            if promocode.discount_price and not promocode.discount_precent:
                total -= promocode.discount_price
            elif promocode.discount_precent and not promocode.discount_price:
                total *= 1 - promocode.discount_precent / 100
        delivery_cost = float(order.delivery_price or 0) if order.delivery_type == DELIVERY else 0.0
        order.total_price = max(total, 0.0) + delivery_cost

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("order_items")
        status = validated_data.pop("status", PENDING)
        order = Order.objects.create(**validated_data)
        self._set_items(order, items)
        self._recalculate(order)
        # status is applied on an update so the pre_save signal handles stock
        order.status = status
        order.save()
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        recalculate = bool(PRICE_FIELDS & validated_data.keys())
        items = validated_data.pop("order_items", None)
        if items is not None:
            self._set_items(instance, items)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if recalculate:
            self._recalculate(instance)
        instance.save()
        return instance


class OrderStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    collecting = serializers.IntegerField()
    delivering = serializers.IntegerField()
    completed = serializers.IntegerField()
    canceled = serializers.IntegerField()
    paid = serializers.IntegerField(help_text="Payment status Paid")
    revenue = serializers.FloatField(help_text="Sum of completed orders")
    average_check = serializers.FloatField(help_text="Average total of completed orders")


class ProductBrandSerializer(RelationSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name")


class ProductCategoryShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ("id", "name")


class ProductSubCategoryShortSerializer(serializers.ModelSerializer):
    product_category = ProductCategoryShortSerializer(read_only=True)

    class Meta:
        model = ProductSubCategory
        fields = ("id", "name", "product_category")


class ProductItemCategorySerializer(RelationSerializer):
    product_sub_category = ProductSubCategoryShortSerializer(read_only=True)

    class Meta:
        model = ProductItemCategory
        fields = ("id", "name", "product_sub_category")


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "created_at")


class ProductCharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCharacteristics
        fields = ("id", "name_uz", "name_ru", "name_en", "value_uz", "value_ru", "value_en",
                  "unit_uz", "unit_ru", "unit_en")
        extra_kwargs = {
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "value_ru": {"required": True, "allow_null": False, "allow_blank": False},
        }


class ProductListSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(read_only=True)
    product_item_category = ProductItemCategorySerializer(read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "images", "product_code", "articul_code", "barcode", "brand", "product_item_category",
                  "price", "discount_price", "discount", "unit", "quantity", "rating", "comments_quantity",
                  "is_active", "created_at", "updated_at")


class ProductSerializer(serializers.ModelSerializer):
    brand = ProductBrandSerializer(required=False, allow_null=True)
    product_item_category = ProductItemCategorySerializer(required=False, allow_null=True)
    characteristics = ProductCharacteristicSerializer(source="product_characteristics", many=True, required=False)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "short_description",
                  "description_uz", "description_ru", "description_en",
                  "brand", "product_item_category", "price", "discount_price", "discount", "unit", "quantity",
                  "is_active", "product_code", "articul_code", "barcode", "weight", "length", "width", "height",
                  "rating", "comments_quantity", "questions_quantity", "filter_data", "characteristics", "images",
                  "created_at", "updated_at")
        # filter_data is built from 1C data
        read_only_fields = ("name", "rating", "comments_quantity", "questions_quantity", "filter_data",
                            "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "name_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "description_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "price": {"min_value": 0},
            "discount_price": {"min_value": 0},
            "discount": {"min_value": 0, "max_value": 100},
            "quantity": {"min_value": 0},
        }

    def validate_product_code(self, value):
        # unique column: store empty codes as NULL
        return value or None

    def validate(self, attrs):
        price = attrs.get("price", self.instance.price if self.instance else 0.0)
        discount_price = attrs.get("discount_price", self.instance.discount_price if self.instance else None)
        if discount_price is not None and discount_price > price:
            raise serializers.ValidationError({"discount_price": "Must not be greater than price."})
        return attrs

    @staticmethod
    def _set_characteristics(product, characteristics):
        product.product_characteristics.all().delete()
        ProductCharacteristics.objects.bulk_create(
            ProductCharacteristics(product=product, **item) for item in characteristics
        )

    @transaction.atomic
    def create(self, validated_data):
        characteristics = validated_data.pop("product_characteristics", [])
        product = super().create(validated_data)
        self._set_characteristics(product, characteristics)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        characteristics = validated_data.pop("product_characteristics", None)
        product = super().update(instance, validated_data)
        if characteristics is not None:
            self._set_characteristics(product, characteristics)
        return product


class ProductStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()
    out_of_stock = serializers.IntegerField(help_text="quantity <= 0")
    discounted = serializers.IntegerField(help_text="Has discount price")
