from rest_framework import serializers
from .order import OrderListSerializer

# attention rows
STALE_PENDING_ORDERS, REFUND_PENDING_ORDERS = "stale_pending_orders", "refund_pending_orders"
UNASSIGNED_ORDERS = "unassigned_orders"
OUT_OF_STOCK_PRODUCTS, NO_PRICE_PRODUCTS, REVIEW_PRODUCTS = "out_of_stock_products", "no_price_products", \
    "review_products"
UNANSWERED_QUESTIONS, UNANSWERED_CHATS, MODERATION_QUEUE = "unanswered_questions", "unanswered_chats", \
    "moderation_queue"
EXPIRING_BANNERS, DRAFT_NOTIFICATIONS = "expiring_banners", "draft_notifications"
ATTENTION_KEYS = (STALE_PENDING_ORDERS, REFUND_PENDING_ORDERS, UNASSIGNED_ORDERS, OUT_OF_STOCK_PRODUCTS,
                  NO_PRICE_PRODUCTS, REVIEW_PRODUCTS, UNANSWERED_QUESTIONS, UNANSWERED_CHATS, MODERATION_QUEUE,
                  EXPIRING_BANNERS, DRAFT_NOTIFICATIONS)
ORDERS, CATALOG, FEEDBACK, CONTENT = "orders", "catalog", "feedback", "content"
DANGER, WARNING, INFO = "danger", "warning", "info"


class TodayCardsSerializer(serializers.Serializer):
    today_orders = serializers.IntegerField(help_text="Orders created today, any status")
    today_total = serializers.FloatField(help_text="Sum of their totals")
    today_customers = serializers.IntegerField(help_text="Customers registered today")
    pending = serializers.IntegerField(help_text="All orders in status Pending")
    stale_pending = serializers.IntegerField(help_text="Pending longer than `stale_minutes`")
    stale_minutes = serializers.IntegerField()
    collecting = serializers.IntegerField(help_text="All orders in status Collecting")
    delivering = serializers.IntegerField(help_text="All orders in status Delivering")


class TodayAttentionObjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(allow_null=True, help_text="Product name / banner or notification title / "
                                                            "question or reply text; null for orders and chats")
    date = serializers.DateTimeField(allow_null=True)


class TodayAttentionItemSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=ATTENTION_KEYS)
    group = serializers.ChoiceField(choices=(ORDERS, CATALOG, FEEDBACK, CONTENT))
    level = serializers.ChoiceField(choices=(DANGER, WARNING, INFO))
    count = serializers.IntegerField()
    amount = serializers.FloatField(allow_null=True, help_text="Only refund_pending_orders: sum of the orders")
    date = serializers.DateTimeField(allow_null=True, help_text="Date of the most urgent object: waiting since "
                                                                "(orders, questions, chats), ends at (banners), "
                                                                "publish at (notifications); null for products")
    objects = TodayAttentionObjectSerializer(many=True, help_text="First few objects, most urgent first")


class TodayAttentionSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="Number of rows (the menu badge)")
    banner_days = serializers.IntegerField(help_text="expiring_banners window")
    items = TodayAttentionItemSerializer(many=True, help_text="Only rows with count > 0")


class TodayCatalogSerializer(serializers.Serializer):
    published = serializers.IntegerField(help_text="publish_status = published")
    draft = serializers.IntegerField(help_text="publish_status = draft")
    review = serializers.IntegerField(help_text="publish_status = review")
    incomplete = serializers.IntegerField(help_text="Active products missing a translation, an image or "
                                                    "characteristics (the three counters below overlap)")
    no_translation = serializers.IntegerField(help_text="Active, name_uz or name_ru is empty")
    no_image = serializers.IntegerField(help_text="Active, no images")
    no_characteristics = serializers.IntegerField(help_text="Active, no characteristics and no attribute values")
    out_of_stock = serializers.IntegerField(help_text="Active with quantity <= 0")


class TodayOrdersPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()
    total = serializers.FloatField()


class TodayOrdersChartSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    count = serializers.IntegerField(help_text="Orders created over the period, any status")
    average_per_day = serializers.IntegerField()
    points = TodayOrdersPointSerializer(many=True)


class TodaySerializer(serializers.Serializer):
    now = serializers.DateTimeField(help_text="Server time the response was built at")
    cards = TodayCardsSerializer()
    attention = TodayAttentionSerializer()
    catalog = TodayCatalogSerializer()
    orders_chart = TodayOrdersChartSerializer()
    recent_orders = OrderListSerializer(many=True)
