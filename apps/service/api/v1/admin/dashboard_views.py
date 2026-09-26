from datetime import date, timedelta
from django.db.models import Avg, Count, DateField, Exists, Max, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from apps.authorization.api.v1.admin.filters import active_since
from apps.authorization.models import Customer, FcmToken
from apps.base.models import Chat, Messages
from apps.service.models import Order, Product, ProductCategory, ProductImage, ProductRemaining, Questions, \
    QuestionsReply
from utils.admin_views import AdminViewMixin
from .dashboard_serializers import DashboardQuerySerializer, DashboardSummarySerializer, DeliveredOrdersSerializer, \
    RegistrationsSerializer, AttentionSerializer, CustomersCompositionSerializer, CatalogSerializer, \
    RevenueSerializer, PERIOD_DAYS
from .serializers import PENDING, COMPLETED, CANCELED

PENDING_ORDER_HOURS = 2
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


class DashboardViewSet(AdminViewMixin, GenericViewSet):
    """Admin home page widgets, one endpoint per widget. Recent orders: `/orders/?page_size=5`."""
    filter_backends = []
    pagination_class = None

    def get_params(self):
        params = DashboardQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return params.validated_data

    def respond(self, data):
        return Response(self.get_serializer(data).data)

    @action(detail=False, methods=["get"], serializer_class=DashboardSummarySerializer)
    def summary(self, request):
        """KPI cards over the last `?days=` (default 30) vs the previous `days`."""
        days = self.get_params().get("days") or 30
        start, prev_start, _ = day_range(days)
        current, previous = Q(created_at__date__gte=start), Q(created_at__date__lt=start)
        completed = Q(status=COMPLETED)

        orders = Order.objects.filter(created_at__date__gte=prev_start).aggregate(
            orders=Count("id", filter=current),
            prev_orders=Count("id", filter=previous),
            revenue=Coalesce(Sum("total_price", filter=current & completed), 0.0),
            prev_revenue=Coalesce(Sum("total_price", filter=previous & completed), 0.0),
            average_check=Coalesce(Avg("total_price", filter=current & completed), 0.0),
            prev_average_check=Coalesce(Avg("total_price", filter=previous & completed), 0.0),
        )
        customers = Customer.objects.filter(created_at__date__gte=prev_start).aggregate(
            new_customers=Count("id", filter=current),
            prev_new_customers=Count("id", filter=previous),
        )
        values = {**orders, **customers}
        data = {"days": days}
        for key in ("orders", "revenue", "average_check", "new_customers"):
            data[key] = {"value": values[key], "change": percent_change(values[key], values[f"prev_{key}"])}
        return self.respond(data)

    @action(detail=False, methods=["get"], url_path="delivered-orders", serializer_class=DeliveredOrdersSerializer)
    def delivered_orders(self, request):
        """Completed orders per day: `?period=week` (7 days, default) or `month` (30 days)."""
        period = self.get_params()["period"]
        start, prev_start, dates = day_range(PERIOD_DAYS[period])
        rows = Order.objects.filter(status=COMPLETED, created_at__date__gte=prev_start) \
            .annotate(day=TruncDate("created_at")).values("day") \
            .annotate(count=Count("id"), revenue=Coalesce(Sum("total_price"), 0.0))
        by_day = {row["day"]: row for row in rows}

        points = []
        for day in dates:
            row = by_day.get(day, {"count": 0, "revenue": 0.0})
            points.append({"date": day, "count": row["count"], "revenue": row["revenue"],
                           "average_check": row["revenue"] / row["count"] if row["count"] else 0.0})
        revenue = sum(p["revenue"] for p in points)
        prev_revenue = sum(row["revenue"] for day, row in by_day.items() if day < start)
        return self.respond({
            "period": period,
            "count": sum(p["count"] for p in points),
            "revenue": revenue,
            "change": percent_change(revenue, prev_revenue),
            "points": points,
        })

    @action(detail=False, methods=["get"], serializer_class=RegistrationsSerializer)
    def registrations(self, request):
        """New customers per day over the last `?days=` (default 7) + mobile/web split."""
        days = self.get_params().get("days") or 7
        start, _, dates = day_range(days)
        has_fcm = Q(Exists(FcmToken.objects.filter(customer=OuterRef("pk"))))
        rows = Customer.objects.filter(created_at__date__gte=start) \
            .annotate(day=TruncDate("created_at")).values("day") \
            .annotate(count=Count("id"), mobile=Count("id", filter=has_fcm))
        by_day = {row["day"]: row for row in rows}

        total = sum(row["count"] for row in by_day.values())
        mobile = sum(row["mobile"] for row in by_day.values())
        return self.respond({
            "days": days,
            "total": total,
            "mobile": mobile,
            "web": total - mobile,
            "mobile_percent": percent(mobile, total),
            "web_percent": percent(total - mobile, total),
            "points": [{"date": day, "count": by_day.get(day, {}).get("count", 0)} for day in dates],
        })

    @action(detail=False, methods=["get"], serializer_class=AttentionSerializer)
    def attention(self, request):
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
        return self.respond({
            "total": sum(counters.values()),
            **counters,
            "out_of_stock_categories": [categories[i] for i in top_ids if i in categories],
            "pending_hours": PENDING_ORDER_HOURS,
            "last_stock_sync": ProductRemaining.objects.aggregate(last=Max("created_at"))["last"],
        })

    @action(detail=False, methods=["get"], serializer_class=CustomersCompositionSerializer)
    def customers(self, request):
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
        return self.respond(data)

    @action(detail=False, methods=["get"], serializer_class=CatalogSerializer)
    def catalog(self, request):
        """Stock state of active products; `?low_stock=` threshold (default 10)."""
        low = self.get_params()["low_stock"]
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
        return self.respond(data)

    @action(detail=False, methods=["get"], serializer_class=RevenueSerializer)
    def revenue(self, request):
        """Completed orders revenue per month, B2B (prorab) vs individual, last `?months=` (default 6)."""
        starts = month_starts(self.get_params()["months"])
        is_b2b = Q(customer__role=PRORAB)
        rows = Order.objects.filter(status=COMPLETED, created_at__date__gte=starts[0]) \
            .annotate(month=TruncMonth("created_at", output_field=DateField())).values("month") \
            .annotate(b2b=Coalesce(Sum("total_price", filter=is_b2b), 0.0),
                      individual=Coalesce(Sum("total_price", filter=~is_b2b), 0.0))
        by_month = {row["month"]: row for row in rows}

        months = [{"month": m, "b2b": by_month.get(m, {}).get("b2b", 0.0),
                   "individual": by_month.get(m, {}).get("individual", 0.0)} for m in starts]
        return self.respond({
            "b2b": sum(m["b2b"] for m in months),
            "individual": sum(m["individual"] for m in months),
            "months": months,
        })
