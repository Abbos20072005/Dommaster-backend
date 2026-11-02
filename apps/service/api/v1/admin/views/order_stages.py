from collections import defaultdict
from datetime import datetime
from statistics import mean, median
from django.db.models import Min
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from apps.service.models import Order, OrderStatusChange
from utils.admin_views import AdminViewMixin
from ..serializers import OrderStagesQuerySerializer, OrderStagesSerializer, STAGE_PERIOD_MONTHS, COURIER, \
    PICKUP_METHOD
from .dashboard import month_starts

# metric -> (start, end): "created" = Order.created_at, a status = the first time the order got it
STAGES = {
    "confirm": ("created", Order.CONFIRMED),
    "to_preparing": (Order.CONFIRMED, Order.COLLECTING),
    "delivery": ("created", Order.COMPLETED),
}
END_STATUSES = [end for _, end in STAGES.values()]
DELIVERY_TYPES = {COURIER: Order.DELIVERY, PICKUP_METHOD: Order.PICKUP}


def first_status_times(start, delivery_method):
    """{order_id: {"created": dt, status: first time it got the status}} of the not canceled orders that
    finished a stage on or after `start`."""
    orders = Order.objects.exclude(status=Order.CANCELED)
    if delivery_method in DELIVERY_TYPES:
        orders = orders.filter(delivery_type=DELIVERY_TYPES[delivery_method])
    firsts = OrderStatusChange.objects.filter(order__in=orders).values("order_id", "to_status") \
        .annotate(at=Min("created_at")).order_by()
    ids = firsts.filter(to_status__in=END_STATUSES, at__gte=start).values("order_id")
    times = defaultdict(dict)
    for order_id, created_at in Order.objects.filter(id__in=ids).values_list("id", "created_at"):
        times[order_id]["created"] = created_at
    for row in firsts.filter(order_id__in=ids, to_status__in=END_STATUSES):
        times[row["order_id"]][row["to_status"]] = row["at"]
    return times


def metric(durations):
    if not durations:
        return {"avg_seconds": None, "median_seconds": None, "count": 0}
    return {"avg_seconds": round(mean(durations)), "median_seconds": round(median(durations)),
            "count": len(durations)}


def get_months(period, delivery_method):
    starts = month_starts(STAGE_PERIOD_MONTHS[period])
    keys = [month.strftime("%Y-%m") for month in starts]
    durations = {key: defaultdict(list) for key in keys}
    start = datetime.combine(starts[0], datetime.min.time())
    for times in first_status_times(start, delivery_method).values():
        for name, (begin, end) in STAGES.items():
            if begin not in times or end not in times or times[end] < times[begin]:
                continue
            key = times[end].strftime("%Y-%m")
            if key in durations:
                durations[key][name].append((times[end] - times[begin]).total_seconds())
    return [{"month": key, **{name: metric(durations[key][name]) for name in STAGES}} for key in keys]


class OrderStagesAPIView(AdminViewMixin, GenericAPIView):
    """Time orders spend between stages, by month: ?period=quarter|half_year|year,
    ?delivery_method=all|courier|pickup. Read from the status log (`OrderStatusChange`), canceled orders left out."""
    serializer_class = OrderStagesSerializer
    filter_backends = []
    pagination_class = None

    def get(self, request):
        params = OrderStagesQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        period, delivery_method = params.validated_data["period"], params.validated_data["delivery_method"]
        data = {"period": period, "delivery_method": delivery_method, "months": get_months(period, delivery_method)}
        return Response(self.get_serializer(data).data)
