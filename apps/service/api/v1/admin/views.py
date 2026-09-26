from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.service.models import Order
from utils.admin_views import AdminModelViewSet
from .filters import OrderFilter
from .serializers import OrderListSerializer, OrderSerializer, OrderStatsSerializer, PENDING, COLLECTING, \
    DELIVERING, COMPLETED, CANCELED, PAID


class OrderViewSet(AdminModelViewSet):
    filterset_class = OrderFilter
    search_fields = ("receiver_name", "receiver_phone", "customer__full_name", "customer__phone_number")
    ordering_fields = ("id", "created_at", "total_price", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Order.objects.select_related("customer")
        if self.action == "list":
            qs = qs.annotate(items_count=Count("order_items"))
        elif self.action != "stats":
            qs = qs.select_related("order_location", "pickup_branch", "promocode") \
                .prefetch_related("order_items__product")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action == "stats":
            return OrderStatsSerializer
        return OrderSerializer

    def perform_destroy(self, instance):
        # stock is already taken for these; cancelling restores it (Order pre_save signal)
        if instance.status in (COLLECTING, DELIVERING):
            raise ValidationError({"status": "Cancel the order before deleting it."})
        instance.delete()

    @action(detail=False, methods=["get"], pagination_class=None)
    def stats(self, request):
        """Counts/revenue over the same filters as the list (?from_created=&to_created=...)."""
        data = self.filter_queryset(self.get_queryset()).aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=PENDING)),
            collecting=Count("id", filter=Q(status=COLLECTING)),
            delivering=Count("id", filter=Q(status=DELIVERING)),
            completed=Count("id", filter=Q(status=COMPLETED)),
            canceled=Count("id", filter=Q(status=CANCELED)),
            paid=Count("id", filter=Q(payment_status=PAID)),
            revenue=Coalesce(Sum("total_price", filter=Q(status=COMPLETED)), 0.0),
            average_check=Coalesce(Avg("total_price", filter=Q(status=COMPLETED)), 0.0),
        )
        return Response(self.get_serializer(data).data)
