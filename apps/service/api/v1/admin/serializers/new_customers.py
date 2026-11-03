from rest_framework import serializers

LAST_6_MONTHS, LAST_12_MONTHS, ALL_TIME = "6_months", "12_months", "all_time"
NEW_CUSTOMERS_PERIODS = (LAST_6_MONTHS, LAST_12_MONTHS, ALL_TIME)


class NewCustomersQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=NEW_CUSTOMERS_PERIODS, default=LAST_12_MONTHS,
                                     help_text="6_months / 12_months = the last 6 / 12 calendar months, the current "
                                               "one incl.; all_time = from the month of the first customer")


class NewCustomersCountSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="= app + site")
    app = serializers.IntegerField(help_text="Registered in the mobile app (iOS / Android)")
    site = serializers.IntegerField(help_text="Registered on the website")


class NewCustomersMonthSerializer(NewCustomersCountSerializer):
    month = serializers.DateField(help_text="First day of the month")


class NewCustomersSerializer(NewCustomersCountSerializer):
    period = serializers.ChoiceField(choices=NEW_CUSTOMERS_PERIODS)
    date_from = serializers.DateField(help_text="First day of the first month = `customers/?from_created=`")
    date_to = serializers.DateField(help_text="Today")
    months = NewCustomersMonthSerializer(many=True, help_text="Every month, oldest first, zeros incl.")
