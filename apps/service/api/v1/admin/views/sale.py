from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.service.models import Sale
from utils.admin_views import AdminModelViewSet
from ..filters import SaleFilter
from ..serializers import SaleListSerializer, SaleSerializer, SaleProductReorderSerializer


class SaleViewSet(AdminModelViewSet):
    filterset_class = SaleFilter
    search_fields = ("name",)
    ordering_fields = ("id", "name", "discount_from", "discount_to", "is_main", "is_visible", "created_at")
    ordering = ("-id",)

    def get_queryset(self):
        return Sale.objects.annotate(products_count=Count("products"))

    def get_serializer_class(self):
        if self.action == "list":
            return SaleListSerializer
        if self.action == "reorder_products":
            return SaleProductReorderSerializer
        return SaleSerializer

    @action(detail=True, methods=["post"], url_path="products/reorder")
    def reorder_products(self, request, pk=None):
        """Order of the sale's products (drag and drop): `ids` = product ids in the new order."""
        sale = self.get_object()
        serializer = self.get_serializer(data=request.data, context={**self.get_serializer_context(), "sale": sale})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"ids": serializer.validated_data["ids"]})
