from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from apps.service.models import Manager, Order, OrderComment, ProductCodeChange
from utils.admin_views import AdminModelViewSet
from ..filters import OrderFilter, OrderSearchFilter, ProductCodeChangeFilter
from ..serializers import OrderListSerializer, OrderSerializer, OrderStatsSerializer, ManagerSerializer, \
    OrderCommentSerializer, OrderIkpuSerializer, ProductCodeChangeSerializer, PENDING, CONFIRMED, COLLECTING, DELIVERING, COMPLETED, CANCELED, READY_FOR_PICKUP, PAID


class ManagerViewSet(AdminModelViewSet):
    queryset = Manager.objects.all()
    serializer_class = ManagerSerializer
    filterset_fields = ("is_active",)
    search_fields = ("full_name",)
    ordering_fields = ("id", "full_name", "created_at")
    ordering = ("full_name",)


class OrderCommentViewSet(AdminModelViewSet):
    """Internal order notes (`?order=<id>`): list + add only, never exposed to the client API."""
    queryset = OrderComment.objects.select_related("author")
    serializer_class = OrderCommentSerializer
    filterset_fields = ("order", "is_system")
    search_fields = ("text",)
    ordering_fields = ("id", "created_at")
    ordering = ("-created_at",)
    http_method_names = ["get", "post", "head", "options"]


class OrderViewSet(AdminModelViewSet):
    filterset_class = OrderFilter
    filter_backends = [DjangoFilterBackend, OrderSearchFilter, OrderingFilter]
    ordering_fields = ("id", "created_at", "total_price", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Order.objects.select_related("customer", "manager")
        if self.action == "list":
            qs = qs.annotate(items_count=Count("order_items"))
        elif self.action != "stats":
            qs = qs.select_related("order_location", "pickup_branch", "promocode") \
                .prefetch_related("order_items__product", "order_items__project", "comments__author",
                                  "atmos_transactions")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action == "stats":
            return OrderStatsSerializer
        if self.action == "ikpu":
            return OrderIkpuSerializer
        return OrderSerializer

    def perform_destroy(self, instance):
        # stock is already taken for these; cancelling restores it (Order pre_save signal)
        if instance.status in (COLLECTING, DELIVERING, READY_FOR_PICKUP):
            raise ValidationError({"status": "Cancel the order before deleting it."})
        instance.delete()

    @action(detail=False, methods=["get"], pagination_class=None)
    def stats(self, request):
        """Counts/revenue over the same filters as the list (?from_created=&to_created=...)."""
        data = self.filter_queryset(self.get_queryset()).aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=PENDING)),
            confirmed=Count("id", filter=Q(status=CONFIRMED)),
            collecting=Count("id", filter=Q(status=COLLECTING)),
            delivering=Count("id", filter=Q(status=DELIVERING)),
            completed=Count("id", filter=Q(status=COMPLETED)),
            canceled=Count("id", filter=Q(status=CANCELED)),
            ready_for_pickup=Count("id", filter=Q(status=READY_FOR_PICKUP)),
            pickup_expired=Count("id", filter=Q(status=READY_FOR_PICKUP, pickup_deadline__lt=timezone.now())),
            paid=Count("id", filter=Q(payment_status=PAID)),
            revenue=Coalesce(Sum("total_price", filter=Q(status=COMPLETED)), 0.0),
            average_check=Coalesce(Avg("total_price", filter=Q(status=COMPLETED)), 0.0),
        )
        return Response(self.get_serializer(data).data)

    @action(detail=True, methods=["patch"])
    def ikpu(self, request, pk=None):
        """IKPU codes of items of a pending order (`{"items": [{"id", "ikpu_code"}]}`); the product cards take
        them too. Returns the order."""
        order = self.get_object()
        with transaction.atomic():
            locked = Order.objects.select_for_update().get(pk=order.pk)
            serializer = OrderIkpuSerializer(data=request.data, context={"order": locked, "request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(OrderSerializer(self.get_object(), context=self.get_serializer_context()).data)


class ProductCodeChangeViewSet(AdminModelViewSet):
    """Log of the IKPU / package codes (`?product=`, `?order=`): read only."""
    queryset = ProductCodeChange.objects.select_related("product", "order", "changed_by__staff_profile")
    serializer_class = ProductCodeChangeSerializer
    filterset_class = ProductCodeChangeFilter
    search_fields = ("product__name_ru", "product__name_uz", "old_value", "new_value")
    ordering_fields = ("id", "created_at")
    ordering = ("-created_at", "-id")
    http_method_names = ["get", "head", "options"]
