from datetime import timedelta
from django.db.models import Count
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from apps.service.models import Order, Product
from apps.service.models.choices import ORDER_STATUS, PUBLISH_STATUS
from utils.admin_views import AdminViewMixin
from ..serializers import OrderStatusesQuerySerializer, OrderStatusesSerializer, ProductStatusesSerializer, \
    CURRENT_MONTH, LAST_MONTH, LAST_3_MONTHS, CUSTOM
from .dashboard import percent, month_starts

ORDER_STATUSES = [value for value, _ in ORDER_STATUS]
PUBLISH_STATUSES = [value for value, _ in PUBLISH_STATUS]


def period_range(period):
    """(date_from, date_to) of a period, the last day incl."""
    today = timezone.now().date()
    if period == LAST_MONTH:
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    months = 1 if period == CURRENT_MONTH else 3 if period == LAST_3_MONTHS else 12
    return month_starts(months)[0], today


def shares(counts, values, key):
    total = sum(counts.values())
    return [{key: value, "count": counts.get(value, 0), "percent": percent(counts.get(value, 0), total)}
            for value in values]


class OrderStatusesAPIView(AdminViewMixin, GenericAPIView):
    """Orders created in the period (Tashkent date) by their current status: ?period= or ?date_from=&date_to=."""
    serializer_class = OrderStatusesSerializer
    filter_backends = []
    pagination_class = None

    def get(self, request):
        params = OrderStatusesQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data
        if "date_from" in data:
            period, (date_from, date_to) = CUSTOM, (data["date_from"], data["date_to"])
        else:
            period = data["period"]
            date_from, date_to = period_range(period)
        rows = Order.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to) \
            .values("status").annotate(n=Count("id")).order_by()
        counts = {row["status"]: row["n"] for row in rows}
        result = {"period": period, "date_from": date_from, "date_to": date_to, "total": sum(counts.values()),
                  "statuses": shares(counts, ORDER_STATUSES, "status")}
        return Response(self.get_serializer(result).data)


class ProductStatusesAPIView(AdminViewMixin, GenericAPIView):
    """All products now: by `publish_status` and by `is_active`."""
    serializer_class = ProductStatusesSerializer
    filter_backends = []
    pagination_class = None

    def get(self, request):
        rows = list(Product.objects.values("publish_status", "is_active").annotate(n=Count("id")).order_by())
        by_status, by_activity = {}, {}
        for row in rows:
            by_status[row["publish_status"]] = by_status.get(row["publish_status"], 0) + row["n"]
            by_activity[row["is_active"]] = by_activity.get(row["is_active"], 0) + row["n"]
        result = {"total": sum(row["n"] for row in rows),
                  "publish_statuses": shares(by_status, PUBLISH_STATUSES, "publish_status"),
                  "activity": shares(by_activity, (True, False), "is_active")}
        return Response(self.get_serializer(result).data)
