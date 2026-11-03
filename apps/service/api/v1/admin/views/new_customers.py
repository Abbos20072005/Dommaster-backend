from django.db.models import Count, DateField, Exists, Min, OuterRef, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from apps.authorization.models import Customer, FcmToken
from utils.admin_views import AdminViewMixin
from ..serializers import NewCustomersQuerySerializer, NewCustomersSerializer, LAST_6_MONTHS, ALL_TIME
from .dashboard import month_starts

APP_CHANNELS = (Customer.Platform.IOS, Customer.Platform.ANDROID)


def registered_customers():
    """Customers who confirmed the OTP and are still in the admin customers list (not deleted)."""
    return Customer.objects.filter(verified=True, is_deleted=False)


def from_app():
    """`registration_channel`; when it is unknown (older customers / app versions) - has a push token,
    the rule of the dashboard `registrations` block."""
    has_fcm = Exists(FcmToken.objects.filter(customer=OuterRef("pk")))
    return Q(registration_channel__in=APP_CHANNELS) | Q(registration_channel=None) & Q(has_fcm)


def months_count(period):
    if period != ALL_TIME:
        return 6 if period == LAST_6_MONTHS else 12
    first = registered_customers().aggregate(first=Min("created_at"))["first"]
    if first is None:
        return 1
    today = timezone.now().date()
    return (today.year - first.year) * 12 + today.month - first.month + 1


class NewCustomersAPIView(AdminViewMixin, GenericAPIView):
    """New customers per month (Tashkent time), app / site: ?period=6_months|12_months|all_time."""
    serializer_class = NewCustomersSerializer
    filter_backends = []
    pagination_class = None

    def get(self, request):
        params = NewCustomersQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        period = params.validated_data["period"]
        starts = month_starts(months_count(period))
        rows = registered_customers().filter(created_at__date__gte=starts[0]) \
            .annotate(month=TruncMonth("created_at", output_field=DateField())).values("month") \
            .annotate(total=Count("id"), app=Count("id", filter=from_app())).order_by()
        by_month = {row["month"]: row for row in rows}

        months = []
        for month in starts:
            row = by_month.get(month, {"total": 0, "app": 0})
            months.append({"month": month, "total": row["total"], "app": row["app"], "site": row["total"] - row["app"]})
        result = {
            "period": period,
            "date_from": starts[0],
            "date_to": timezone.now().date(),
            **{key: sum(m[key] for m in months) for key in ("total", "app", "site")},
            "months": months,
        }
        return Response(self.get_serializer(result).data)
