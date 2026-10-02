from django.db.models import Count
from rest_framework.exceptions import ValidationError
from apps.service.models import Brand, PartnerBrand
from utils.admin_views import AdminModelViewSet
from ..filters import BrandFilter, PartnerBrandFilter
from ..serializers import BrandSerializer, PartnerBrandSerializer


class BrandViewSet(AdminModelViewSet):
    serializer_class = BrandSerializer
    filterset_class = BrandFilter
    search_fields = ("name_ru", "name_uz", "name_en", "code")
    ordering_fields = ("id", "name", "products_count", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return Brand.objects.annotate(products_count=Count("product_brand"))

    def perform_destroy(self, instance):
        # Product.brand is SET_NULL: deleting would silently detach its products
        if instance.products_count:
            raise ValidationError({"detail": "Brand has products, hide it instead (is_visible=false)."})
        instance.image.delete(save=False)
        instance.delete()


class PartnerBrandViewSet(AdminModelViewSet):
    queryset = PartnerBrand.objects.all()
    serializer_class = PartnerBrandSerializer
    filterset_class = PartnerBrandFilter
    search_fields = ("name",)
    ordering_fields = ("id", "name", "created_at", "updated_at")
    ordering = ("-created_at",)
