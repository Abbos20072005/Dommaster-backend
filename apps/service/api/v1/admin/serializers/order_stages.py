from rest_framework import serializers
from .dashboard import QUARTER, HALF_YEAR, YEAR

STAGE_PERIOD_MONTHS = {QUARTER: 3, HALF_YEAR: 6, YEAR: 12}  # calendar months, the current one incl.
ALL_METHODS, COURIER, PICKUP_METHOD = "all", "courier", "pickup"
DELIVERY_METHODS = (ALL_METHODS, COURIER, PICKUP_METHOD)


class OrderStagesQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=tuple(STAGE_PERIOD_MONTHS), default=QUARTER,
                                     help_text="quarter / half_year / year = the last 3 / 6 / 12 calendar months, "
                                               "the current one incl.")
    delivery_method = serializers.ChoiceField(choices=DELIVERY_METHODS, default=ALL_METHODS,
                                              help_text="courier = delivery orders, pickup = pickup orders")


class StageMetricSerializer(serializers.Serializer):
    avg_seconds = serializers.IntegerField(allow_null=True, help_text="null = no order in the month")
    median_seconds = serializers.IntegerField(allow_null=True, help_text="null = no order in the month")
    count = serializers.IntegerField()


class OrderStagesMonthSerializer(serializers.Serializer):
    month = serializers.CharField(help_text="YYYY-MM, the month the stage ended in (Tashkent time)")
    confirm = StageMetricSerializer(help_text="Created -> first Confirmed")
    to_preparing = StageMetricSerializer(help_text="First Confirmed -> first Collecting")
    delivery = StageMetricSerializer(help_text="Created -> first Completed")


class OrderStagesSerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=tuple(STAGE_PERIOD_MONTHS))
    delivery_method = serializers.ChoiceField(choices=DELIVERY_METHODS)
    months = OrderStagesMonthSerializer(many=True, help_text="Oldest first")
