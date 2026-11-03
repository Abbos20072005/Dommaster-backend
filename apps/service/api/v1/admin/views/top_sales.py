"""Top categories / brands / customers by the amount sold.

"Sold" = the dashboard revenue card rule ("Umumiy daromad", `order_kpis`): orders now in status Completed, by the day
they were created, their `total_price` (goods after discounts and the promocode + delivery). Every other status is not
counted, Canceled included; the payment status is not looked at. Categories and brands split an order's `total_price`
over its items by item sums (unit price at order time × quantity, `pro.allocate`), so every list adds up to the card."""
from collections import defaultdict

from django.db.models import Count, Max, Min, Sum
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.authorization.activity import mask_phone
from apps.authorization.models import Customer
from apps.service.models import Brand, Order, OrderItem, ProductCategory
from apps.service.pro import ZERO, allocate, money
from utils.admin_views import AdminViewMixin
from ..serializers import TopSalesQuerySerializer, TopSalesSerializer, TopCustomersSerializer, CUSTOM, COMPLETED
from ..serializers.top_sales import ALL_TIME
from .dashboard import percent
from .statuses import period_range

TOP = 10
CATEGORY = "product__product_item_category__product_sub_category__product_category"


def sales_range(params):
    """(period, date_from, date_to); all_time starts on the day of the first order (None without orders)."""
    if "date_from" in params:
        return CUSTOM, params["date_from"], params["date_to"]
    period = params["period"]
    if period == ALL_TIME:
        first = Order.objects.aggregate(first=Min("created_at"))["first"]
        return period, first and first.date(), timezone.now().date()
    return period, *period_range(period)


def sold_orders(date_from, date_to):
    orders = Order.objects.filter(status=COMPLETED, created_at__date__lte=date_to)
    return orders.filter(created_at__date__gte=date_from) if date_from else orders


def item_shares(orders):
    """[(order_id, category_id, brand_id, amount)]: each order's total_price split over its items;
    an order without items is one row without a category / brand."""
    totals = dict(orders.values_list("id", "total_price"))
    items = defaultdict(list)
    for row in OrderItem.objects.filter(order_id__in=totals).order_by("order_id", "id").values_list(
            "order_id", "quantity", "unit_price", "product__price", "product__discount_price", CATEGORY,
            "product__brand_id"):
        items[row[0]].append(row)

    shares = []
    for order_id, total in totals.items():
        rows = items.get(order_id)
        if not rows:
            shares.append((order_id, None, None, money(total)))
            continue
        # items older than `unit_price`: what the product costs now (OrderItem.unit_price_of)
        weights = [(unit if unit is not None else money(discount if discount is not None else price)) * quantity
                   for _, quantity, unit, price, discount, _, _ in rows]
        for row, amount in zip(rows, allocate(total, weights)):
            shares.append((order_id, row[5], row[6], amount))
    return shares


def ranking(shares, index, model, total):
    """Top rows of one key of `shares` + «others» (the rest merged)."""
    amounts, orders = defaultdict(lambda: ZERO), defaultdict(set)
    for share in shares:
        amounts[share[index]] += share[3]
        orders[share[index]].add(share[0])
    keys = sorted(amounts, key=lambda key: (-amounts[key], key is None, key or 0))
    top, rest = keys[:TOP], keys[TOP:]
    names = model.objects.in_bulk([key for key in top if key is not None])

    def share(amount, order_ids):
        return {"amount": float(amount), "orders_count": len(order_ids), "percent": percent(amount, total)}

    rest_orders = set().union(*(orders[key] for key in rest))
    return {
        "items": [{"id": key, "name": names[key].name if key in names else None, **share(amounts[key], orders[key])}
                  for key in top],
        "others": {"count": len(rest), **share(sum((amounts[key] for key in rest), ZERO), rest_orders)},
    }


class SalesAPIViewMixin(AdminViewMixin):
    filter_backends = []
    pagination_class = None

    def sales_range(self, request):
        params = TopSalesQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        return sales_range(params.validated_data)


class TopSalesAPIView(SalesAPIViewMixin, GenericAPIView):
    """Top 10 root categories and top 10 brands by the amount sold + «others»: ?period= or ?date_from=&date_to=."""
    serializer_class = TopSalesSerializer

    def get(self, request):
        period, date_from, date_to = self.sales_range(request)
        orders = sold_orders(date_from, date_to)
        shares = item_shares(orders)
        total = sum((share[3] for share in shares), ZERO)
        data = {"period": period, "date_from": date_from, "date_to": date_to, "total": float(total),
                "orders_count": len({share[0] for share in shares}),
                "categories": ranking(shares, 1, ProductCategory, total),
                "brands": ranking(shares, 2, Brand, total)}
        return Response(self.get_serializer(data).data)


class TopCustomersAPIView(SalesAPIViewMixin, GenericAPIView):
    """Top 10 customers by the amount sold to them: ?period= or ?date_from=&date_to=. Phones masked."""
    serializer_class = TopCustomersSerializer

    def get(self, request):
        period, date_from, date_to = self.sales_range(request)
        orders = sold_orders(date_from, date_to)
        summary = orders.aggregate(total=Sum("total_price"), orders_count=Count("id"))
        total = summary["total"] or 0.0
        rows = list(orders.exclude(customer=None).values("customer")
                    .annotate(amount=Sum("total_price"), orders_count=Count("id"), last_order_at=Max("created_at"))
                    .order_by("-amount", "customer")[:TOP])
        customers = Customer.objects.in_bulk([row["customer"] for row in rows])
        result = []
        for row in rows:
            customer = customers[row["customer"]]
            result.append({"id": customer.id, "full_name": customer.full_name,
                           "phone_number": mask_phone(customer.phone_number), "role": customer.role,
                           "is_pro": customer.is_pro, "is_deleted": customer.is_deleted,
                           "orders_count": row["orders_count"], "amount": row["amount"],
                           "percent": percent(row["amount"], total), "last_order_at": row["last_order_at"]})
        data = {"period": period, "date_from": date_from, "date_to": date_to, "total": total,
                "orders_count": summary["orders_count"], "customers": result}
        return Response(self.get_serializer(data).data)
