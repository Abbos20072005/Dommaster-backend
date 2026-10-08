from datetime import date, timedelta
from django.db.models import Avg, Count, DateField, Exists, F, Max, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from apps.authorization.api.v1.admin.filters import active_since
from apps.authorization.models import Customer, FcmToken
from apps.base.models import Chat, Messages
from apps.service.models import Manager, Order, Product, ProductCategory, ProductImage, ProductRemaining, \
    Questions, QuestionsReply
from utils.admin_views import AdminViewMixin
from ..serializers import DashboardQuerySerializer, DashboardSerializer, PERIOD_DAYS, PERIOD_PLAN_MONTHS, YEAR, DAY, \
    MONTH_STEP, PENDING, COMPLETED, CANCELED

PENDING_ORDER_HOURS = 2
RECENT_ORDERS = 5
PRORAB = Customer.Role.PRORAB


def percent_change(current, previous):
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def percent(part, total):
    return round(part / total * 100, 1) if total else 0.0


def day_range(days):
    """Last `days` calendar days incl. today: (start, previous_start, dates)."""
    today = timezone.now().date()  # USE_TZ=False -> naive local time
    start = today - timedelta(days=days - 1)
    return start, start - timedelta(days=days), [start + timedelta(days=i) for i in range(days)]


def month_starts(months):
    """First days of the last `months` months incl. the current one, oldest first."""
    today = timezone.now().date()
    index = today.year * 12 + today.month - 1
    return [date(i // 12, i % 12 + 1, 1) for i in range(index - months + 1, index + 1)]


def period_buckets(period):
    """Chart points of a period: (start, previous_start, dates, step, trunc).
    week / month = last 7 / 30 days by day, year = last 12 calendar months (incl. the current one) by month."""
    if period == YEAR:
        months = month_starts(24)
        return months[12], months[0], months[12:], MONTH_STEP, TruncMonth("created_at", output_field=DateField())
    return *day_range(PERIOD_DAYS[period]), DAY, TruncDate("created_at")


def summary_range(params):
    """KPI cards range: explicit ?date_from=&date_to= or the last ?days= incl. today."""
    if "date_from" in params:
        return params["date_from"], params["date_to"]
    end = timezone.now().date()
    return end - timedelta(days=params["days"] - 1), end


def get_summary(start, end):
    """KPI cards over start..end (inclusive) vs the previous range of the same length."""
    days = (end - start).days + 1
    prev_start = start - timedelta(days=days)
    in_ranges = Q(created_at__date__range=(prev_start, end))
    current, previous = Q(created_at__date__gte=start), Q(created_at__date__lt=start)
    completed = Q(status=COMPLETED)

    orders = Order.objects.filter(in_ranges).aggregate(
        orders=Count("id", filter=current),
        prev_orders=Count("id", filter=previous),
        revenue=Coalesce(Sum("total_price", filter=current & completed), 0.0),
        prev_revenue=Coalesce(Sum("total_price", filter=previous & completed), 0.0),
        average_check=Coalesce(Avg("total_price", filter=current & completed), 0.0),
        prev_average_check=Coalesce(Avg("total_price", filter=previous & completed), 0.0),
    )
    customers = Customer.objects.filter(in_ranges).aggregate(
        new_customers=Count("id", filter=current),
        prev_new_customers=Count("id", filter=previous),
    )
    values = {**orders, **customers}
    data = {"days": days, "date_from": start, "date_to": end}
    for key in ("orders", "revenue", "average_check", "new_customers"):
        data[key] = {"value": values[key], "change": percent_change(values[key], values[f"prev_{key}"])}
    return data


def get_delivered_orders(period):
    """Completed orders per day (per month for a year) over the period vs the previous one."""
    start, prev_start, dates, step, trunc = period_buckets(period)
    rows = Order.objects.filter(status=COMPLETED, created_at__date__gte=prev_start) \
        .annotate(day=trunc).values("day") \
        .annotate(count=Count("id"), revenue=Coalesce(Sum("total_price"), 0.0))
    by_day = {row["day"]: row for row in rows}

    points = []
    for day in dates:
        row = by_day.get(day, {"count": 0, "revenue": 0.0})
        points.append({"date": day, "count": row["count"], "revenue": row["revenue"],
                       "average_check": row["revenue"] / row["count"] if row["count"] else 0.0})
    revenue = sum(p["revenue"] for p in points)
    prev_revenue = sum(row["revenue"] for day, row in by_day.items() if day < start)
    return {
        "period": period,
        "step": step,
        "count": sum(p["count"] for p in points),
        "revenue": revenue,
        "change": percent_change(revenue, prev_revenue),
        "points": points,
    }


def get_registrations(period):
    """New customers per day (per month for a year) + mobile/web split."""
    start, _, dates, step, trunc = period_buckets(period)
    has_fcm = Q(Exists(FcmToken.objects.filter(customer=OuterRef("pk"))))
    rows = Customer.objects.filter(created_at__date__gte=start) \
        .annotate(day=trunc).values("day") \
        .annotate(count=Count("id"), mobile=Count("id", filter=has_fcm))
    by_day = {row["day"]: row for row in rows}

    total = sum(row["count"] for row in by_day.values())
    mobile = sum(row["mobile"] for row in by_day.values())
    return {
        "period": period,
        "step": step,
        "days": (timezone.now().date() - start).days + 1,
        "total": total,
        "mobile": mobile,
        "web": total - mobile,
        "mobile_percent": percent(mobile, total),
        "web_percent": percent(total - mobile, total),
        "points": [{"date": day, "count": by_day.get(day, {}).get("count", 0)} for day in dates],
    }


def get_recent_orders(limit=RECENT_ORDERS):
    return Order.objects.select_related("customer", "manager").annotate(items_count=Count("order_items")) \
        .order_by("-created_at")[:limit]


def get_attention():
    """Things that need an admin's action."""
    out_of_stock = Product.objects.filter(is_active=True, quantity__lte=0)
    category_field = "product_item_category__product_sub_category__product_category"
    top_ids = [row[category_field] for row in out_of_stock.exclude(**{category_field: None})
               .values(category_field).annotate(count=Count("id")).order_by("-count")[:2]]
    categories = {c.id: c.name for c in ProductCategory.objects.filter(id__in=top_ids)}

    last_message_is_answer = Messages.objects.filter(chat=OuterRef("pk")) \
        .order_by("-created_at", "-id").values("is_answer")[:1]
    counters = {
        "out_of_stock": out_of_stock.count(),
        "stale_pending_orders": Order.objects.filter(
            status=PENDING, created_at__lt=timezone.now() - timedelta(hours=PENDING_ORDER_HOURS)).count(),
        "unanswered_questions": Questions.objects.filter(is_visible=True)
        .exclude(question_reply__is_admin=True).count(),
        "unanswered_chats": Chat.objects.annotate(last_is_answer=Subquery(last_message_is_answer))
        .filter(last_is_answer=False).count(),
        "moderation_queue": QuestionsReply.objects.filter(is_visible=False, is_admin=False).count(),
    }
    return {
        "total": sum(counters.values()),
        **counters,
        "out_of_stock_categories": [categories[i] for i in top_ids if i in categories],
        "pending_hours": PENDING_ORDER_HOURS,
        "last_stock_sync": ProductRemaining.objects.aggregate(last=Max("created_at"))["last"],
    }


def get_customers():
    """Customers split into disjoint groups (individual + b2b + unverified = total)."""
    data = Customer.objects.aggregate(
        total=Count("id"),
        individual=Count("id", filter=Q(verified=True) & ~Q(role=PRORAB)),
        b2b=Count("id", filter=Q(verified=True, role=PRORAB)),
        unverified=Count("id", filter=Q(verified=False)),
        active=Count("id", filter=Q(last_login__gte=active_since())),
        blocked=Count("id", filter=Q(is_blocked=True)),
    )
    buyers = Order.objects.exclude(status=CANCELED).exclude(customer=None) \
        .values("customer").annotate(orders=Count("id"))
    data["repeat_purchase_percent"] = percent(buyers.filter(orders__gte=2).count(), buyers.count())
    return data


def get_catalog(low):
    """Stock state of active products, `low` = low stock threshold."""
    active = Q(is_active=True)
    data = Product.objects.annotate(has_image=Exists(ProductImage.objects.filter(product=OuterRef("pk")))) \
        .aggregate(
            total=Count("id", filter=active),
            in_stock=Count("id", filter=active & Q(quantity__gt=low)),
            low_stock=Count("id", filter=active & Q(quantity__gt=0, quantity__lte=low)),
            out_of_stock=Count("id", filter=active & Q(quantity__lte=0)),
            incomplete=Count("id", filter=active & (Q(has_image=False) | Q(price__lte=0))),
            inactive=Count("id", filter=Q(is_active=False)),
        )
    data["low_stock_threshold"] = low
    return data


def get_revenue(months):
    """Completed orders revenue per month, B2B (prorab) vs individual."""
    starts = month_starts(months)
    is_b2b = Q(customer__role=PRORAB)
    rows = Order.objects.filter(status=COMPLETED, created_at__date__gte=starts[0]) \
        .annotate(month=TruncMonth("created_at", output_field=DateField())).values("month") \
        .annotate(b2b=Coalesce(Sum("total_price", filter=is_b2b), 0.0),
                  individual=Coalesce(Sum("total_price", filter=~is_b2b), 0.0))
    by_month = {row["month"]: row for row in rows}

    points = [{"month": m, "b2b": by_month.get(m, {}).get("b2b", 0.0),
               "individual": by_month.get(m, {}).get("individual", 0.0)} for m in starts]
    return {
        "b2b": sum(p["b2b"] for p in points),
        "individual": sum(p["individual"] for p in points),
        "months": points,
    }


def get_chat_response_minutes(start, end):
    """Average minutes from a customer's chat message to the staff answer. A run of customer messages
    counts once, from its first message; runs still unanswered are skipped."""
    in_chat = Messages.objects.filter(chat=OuterRef("chat"))
    previous_is_answer = in_chat.filter(created_at__lt=OuterRef("created_at")) \
        .order_by("-created_at", "-id").values("is_answer")[:1]
    answered_at = in_chat.filter(is_answer=True, created_at__gt=OuterRef("created_at")) \
        .order_by("created_at").values("created_at")[:1]
    average = Messages.objects.filter(is_answer=False, created_at__date__range=(start, end)) \
        .annotate(previous_is_answer=Subquery(previous_is_answer), answered_at=Subquery(answered_at)) \
        .filter(Q(previous_is_answer=True) | Q(previous_is_answer__isnull=True), answered_at__isnull=False) \
        .aggregate(average=Avg(F("answered_at") - F("created_at")))["average"]
    return round(average.total_seconds() / 60) if average is not None else None


def get_managers_plan(period):
    """Active managers' completed revenue over the period vs their plan + team totals."""
    start, end = period_buckets(period)[0], timezone.now().date()
    in_period = Q(status=COMPLETED, created_at__date__range=(start, end))
    by_manager = {row["manager"]: row for row in Order.objects.filter(in_period).exclude(manager=None)
                  .values("manager").annotate(revenue=Coalesce(Sum("total_price"), 0.0), orders_count=Count("id"))}

    managers = []
    for manager in Manager.objects.filter(is_active=True).order_by("full_name"):
        row = by_manager.get(manager.id, {"revenue": 0.0, "orders_count": 0})
        plan = float(manager.monthly_plan) * PERIOD_PLAN_MONTHS[period]
        managers.append({"id": manager.id, "full_name": manager.full_name, "plan": plan, "revenue": row["revenue"],
                         "orders_count": row["orders_count"],
                         "percent": percent(row["revenue"], plan) if plan else None})
    managers.sort(key=lambda m: (m["percent"] is None, -(m["percent"] or 0)))

    with_plan = [m for m in managers if m["plan"]]
    plan, revenue = sum(m["plan"] for m in with_plan), sum(m["revenue"] for m in with_plan)
    totals = Order.objects.filter(in_period).aggregate(
        total=Coalesce(Sum("total_price"), 0.0),
        b2b=Coalesce(Sum("total_price", filter=Q(customer__role=PRORAB)), 0.0),
    )
    return {
        "period": period,
        "date_from": start,
        "date_to": end,
        "plan": plan,
        "revenue": revenue,
        "team_percent": percent(revenue, plan) if plan else None,
        "b2b_percent": percent(totals["b2b"], totals["total"]),
        "chat_response_minutes": get_chat_response_minutes(start, end),
        "managers": managers,
    }


class DashboardAPIView(AdminViewMixin, GenericAPIView):
    """Admin home page, all widgets in one response.
    ?days= KPI window (30) or ?date_from=&date_to= instead of it, ?period=week|month|year charts and
    managers plan (week), ?months= revenue chart (6), ?low_stock= (10)."""
    serializer_class = DashboardSerializer
    filter_backends = []
    pagination_class = None

    def get(self, request):
        params = DashboardQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        params = params.validated_data
        data = {
            "summary": get_summary(*summary_range(params)),
            "delivered_orders": get_delivered_orders(params["period"]),
            "registrations": get_registrations(params["period"]),
            "recent_orders": get_recent_orders(),
            "attention": get_attention(),
            "customers": get_customers(),
            "catalog": get_catalog(params["low_stock"]),
            "revenue": get_revenue(params["months"]),
            "managers_plan": get_managers_plan(params["period"]),
        }
        return Response(self.get_serializer(data).data)
