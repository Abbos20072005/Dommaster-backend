from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.authorization.models import Customer
from utils.admin_views import AdminModelViewSet
from ..filters import CustomerFilter, active_since
from ..serializers import CustomerSerializer, CustomerDetailSerializer, CustomerStatsSerializer

ORDER_COMPLETED = 3


class CustomerViewSet(AdminModelViewSet):
    filterset_class = CustomerFilter
    search_fields = ("full_name", "phone_number", "email")
    ordering_fields = ("id", "full_name", "created_at", "last_login", "orders_count", "total_purchase")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Customer.objects.annotate(
            # only completed orders count as purchases
            orders_count=Count("order", filter=Q(order__status=ORDER_COMPLETED)),
            total_purchase=Coalesce(Sum("order__total_price", filter=Q(order__status=ORDER_COMPLETED)), 0.0),
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related("customeraddresses_set")
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CustomerDetailSerializer
        if self.action == "stats":
            return CustomerStatsSerializer
        return CustomerSerializer

    @action(detail=False, methods=["get"], filter_backends=[], pagination_class=None)
    def stats(self, request):
        data = Customer.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(last_login__gte=active_since())),
            b2b=Count("id", filter=Q(role=Customer.Role.PRORAB)),
            blocked=Count("id", filter=Q(is_blocked=True)),
        )
        return Response(self.get_serializer(data).data)
