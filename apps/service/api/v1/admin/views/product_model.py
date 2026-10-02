from django.db.models import Count
from rest_framework.exceptions import ValidationError
from apps.service.models import ProductModel
from utils.admin_views import AdminModelViewSet
from ..filters import ProductModelFilter
from ..serializers import ProductModelSerializer


class ProductModelViewSet(AdminModelViewSet):
    serializer_class = ProductModelSerializer
    filterset_class = ProductModelFilter
    search_fields = ("name",)
    ordering_fields = ("id", "name", "products_count", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return ProductModel.objects.select_related("brand").annotate(products_count=Count("products"))

    def perform_destroy(self, instance):
        # Product.product_model is SET_NULL: deleting would silently detach its products
        if instance.products_count:
            raise ValidationError({"detail": "Model has products, deactivate it instead (is_active=false)."})
        instance.delete()
