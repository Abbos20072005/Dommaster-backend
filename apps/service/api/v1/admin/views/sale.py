from django.db.models import Count
from apps.service.models import Sale
from utils.admin_views import AdminModelViewSet
from ..filters import SaleFilter
from ..serializers import SaleListSerializer, SaleSerializer


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
        return SaleSerializer
