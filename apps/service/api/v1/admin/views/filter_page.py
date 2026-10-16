from apps.service.models import FilterPage
from utils.admin_views import AdminModelViewSet
from ..filters import FilterPageFilter
from ..serializers import FilterPageSerializer


class FilterPageViewSet(AdminModelViewSet):
    serializer_class = FilterPageSerializer
    filterset_class = FilterPageFilter
    search_fields = ("keyword_ru", "keyword_uz", "title_ru", "title_uz", "slug")
    ordering_fields = ("id", "slug", "search_volume", "products_count", "created_at", "updated_at")
    ordering = ("-search_volume", "id")

    def get_queryset(self):
        return FilterPage.objects.select_related("item_category__product_sub_category__product_category", "brand")
