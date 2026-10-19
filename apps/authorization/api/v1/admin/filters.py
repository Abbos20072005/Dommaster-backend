from datetime import timedelta
import django_filters
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.authorization.models import Customer, StaffProfile

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


class StaffFilter(django_filters.FilterSet):
    access_level = django_filters.ChoiceFilter(choices=StaffProfile.AccessLevel.choices,
                                               method="filter_access_level")
    status = django_filters.ChoiceFilter(choices=StaffProfile.Status.choices, method="filter_status")

    class Meta:
        model = get_user_model()
        fields = ()

    def filter_access_level(self, queryset, name, value):
        return queryset.filter(is_superuser=value == StaffProfile.AccessLevel.SUPER_ADMIN)

    def filter_status(self, queryset, name, value):
        return queryset.filter(is_active=value == StaffProfile.Status.ACTIVE)
