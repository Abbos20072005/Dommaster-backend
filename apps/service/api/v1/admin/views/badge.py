from django.db.models import Count
from apps.service.models import ProductBadge
from utils.admin_views import AdminModelViewSet
from ..filters import ProductBadgeFilter
from ..serializers import ProductBadgeSerializer


class ProductBadgeViewSet(AdminModelViewSet):
    serializer_class = ProductBadgeSerializer
    filterset_class = ProductBadgeFilter
    search_fields = ("name_ru", "name_uz", "name_en")
    ordering_fields = ("id", "name", "products_count", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return ProductBadge.objects.annotate(products_count=Count("products"))
