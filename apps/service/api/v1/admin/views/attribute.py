from apps.service.models import ProductAttribute
from utils.admin_views import AdminModelViewSet
from ..filters import ProductAttributeFilter
from ..serializers import ProductAttributeSerializer


class ProductAttributeViewSet(AdminModelViewSet):
    queryset = ProductAttribute.objects.select_related("item_category__product_sub_category__product_category")
    serializer_class = ProductAttributeSerializer
    filterset_class = ProductAttributeFilter
    search_fields = ("name_ru", "name_uz", "name_en")
    ordering_fields = ("id", "name", "value_type", "created_at", "updated_at")
    ordering = ("-created_at",)
