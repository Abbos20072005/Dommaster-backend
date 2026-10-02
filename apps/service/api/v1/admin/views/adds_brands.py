from django.db.models import Count
from apps.service.models import AddsBrands
from utils.admin_views import AdminModelViewSet
from ..filters import AddsBrandsFilter
from ..serializers import AddsBrandsListSerializer, AddsBrandsSerializer


class AddsBrandsViewSet(AdminModelViewSet):
    filterset_class = AddsBrandsFilter
    search_fields = ("name_ru", "name_uz", "name_en", "title_ru", "title_uz", "title_en", "brand__name_ru")
    ordering_fields = ("id", "name", "products_count", "is_visible", "created_at", "updated_at")
    ordering = ("-id",)

    def get_queryset(self):
        return AddsBrands.objects.select_related("brand").annotate(products_count=Count("products"))

    def get_serializer_class(self):
        if self.action == "list":
            return AddsBrandsListSerializer
        return AddsBrandsSerializer
