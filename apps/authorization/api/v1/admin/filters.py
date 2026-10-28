import re
from datetime import timedelta
import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Exists, F, OuterRef, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from apps.authorization.models import Customer, StaffProfile

ACTIVE_DAYS = 30


def active_since():
    return timezone.now() - timedelta(days=ACTIVE_DAYS)


class CustomerSearchFilter(SearchFilter):
    """`?search=` of the customers list: name / phone / email as usual (`search_fields`), plus a query of digits
    only (spaces, `+`, `-`, brackets, `#`, `№` are ignored) = a part of the phone or the number of one of the
    customer's orders; `#28598` / `№28598` = the order number only."""
    search_description = "Name, part of the phone, email or an order number (#28598)"
    NUMBER_NOISE = re.compile(r"[\s+\-()#№]")

    def filter_queryset(self, request, queryset, view):
        search = (request.query_params.get(self.search_param) or "").replace("\x00", "").strip()
        number = self.NUMBER_NOISE.sub("", search)
        if search and number.isdigit():
            from apps.service.models import Order
            has_order = Exists(Order.objects.filter(customer=OuterRef("pk"), id=number))
            if search[0] in "#№":
                return queryset.filter(has_order)
            return queryset.filter(Q(phone_number__contains=number) | has_order)
        return super().filter_queryset(request, queryset, view)


class NullsLastOrderingFilter(OrderingFilter):
    """`?ordering=` with empty values (no orders, never logged in) at the end in both directions."""

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset
        return queryset.order_by(*[F(field[1:]).desc(nulls_last=True) if field.startswith("-")
                                   else F(field).asc(nulls_last=True) for field in ordering])


class CustomerFilter(django_filters.FilterSet):
    """The list leaves deleted customers out unless `is_deleted` is sent (CustomerViewSet.get_queryset)."""
    role = django_filters.ChoiceFilter(choices=Customer.Role.choices)
    is_active = django_filters.BooleanFilter(method="filter_is_active", label=f"Logged in within {ACTIVE_DAYS} days")
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    has_orders = django_filters.BooleanFilter(method="filter_has_orders")
    registration_channel = django_filters.CharFilter(
        method="filter_registration_channel",
        label="site / ios / android; several: ?registration_channel=ios&registration_channel=android or ios,android")
    segment = django_filters.ChoiceFilter(choices=Customer.Segment.choices)
    tag = django_filters.CharFilter(method="filter_tag", label="Customers with this tag")
    # orders_count / total_purchase / last_order_at / returns_count are annotated in CustomerViewSet.get_queryset
    orders_min = django_filters.NumberFilter(field_name="orders_count", lookup_expr="gte")
    orders_max = django_filters.NumberFilter(field_name="orders_count", lookup_expr="lte")
    purchase_min = django_filters.NumberFilter(field_name="total_purchase", lookup_expr="gte")
    purchase_max = django_filters.NumberFilter(field_name="total_purchase", lookup_expr="lte")
    last_order_from = django_filters.DateFilter(field_name="last_order_at", lookup_expr="date__gte")
    last_order_to = django_filters.DateFilter(field_name="last_order_at", lookup_expr="date__lte")
    has_returns = django_filters.BooleanFilter(method="filter_has_returns", label="Has canceled orders")
    is_deleted = django_filters.BooleanFilter()

    class Meta:
        model = Customer
        fields = ("role", "verified", "is_blocked")

    def filter_registration_channel(self, queryset, name, value):
        values = {v.strip() for raw in self.data.getlist(name) for v in raw.split(",") if v.strip()}
        unknown = values - set(Customer.Platform.values)
        if unknown:
            raise ValidationError({name: f"Unknown channel: {', '.join(sorted(unknown))}."})
        return queryset.filter(registration_channel__in=values) if values else queryset

    def filter_tag(self, queryset, name, value):
        return queryset.filter(tags__contains=[value.strip()])

    def filter_has_returns(self, queryset, name, value):
        return queryset.filter(returns_count__gt=0) if value else queryset.filter(returns_count=0)

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
