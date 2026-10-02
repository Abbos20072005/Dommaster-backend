from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from apps.service.models import Product, ProductImage, ProductAttributeValue
from utils.admin_views import AdminModelViewSet
from ..filters import ProductFilter
from ..serializers import ProductListSerializer, ProductSerializer, ProductImageSerializer, ProductStatsSerializer


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
            .prefetch_related("badges", Prefetch("product_image", queryset=ProductImage.objects.order_by("id")))
        if self.action != "list":
            qs = qs.prefetch_related("product_characteristics", Prefetch(
                "attribute_values", queryset=ProductAttributeValue.objects.select_related("attribute")))
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
