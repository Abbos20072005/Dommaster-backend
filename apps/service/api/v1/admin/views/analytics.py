from datetime import date, timedelta
from django.db.models import Count, ExpressionWrapper, F, FloatField, OuterRef, Q, Subquery, Sum, Avg
from django.db.models.functions import Coalesce, TruncDate
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from apps.authorization.models import Customer
from apps.service.models import Order, OrderItem, Product, ProductCategory
from utils.admin_views import AdminViewMixin
from ..serializers import SalesAnalyticsQuerySerializer, SalesAnalyticsSerializer, COMPLETED, CANCELED, DELIVERY, \
    PAYMENT_ON_DELIVERY, DAY, CLICK, PAYME, UZUM, CASH, CARD, OTHER, PAYMENT_KEYS, DELIVERY_KEY, PICKUP_KEY, \
    DELIVERY_KEYS, CHANNEL_KEYS, B2B
from .dashboard import month_starts, percent, percent_change, summary_range

TOP_CATEGORIES = 8
TOP_PRODUCTS = 10
COHORT_MONTHS = 4
COHORT_OFFSETS = 3
# PAYMENT_STATUS Cancelled: set only after the money went back to the customer
REFUNDED = 3
PRORAB = Customer.Role.PRORAB
PAYMENT_TYPE_KEYS = {1: CLICK, 2: PAYME, 3: UZUM}
CATEGORY = "product__product_item_category__product_sub_category__product_category"
# OrderItem keeps no price: the product's current price, the same rule the order total is built with
ITEM_REVENUE = ExpressionWrapper(F("quantity") * Coalesce(F("product__discount_price"), F("product__price")),
                                 output_field=FloatField())


def previous_start(start, end):
    return start - timedelta(days=(end - start).days + 1)


def points_change(current, previous, comparable):
    """Difference of two rates in percentage points."""
    return round(current - previous, 1) if comparable else None


def shift_month(month, offset):
    index = month.year * 12 + month.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def scope(filters, prefix=""):
    """?channel= / ?segment= of the page as a Q over orders; `prefix` = path from the queried model to the order."""
    q = Q()
    if filters.get("channel"):
        q &= Q(**{f"{prefix}channel": filters["channel"]})
    if filters.get("segment"):
        is_b2b = Q(**{f"{prefix}customer__role": PRORAB})
        q &= is_b2b if filters["segment"] == B2B else ~is_b2b
    return q


def orders_of(filters):
    return Order.objects.filter(scope(filters))


def items_of(filters):
    return OrderItem.objects.filter(scope(filters, "order__"))


def completed_orders(start, end, filters):
    return orders_of(filters).filter(status=COMPLETED, created_at__date__range=(start, end))


def completed_items(start, end, filters):
    return items_of(filters).filter(order__status=COMPLETED, order__created_at__date__range=(start, end))


def repeat_buyers(start, end, filters):
    """(buyers of start..end, those of them with an earlier or one more non-canceled order by `end`).
    The filters pick the buyers; their other orders count whatever the channel is."""
    in_range = Q(created_at__date__gte=start) & scope(filters)
    buyers = Order.objects.exclude(status=CANCELED).exclude(customer=None).filter(created_at__date__lte=end) \
        .values("customer") \
        .annotate(total=Count("id"), in_range=Count("id", filter=in_range)) \
        .filter(in_range__gt=0)
    return buyers.count(), buyers.filter(total__gte=2).count()


