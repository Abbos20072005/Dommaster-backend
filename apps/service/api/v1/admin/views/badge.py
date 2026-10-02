from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.service.models import ProductBadge
from utils.admin_views import AdminModelViewSet
from ..filters import ProductBadgeFilter
from ..serializers import ProductBadgeSerializer, CategoryReorderSerializer


class ProductBadgeViewSet(AdminModelViewSet):
    serializer_class = ProductBadgeSerializer
    filterset_class = ProductBadgeFilter
    search_fields = ("name_ru", "name_uz", "name_en")
    ordering_fields = ("id", "name", "position", "products_count", "created_at", "updated_at")
    ordering = ("position", "id")

    def get_queryset(self):
        return ProductBadge.objects.annotate(products_count=Count("products"))

    @action(detail=False, methods=["post"], serializer_class=CategoryReorderSerializer)
    def reorder(self, request):
        """Order of the badges on a product card: `ids` in the new order, list index becomes `position`."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
