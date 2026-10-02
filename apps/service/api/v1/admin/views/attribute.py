from django.db.models import Count
from rest_framework.exceptions import ValidationError
from apps.service.models import ProductAttribute
from utils.admin_views import AdminModelViewSet
from ..filters import ProductAttributeFilter
from ..serializers import ProductAttributeSerializer


class ProductAttributeViewSet(AdminModelViewSet):
    serializer_class = ProductAttributeSerializer
    filterset_class = ProductAttributeFilter
    search_fields = ("name_ru", "name_uz", "name_en")
    ordering_fields = ("id", "name", "value_type", "item_categories_count", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return ProductAttribute.objects.prefetch_related(
            "options", "item_categories__product_sub_category__product_category",
        ).annotate(item_categories_count=Count("item_categories", distinct=True))

    def perform_destroy(self, instance):
        if instance.item_categories_count:
            raise ValidationError({"detail": "Attribute is used in categories, detach it from them first."})
        instance.delete()