def get_summary(start, end, filters):
    """KPI cards over start..end (inclusive) vs the previous range of the same length."""
    prev_start = previous_start(start, end)
    completed = Q(status=COMPLETED)
    aggregates = {}
    for prefix, in_range in (("", Q(created_at__date__gte=start)), ("prev_", Q(created_at__date__lt=start))):
        aggregates.update({
            f"{prefix}orders": Count("id", filter=in_range),
            f"{prefix}revenue": Coalesce(Sum("total_price", filter=in_range & completed), 0.0),
            f"{prefix}average_check": Coalesce(Avg("total_price", filter=in_range & completed), 0.0),
            f"{prefix}canceled": Count("id", filter=in_range & Q(status=CANCELED)),
            f"{prefix}refunded": Count("id", filter=in_range & Q(payment_status=REFUNDED)),
        })
    values = orders_of(filters).filter(created_at__date__range=(prev_start, end)).aggregate(**aggregates)

    data = {"days": (end - start).days + 1, "date_from": start, "date_to": end}
    for key in ("revenue", "orders", "average_check"):
        data[key] = {"value": values[key], "change": percent_change(values[key], values[f"prev_{key}"])}
    for key, counter in (("cancel_rate", "canceled"), ("refund_rate", "refunded")):
        rate = percent(values[counter], values["orders"])
        prev_rate = percent(values[f"prev_{counter}"], values["prev_orders"])
        data[key] = {"value": rate, "change": points_change(rate, prev_rate, values["prev_orders"])}

    buyers, repeat = repeat_buyers(start, end, filters)
    prev_buyers, prev_repeat = repeat_buyers(prev_start, start - timedelta(days=1), filters)
    rate = percent(repeat, buyers)
    data["repeat_rate"] = {"value": rate, "change": points_change(rate, percent(prev_repeat, prev_buyers), prev_buyers)}
    return data


def get_chart(start, end, filters):
    """Per day: completed orders revenue (+ the same day of the previous range) and all created orders."""
    days = (end - start).days + 1
    prev_start = previous_start(start, end)
    rows = orders_of(filters).filter(created_at__date__range=(prev_start, end)) \
        .annotate(day=TruncDate("created_at")).values("day") \
        .annotate(orders=Count("id"), revenue=Coalesce(Sum("total_price", filter=Q(status=COMPLETED)), 0.0))
    by_day = {row["day"]: row for row in rows}

    points = []
    for i in range(days):
        day, prev_day = start + timedelta(days=i), prev_start + timedelta(days=i)
        row = by_day.get(day, {})
        points.append({"date": day, "revenue": row.get("revenue", 0.0), "orders": row.get("orders", 0),
                       "previous_date": prev_day, "previous_revenue": by_day.get(prev_day, {}).get("revenue", 0.0)})
    return {"step": DAY, "points": points}


def get_categories(start, end, filters):
    """Top categories by the revenue of their products in completed orders."""
    rows = list(completed_items(start, end, filters).values(CATEGORY)
                .annotate(revenue=Coalesce(Sum(ITEM_REVENUE), 0.0)).order_by("-revenue"))
    total = sum(row["revenue"] for row in rows)
    top = [row for row in rows if row[CATEGORY]][:TOP_CATEGORIES]
    categories = ProductCategory.objects.in_bulk([row[CATEGORY] for row in top])
    return [{"category": categories[row[CATEGORY]], "revenue": row["revenue"],
             "percent": percent(row["revenue"], total)} for row in top]


def shares(rows, keys):
    """Completed orders grouped into `keys` (rows of key / orders / revenue) + their shares, biggest first."""
    data = {key: {"key": key, "orders": 0, "revenue": 0.0} for key in keys}
    for row in rows:
        data[row["key"]]["orders"] += row["orders"]
        data[row["key"]]["revenue"] += row["revenue"]
    orders = sum(item["orders"] for item in data.values())
    revenue = sum(item["revenue"] for item in data.values())
    for item in data.values():
        item["orders_percent"] = percent(item["orders"], orders)
        item["revenue_percent"] = percent(item["revenue"], revenue)
    return sorted(data.values(), key=lambda item: -item["revenue"])


def payment_key(payment_type, payment_method):
    if payment_type == PAYMENT_ON_DELIVERY:
        return payment_method if payment_method in (CASH, CARD) else OTHER
    return PAYMENT_TYPE_KEYS.get(payment_type, OTHER)


def get_channels(start, end, filters):
    rows = completed_orders(start, end, filters).values("channel") \
        .annotate(orders=Count("id"), revenue=Coalesce(Sum("total_price"), 0.0))
    return shares([{**row, "key": row["channel"] or OTHER} for row in rows], CHANNEL_KEYS)


def get_payment_methods(start, end, filters):
    rows = completed_orders(start, end, filters).values("payment_type", "payment_method") \
        .annotate(orders=Count("id"), revenue=Coalesce(Sum("total_price"), 0.0))
    return shares([{**row, "key": payment_key(row["payment_type"], row["payment_method"])} for row in rows],
                  PAYMENT_KEYS)


