from rest_framework import serializers
from .statuses import CURRENT_MONTH, LAST_3_MONTHS, LAST_YEAR, CUSTOM, OrderStatusesQuerySerializer

ALL_TIME = "all_time"
SALES_PERIODS = (CURRENT_MONTH, LAST_3_MONTHS, LAST_YEAR, ALL_TIME)


class TopSalesQuerySerializer(OrderStatusesQuerySerializer):
    period = serializers.ChoiceField(choices=SALES_PERIODS, default=CURRENT_MONTH,
                                     help_text="current_month = this calendar month, last_3_months / year = the last "
                                               "3 / 12 calendar months, the current one incl., all_time = whole "
                                               "history; ignored when date_from + date_to are sent")


class TopSalesRangeSerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=(*SALES_PERIODS, CUSTOM), help_text="custom = date_from + date_to sent")
    date_from = serializers.DateField(allow_null=True,
                                      help_text="= `orders/?from_created=`; all_time: day of the first order, "
                                                "null when there are no orders")
    date_to = serializers.DateField(help_text="= `orders/?to_created=`")
    total = serializers.FloatField(help_text="Sold over the range = the dashboard revenue card for the same dates")
    orders_count = serializers.IntegerField(help_text="Orders counted (completed ones)")


class TopSalesShareSerializer(serializers.Serializer):
    amount = serializers.FloatField(help_text="Sold, UZS")
    orders_count = serializers.IntegerField(help_text="Counted orders that hold at least one such item")
    percent = serializers.FloatField(help_text="Share of `total`, %, 1 decimal")


class TopSalesRowSerializer(TopSalesShareSerializer):
    id = serializers.IntegerField(allow_null=True, help_text="null = items without one (or an order without items)")
    name = serializers.CharField(allow_null=True)


class TopSalesOthersSerializer(TopSalesShareSerializer):
    count = serializers.IntegerField(help_text="Rows merged into «Boshqalar», 0 = none")


class TopSalesRankingSerializer(serializers.Serializer):
    items = TopSalesRowSerializer(many=True, help_text="Top 10 by amount, biggest first")
    others = TopSalesOthersSerializer(help_text="Everything after the top 10; items + others add up to `total`")


class TopSalesSerializer(TopSalesRangeSerializer):
    categories = TopSalesRankingSerializer(help_text="By the product's root category")
    brands = TopSalesRankingSerializer()


class TopCustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Customer card = `customers/<id>/`")
    full_name = serializers.CharField()
    phone_number = serializers.CharField(help_text="Masked; the full one = `customers/<id>/reveal-phone/`")
    role = serializers.CharField(help_text="user / prorab (now)")
    is_pro = serializers.BooleanField(help_text="role prorab = PRO, else B2C")
    is_deleted = serializers.BooleanField()
    orders_count = serializers.IntegerField()
    amount = serializers.FloatField(help_text="Sold to the customer over the range, UZS")
    percent = serializers.FloatField(help_text="Share of `total`, %, 1 decimal")
    last_order_at = serializers.DateTimeField(help_text="Last counted order of the range")


class TopCustomersSerializer(TopSalesRangeSerializer):
    customers = TopCustomerSerializer(many=True, help_text="Top 10 by amount, biggest first")
