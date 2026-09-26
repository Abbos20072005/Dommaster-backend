import django_filters
from apps.service.models import Order, ORDER_STATUS


class OrderFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=ORDER_STATUS, label="?status=0&status=1")
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    min_total = django_filters.NumberFilter(field_name="total_price", lookup_expr="gte")
    max_total = django_filters.NumberFilter(field_name="total_price", lookup_expr="lte")

    class Meta:
        model = Order
        fields = ("id", "payment_status", "payment_type", "payment_method", "delivery_type", "customer",
                  "pickup_branch")