def get_delivery_types(start, end, filters):
    rows = completed_orders(start, end, filters).values("delivery_type") \
        .annotate(orders=Count("id"), revenue=Coalesce(Sum("total_price"), 0.0))
    return shares([{**row, "key": DELIVERY_KEY if row["delivery_type"] == DELIVERY else PICKUP_KEY} for row in rows],
                  DELIVERY_KEYS)


def with_products(rows):
    products = Product.objects.in_bulk([row["product"] for row in rows])
    return [{**row, "product": products[row["product"]]} for row in rows]


def get_top_products(start, end, filters):
    """Best sellers of completed orders by revenue, `change` vs the previous range."""
    current, previous = Q(order__created_at__date__gte=start), Q(order__created_at__date__lt=start)
    rows = completed_items(previous_start(start, end), end, filters).values("product").annotate(
        sold=Coalesce(Sum("quantity", filter=current), 0),
        revenue=Coalesce(Sum(ITEM_REVENUE, filter=current), 0.0),
        prev_revenue=Coalesce(Sum(ITEM_REVENUE, filter=previous), 0.0),
    ).filter(sold__gt=0).order_by("-revenue", "-sold")[:TOP_PRODUCTS]
    return with_products([{"product": row["product"], "quantity": row["sold"], "revenue": row["revenue"],
                           "change": percent_change(row["revenue"], row["prev_revenue"])} for row in rows])


def get_refunded_products(start, end, filters):
    """Products of the orders whose payment was returned (the whole order counts as returned)."""
    rows = items_of(filters).filter(order__payment_status=REFUNDED, order__created_at__date__range=(start, end)) \
        .values("product").annotate(returned=Coalesce(Sum("quantity"), 0), orders=Count("order", distinct=True)) \
        .order_by("-returned", "-orders")[:TOP_PRODUCTS]
    return with_products([{"product": row["product"], "quantity": row["returned"], "orders": row["orders"]}
                          for row in rows])


def get_cohorts():
    """Customers by the month of their first non-canceled order: % who ordered again by the end of the
    1st .. `COHORT_OFFSETS`-th month after it. Does not depend on the date range and the filters."""
    months = month_starts(COHORT_MONTHS)
    orders = Order.objects.exclude(status=CANCELED).filter(customer=OuterRef("pk")) \
        .order_by("created_at", "id").values("created_at")
    buyers = Customer.objects.annotate(first=Subquery(orders[:1]), second=Subquery(orders[1:2])) \
        .filter(first__gte=months[0]).values_list("first", "second")

    cohorts = {month: {"customers": 0, "repeat": [0] * COHORT_OFFSETS} for month in months}
    for first, second in buyers:
        month = first.date().replace(day=1)
        cohorts[month]["customers"] += 1
        for i in range(COHORT_OFFSETS):
            if second and second.date() < shift_month(month, i + 2):
                cohorts[month]["repeat"][i] += 1

    rows = []
    for month, cohort in cohorts.items():
        rows.append({"month": month, "customers": cohort["customers"], "percents": [
            percent(cohort["repeat"][i], cohort["customers"]) if shift_month(month, i + 1) <= months[-1] else None
            for i in range(COHORT_OFFSETS)]})
    return {"offsets": COHORT_OFFSETS, "rows": rows}


class SalesAnalyticsAPIView(AdminViewMixin, GenericAPIView):
    """"Sales analytics" page, all widgets in one response.
    ?days= window ending today (30) or ?date_from=&date_to= instead of it, ?channel=site|ios|android,
    ?segment=individual|b2b; the cohorts ignore all of them."""
    serializer_class = SalesAnalyticsSerializer
    filter_backends = []
    pagination_class = None

    def get(self, request):
        params = SalesAnalyticsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        filters = params.validated_data
        scoped = (*summary_range(filters), filters)
        data = {
            "summary": get_summary(*scoped),
            "chart": get_chart(*scoped),
            "channels": get_channels(*scoped),
            "categories": get_categories(*scoped),
            "payment_methods": get_payment_methods(*scoped),
            "delivery_types": get_delivery_types(*scoped),
            "top_products": get_top_products(*scoped),
            "refunded_products": get_refunded_products(*scoped),
            "cohorts": get_cohorts(),
        }
        return Response(self.get_serializer(data).data)
