import django_filters
from apps.service.models import Order, Product, ORDER_STATUS


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


class ProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="product_item_category__product_sub_category__product_category")
    sub_category = django_filters.NumberFilter(field_name="product_item_category__product_sub_category")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")
    has_discount = django_filters.BooleanFilter(field_name="discount_price", lookup_expr="isnull", exclude=True)
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Product
        fields = ("brand", "product_item_category", "is_active", "unit")

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(quantity__gt=0) if value else queryset.filter(quantity__lte=0)
