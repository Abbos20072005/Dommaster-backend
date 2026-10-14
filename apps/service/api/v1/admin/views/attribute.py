from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError
from apps.service.models import ProductAttribute, ProductAttributeValue
from utils.admin_views import AdminModelViewSet
from ..filters import ProductAttributeFilter
from ..serializers import ProductAttributeSerializer


class ProductAttributeViewSet(AdminModelViewSet):
    serializer_class = ProductAttributeSerializer
    filterset_class = ProductAttributeFilter
    search_fields = ("name_ru", "name_uz")
    ordering_fields = ("id", "name", "value_type", "item_categories_count", "products_count", "created_at",
                       "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        # subquery: a second Count() join would multiply the rows (categories x products)
        products_count = ProductAttributeValue.objects.filter(attribute=OuterRef("pk")).order_by() \
            .values("attribute").annotate(count=Count("id")).values("count")
        return ProductAttribute.objects.prefetch_related(
            "options", "item_categories__product_sub_category__product_category",
        ).annotate(
            item_categories_count=Count("item_categories", distinct=True),
            products_count=Coalesce(Subquery(products_count), 0),
        )

    def perform_destroy(self, instance):
        # ProductItemCategoryAttribute.attribute and ProductAttributeValue.attribute are PROTECT
        if instance.item_categories_count:
            raise ValidationError({"detail": "Attribute is used in categories, detach it from them first."})
        if instance.products_count:
            raise ValidationError({"detail": "Attribute has values in products, clear them first."})
        instance.delete()
