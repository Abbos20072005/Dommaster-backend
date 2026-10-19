from rest_framework import serializers

from apps.service.attributes import request_language, translated
from apps.service.models import Order, Project
from apps.service.pro import clean_name

MONEY = {"max_digits": 18, "decimal_places": 2}


class ProjectSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True, default=0, help_text="Linked order items")
    orders_count = serializers.IntegerField(read_only=True, default=0, help_text="Orders with linked items")

    class Meta:
        model = Project
        fields = ("id", "name", "address", "comment", "status", "archived_at", "items_count", "orders_count",
                  "created_at", "updated_at")
        read_only_fields = ("status", "archived_at", "created_at", "updated_at")

    def validate_name(self, value):
        value = clean_name(value)
        if not Project.NAME_MIN_LENGTH <= len(value) <= Project.NAME_MAX_LENGTH:
            raise serializers.ValidationError(
                f"From {Project.NAME_MIN_LENGTH} to {Project.NAME_MAX_LENGTH} characters.")
        return value


class ProjectListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Project.STATUS_CHOICES, required=False)


class LinkItemsSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    item_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=False,
                                     help_text="Order item ids; not sent = every item of the order")
    force = serializers.BooleanField(default=False, help_text="Move items linked to another project")


class UnlinkItemsSerializer(serializers.Serializer):
    item_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=False,
                                     help_text="Order item ids; not sent = every item of the order")


class PeriodSerializer(serializers.Serializer):
    to = serializers.DateField(required=False, help_text="Order date to, inclusive")
    vars()["from"] = serializers.DateField(required=False, help_text="Order date from, inclusive")

    def validate(self, attrs):
        if attrs.get("from") and attrs.get("to") and attrs["from"] > attrs["to"]:
            raise serializers.ValidationError({"from": "Must not be after `to`."})
        return attrs


class PeriodPageSerializer(PeriodSerializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)


class LinkedProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class LinkedItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    project = LinkedProjectSerializer(allow_null=True)


class LinkResultSerializer(serializers.ModelSerializer):
    order_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("id", "order_items")

    def get_order_items(self, order) -> LinkedItemSerializer(many=True):
        items = order.order_items.select_related("project").order_by("id")
        return LinkedItemSerializer(items, many=True).data


class UnlinkedOrderSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField()
    unlinked_items_count = serializers.IntegerField()

    class Meta:
        model = Order
        fields = ("id", "status", "payment_status", "total_price", "created_at", "items_count",
                  "unlinked_items_count")


class ExpenseTotalsSerializer(serializers.Serializer):
    goods = serializers.DecimalField(**MONEY, help_text="Goods after the product discount and the promocode share")
    delivery = serializers.DecimalField(**MONEY, help_text="Share of the delivery")
    total = serializers.DecimalField(**MONEY)
    orders_count = serializers.IntegerField()
    items_count = serializers.IntegerField()


class ProjectExpenseSerializer(ExpenseTotalsSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()


class CategoryExpenseSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True, help_text="Root category; null = product without a category")
    name = serializers.CharField(allow_null=True)
    goods = serializers.DecimalField(**MONEY)


class DashboardSerializer(serializers.Serializer):
    totals = ExpenseTotalsSerializer()
    projects = ProjectExpenseSerializer(many=True)
    categories = CategoryExpenseSerializer(many=True)


class ProjectSummarySerializer(serializers.Serializer):
    project = ProjectSerializer()
    totals = ExpenseTotalsSerializer()
    categories = CategoryExpenseSerializer(many=True)


class ExpenseProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    image = serializers.CharField(allow_null=True)


class ProjectItemSerializer(serializers.Serializer):
    """One linked order item (`ItemExpense`)."""
    id = serializers.IntegerField(source="item.id")
    order_id = serializers.IntegerField(source="order.id")
    order_created_at = serializers.DateTimeField(source="order.created_at")
    product = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    quantity = serializers.IntegerField(source="item.quantity")
    unit_price = serializers.DecimalField(**MONEY)
    amount = serializers.DecimalField(**MONEY, help_text="unit_price × quantity")
    discount = serializers.DecimalField(**MONEY, help_text="Share of the order's promocode discount")
    goods = serializers.DecimalField(**MONEY, help_text="amount - discount")
    delivery = serializers.DecimalField(**MONEY, help_text="Share of the order's delivery")
    total = serializers.DecimalField(**MONEY)

    def get_product(self, expense) -> ExpenseProductSerializer:
        product = expense.item.product
        image = product.product_image.first()
        request = self.context.get("request")
        return {
            "id": product.id,
            "name": translated(product, "name", request_language(request)),
            "image": request.build_absolute_uri(image.image.url) if image and request else None,
        }

    def get_category(self, expense) -> LinkedProjectSerializer(allow_null=True):
        category = expense.item.category_root
        if category is None:
            return None
        return {"id": category.id, "name": translated(category, "name", request_language(self.context.get("request")))}
