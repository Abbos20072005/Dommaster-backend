from rest_framework import serializers

CURRENT_MONTH, LAST_MONTH, LAST_3_MONTHS, LAST_YEAR, CUSTOM = "current_month", "last_month", "last_3_months", \
    "year", "custom"
STATUS_PERIODS = (CURRENT_MONTH, LAST_MONTH, LAST_3_MONTHS, LAST_YEAR)


class OrderStatusesQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=STATUS_PERIODS, default=CURRENT_MONTH,
                                     help_text="current_month / last_month = calendar months, last_3_months / year = "
                                               "the last 3 / 12 calendar months, the current one incl.; "
                                               "ignored when date_from + date_to are sent")
    date_from = serializers.DateField(required=False, help_text="Range start, sent together with date_to")
    date_to = serializers.DateField(required=False, help_text="Range end (inclusive)")

    def validate(self, attrs):
        date_from, date_to = attrs.get("date_from"), attrs.get("date_to")
        if (date_from is None) != (date_to is None):
            missing = "date_to" if date_to is None else "date_from"
            raise serializers.ValidationError({missing: "date_from and date_to are sent together."})
        if date_from and date_from > date_to:
            raise serializers.ValidationError({"date_to": "Must not be earlier than date_from."})
        return attrs


class StatusShareSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    percent = serializers.FloatField(help_text="Share of `total`, %, 1 decimal; 0 when total is 0")


class OrderStatusShareSerializer(StatusShareSerializer):
    status = serializers.IntegerField(help_text="Order status code, `orders/?status=`")


class OrderStatusesSerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=(*STATUS_PERIODS, CUSTOM), help_text="custom = date_from + date_to sent")
    date_from = serializers.DateField(help_text="= `orders/?from_created=`")
    date_to = serializers.DateField(help_text="= `orders/?to_created=`")
    total = serializers.IntegerField(help_text="Orders created in the range, every status")
    statuses = OrderStatusShareSerializer(many=True, help_text="Every status in code order, zeros incl.")


class PublishStatusShareSerializer(StatusShareSerializer):
    publish_status = serializers.CharField(help_text="`products/?publish_status=`")


class ActivityShareSerializer(StatusShareSerializer):
    is_active = serializers.BooleanField(help_text="`products/?is_active=`")


class ProductStatusesSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="All products = `products/` count")
    publish_statuses = PublishStatusShareSerializer(many=True, help_text="draft / review / published")
    activity = ActivityShareSerializer(many=True, help_text="active / inactive (shown to customers or not)")
