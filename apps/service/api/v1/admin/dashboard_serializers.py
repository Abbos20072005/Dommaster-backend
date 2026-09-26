from rest_framework import serializers
from .serializers import OrderListSerializer

WEEK, MONTH = "week", "month"
PERIOD_DAYS = {WEEK: 7, MONTH: 30}


class DashboardQuerySerializer(serializers.Serializer):
    """Query params of the dashboard endpoint."""
    days = serializers.IntegerField(default=30, min_value=1, max_value=365, help_text="KPI cards window")
    period = serializers.ChoiceField(choices=list(PERIOD_DAYS), default=WEEK,
                                     help_text="Delivered orders / registrations charts: 7 or 30 days")
    months = serializers.IntegerField(default=6, min_value=1, max_value=24)
    low_stock = serializers.IntegerField(default=10, min_value=0)


class MetricSerializer(serializers.Serializer):
    value = serializers.FloatField()
    change = serializers.FloatField(allow_null=True, help_text="% vs the previous period of the same length, "
                                                               "null if the previous period is 0")


class DashboardSummarySerializer(serializers.Serializer):
    days = serializers.IntegerField()
    orders = MetricSerializer(help_text="All created orders")
    revenue = MetricSerializer(help_text="Sum of completed orders")
    average_check = MetricSerializer(help_text="Average total of completed orders")
    new_customers = MetricSerializer()


class DeliveredOrdersPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()
    revenue = serializers.FloatField()
    average_check = serializers.FloatField()


class DeliveredOrdersSerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=list(PERIOD_DAYS))
    count = serializers.IntegerField()
    revenue = serializers.FloatField()
    change = serializers.FloatField(allow_null=True, help_text="Revenue % vs the previous period")
    points = DeliveredOrdersPointSerializer(many=True)


class RegistrationsPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()


class RegistrationsSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    total = serializers.IntegerField()
    mobile = serializers.IntegerField(help_text="Has an FCM token (registered a device in the app)")
    web = serializers.IntegerField()
    mobile_percent = serializers.FloatField()
    web_percent = serializers.FloatField()
    points = RegistrationsPointSerializer(many=True)


class AttentionSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="Sum of all counters below")
    out_of_stock = serializers.IntegerField(help_text="Active products with quantity <= 0")
    out_of_stock_categories = serializers.ListField(child=serializers.CharField(),
                                                    help_text="Top categories of out-of-stock products")
    stale_pending_orders = serializers.IntegerField(help_text="Pending longer than `pending_hours`")
    pending_hours = serializers.IntegerField()
    unanswered_questions = serializers.IntegerField(help_text="Visible questions without an admin reply")
    unanswered_chats = serializers.IntegerField(help_text="Chats whose last message is from the customer")
    moderation_queue = serializers.IntegerField(help_text="Hidden customer replies to questions")
    last_stock_sync = serializers.DateTimeField(allow_null=True, help_text="Last 1C remaining (stock) upload")


class CustomersCompositionSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    individual = serializers.IntegerField(help_text="Verified, role user")
    b2b = serializers.IntegerField(help_text="Verified, role prorab")
    unverified = serializers.IntegerField()
    active = serializers.IntegerField(help_text="Logged in within the last 30 days")
    repeat_purchase_percent = serializers.FloatField(help_text="% of buyers with 2+ non-canceled orders")
    blocked = serializers.IntegerField()


class CatalogSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="Active products; in_stock + low_stock + out_of_stock = total")
    in_stock = serializers.IntegerField(help_text="quantity > low_stock")
    low_stock = serializers.IntegerField(help_text="0 < quantity <= low_stock")
    out_of_stock = serializers.IntegerField(help_text="quantity <= 0")
    incomplete = serializers.IntegerField(help_text="No image or no price (overlaps with the stock counters)")
    inactive = serializers.IntegerField()
    low_stock_threshold = serializers.IntegerField()


class RevenueMonthSerializer(serializers.Serializer):
    month = serializers.DateField(help_text="First day of the month")
    b2b = serializers.FloatField()
    individual = serializers.FloatField()


class RevenueSerializer(serializers.Serializer):
    b2b = serializers.FloatField(help_text="Completed orders of prorab customers")
    individual = serializers.FloatField(help_text="All other completed orders")
    months = RevenueMonthSerializer(many=True)


class DashboardSerializer(serializers.Serializer):
    summary = DashboardSummarySerializer()
    delivered_orders = DeliveredOrdersSerializer()
    registrations = RegistrationsSerializer()
    recent_orders = OrderListSerializer(many=True)
    attention = AttentionSerializer()
    customers = CustomersCompositionSerializer()
    catalog = CatalogSerializer()
    revenue = RevenueSerializer()
