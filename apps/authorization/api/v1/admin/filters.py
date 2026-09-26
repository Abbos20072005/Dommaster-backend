from datetime import timedelta
import django_filters
from django.utils import timezone
from apps.authorization.models import Customer

ACTIVE_DAYS = 30


def active_since():
    return timezone.now() - timedelta(days=ACTIVE_DAYS)


class CustomerFilter(django_filters.FilterSet):
    role = django_filters.ChoiceFilter(choices=Customer.Role.choices)
    is_active = django_filters.BooleanFilter(method="filter_is_active", label=f"Logged in within {ACTIVE_DAYS} days")
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    has_orders = django_filters.BooleanFilter(method="filter_has_orders")

    class Meta:
        model = Customer
        fields = ("role", "verified", "is_blocked")

    def filter_is_active(self, queryset, name, value):
        lookup = {"last_login__gte": active_since()}
        return queryset.filter(**lookup) if value else queryset.exclude(**lookup)

    def filter_has_orders(self, queryset, name, value):
        # `orders_count` is annotated in CustomerViewSet.get_queryset
        return queryset.filter(orders_count__gt=0) if value else queryset.filter(orders_count=0)
