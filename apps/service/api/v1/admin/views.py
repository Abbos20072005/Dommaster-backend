from django.db.models import Avg, Count, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from apps.service.models import Order, Product, ProductImage
from utils.admin_views import AdminModelViewSet
from .filters import OrderFilter, ProductFilter
from .serializers import OrderListSerializer, OrderSerializer, OrderStatsSerializer, PENDING, COLLECTING, \
    DELIVERING, COMPLETED, CANCELED, PAID, ProductListSerializer, ProductSerializer, ProductImageSerializer, \
    ProductStatsSerializer


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


class ProductViewSet(AdminModelViewSet):
    filterset_class = ProductFilter
    search_fields = ("name_ru", "name_uz", "name_en", "product_code", "articul_code", "barcode")
    ordering_fields = ("id", "name", "price", "quantity", "rating", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Product.objects.all()
        if self.action == "stats":
            return qs
        qs = qs.select_related("brand", "product_item_category__product_sub_category__product_category") \
            .prefetch_related(Prefetch("product_image", queryset=ProductImage.objects.order_by("id")))
        if self.action != "list":
            qs = qs.prefetch_related("product_characteristics")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action == "stats":
            return ProductStatsSerializer
        if self.action in ("images", "delete_image"):
            return ProductImageSerializer
        return ProductSerializer

    def perform_destroy(self, instance):
        # OrderItem.product is CASCADE: deleting would wipe it from existing orders
        if instance.product_order_item.exists():
            raise ValidationError({"detail": "Product is used in orders, deactivate it instead (is_active=false)."})
        instance.delete()

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def images(self, request, pk=None):
        """Upload a product image (multipart, field `image`)."""
        product = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"images/(?P<image_id>[0-9]+)")
    def delete_image(self, request, pk=None, image_id=None):
        image = get_object_or_404(ProductImage, pk=image_id, product_id=pk)
        image.image.delete(save=False)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], pagination_class=None)
    def stats(self, request):
        """Counts over the same filters as the list (?category=&brand=...)."""
        data = self.filter_queryset(self.get_queryset()).aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            inactive=Count("id", filter=Q(is_active=False)),
            out_of_stock=Count("id", filter=Q(quantity__lte=0)),
            discounted=Count("id", filter=Q(discount_price__isnull=False)),
        )
        return Response(self.get_serializer(data).data)
