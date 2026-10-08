from rest_framework import serializers
from apps.service.models import Product
from .category import ProductCategoryShortSerializer
from .dashboard import DAY, DateRangeQuerySerializer, MetricSerializer

MAX_RANGE_DAYS = 366

# payment breakdown keys: PAYMENT_TYPE 1-3, "on delivery" (4) split by `payment_method`, the rest
CLICK, PAYME, UZUM, CASH, CARD, OTHER = "click", "payme", "uzum", "cash", "card", "other"
PAYMENT_KEYS = (CLICK, PAYME, UZUM, CASH, CARD, OTHER)
# delivery breakdown keys
DELIVERY_KEY, PICKUP_KEY = "delivery", "pickup"
DELIVERY_KEYS = (DELIVERY_KEY, PICKUP_KEY)


class SalesAnalyticsQuerySerializer(DateRangeQuerySerializer):
    """Query params of the sales analytics endpoint: one range for every widget but the cohorts."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "date_from" in attrs and (attrs["date_to"] - attrs["date_from"]).days >= MAX_RANGE_DAYS:
            raise serializers.ValidationError({"date_to": f"The range is at most {MAX_RANGE_DAYS} days."})
        return attrs


class RateSerializer(serializers.Serializer):
    value = serializers.FloatField(help_text="%")
    change = serializers.FloatField(allow_null=True, help_text="Percentage points vs the previous period of the "
                                                               "same length, null if it has nothing to compare")


class SalesSummarySerializer(serializers.Serializer):
    days = serializers.IntegerField(help_text="Length of the range in days")
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    revenue = MetricSerializer(help_text="Sum of completed orders")
    orders = MetricSerializer(help_text="All created orders")
    average_check = MetricSerializer(help_text="Average total of completed orders")
    cancel_rate = RateSerializer(help_text="Canceled orders / all created orders")
    refund_rate = RateSerializer(help_text="Orders whose payment was returned / all created orders")
    repeat_rate = RateSerializer(help_text="Buyers of the range for whom it was not the first order")


class SalesChartPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    revenue = serializers.FloatField()
    orders = serializers.IntegerField()
    previous_date = serializers.DateField(help_text="The same day of the previous period")
    previous_revenue = serializers.FloatField()


class SalesChartSerializer(serializers.Serializer):
    step = serializers.ChoiceField(choices=(DAY,))
    points = SalesChartPointSerializer(many=True)


class SalesCategorySerializer(serializers.Serializer):
    category = ProductCategoryShortSerializer()
    revenue = serializers.FloatField()
    percent = serializers.FloatField(help_text="Share in the products revenue of the range")


class SalesShareSerializer(serializers.Serializer):
    orders = serializers.IntegerField()
    revenue = serializers.FloatField()
    orders_percent = serializers.FloatField()
    revenue_percent = serializers.FloatField()


class SalesPaymentMethodSerializer(SalesShareSerializer):
    key = serializers.ChoiceField(choices=PAYMENT_KEYS)


class SalesDeliveryTypeSerializer(SalesShareSerializer):
    key = serializers.ChoiceField(choices=DELIVERY_KEYS)


class SalesProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "product_code", "articul_code")


class SalesTopProductSerializer(serializers.Serializer):
    product = SalesProductSerializer()
    quantity = serializers.IntegerField()
    revenue = serializers.FloatField()
    change = serializers.FloatField(allow_null=True, help_text="Revenue % vs the previous period, "
                                                               "null if it was not sold then")


class SalesRefundedProductSerializer(serializers.Serializer):
    product = SalesProductSerializer()
    quantity = serializers.IntegerField()
    orders = serializers.IntegerField(help_text="Refunded orders with the product")


class SalesCohortSerializer(serializers.Serializer):
    month = serializers.DateField(help_text="First day of the month of the first order")
    customers = serializers.IntegerField(help_text="Customers whose first order was in the month")
    percents = serializers.ListField(
        child=serializers.FloatField(allow_null=True),
        help_text="[i] = % of them who ordered again by the end of the (i + 1)-th month after it, "
                  "null while that month has not started")


class SalesCohortsSerializer(serializers.Serializer):
    offsets = serializers.IntegerField(help_text="Length of `percents`")
    rows = SalesCohortSerializer(many=True)


class SalesAnalyticsSerializer(serializers.Serializer):
    summary = SalesSummarySerializer()
    chart = SalesChartSerializer()
    categories = SalesCategorySerializer(many=True)
    payment_methods = SalesPaymentMethodSerializer(many=True)
    delivery_types = SalesDeliveryTypeSerializer(many=True)
    top_products = SalesTopProductSerializer(many=True)
    refunded_products = SalesRefundedProductSerializer(many=True)
    cohorts = SalesCohortsSerializer()
