from django.db.models import Count
from rest_framework.exceptions import ValidationError
from apps.service.models import ProductCategory, ProductSubCategory, ProductItemCategory
from utils.admin_views import AdminModelViewSet
from ..filters import ProductCategoryFilter, ProductSubCategoryFilter, ProductItemCategoryFilter
from ..serializers import ProductCategorySerializer, ProductSubCategoryAdminSerializer, \
    ProductItemCategoryAdminSerializer


class CategoryDeleteMixin:
    def perform_destroy(self, instance):
        # children and Product.product_item_category are CASCADE: deleting would wipe the products (and order items)
        if instance.products_count:
            raise ValidationError({"detail": "Category has products, move them to another category first."})
        instance.delete()


class ProductCategoryViewSet(CategoryDeleteMixin, AdminModelViewSet):
    serializer_class = ProductCategorySerializer
    filterset_class = ProductCategoryFilter
    search_fields = ("name_ru", "name_uz", "name_en", "code")
    ordering_fields = ("id", "name", "position", "children_count", "products_count", "created_at", "updated_at")
    ordering = ("position", "id")

    def get_queryset(self):
        # reverse names: category -> "product_category" (subs) -> "product_sub_category" (items)
        #   -> "product_item_category" (products)
        return ProductCategory.objects.annotate(
            children_count=Count("product_category", distinct=True),
            products_count=Count("product_category__product_sub_category__product_item_category", distinct=True),
        )


class ProductSubCategoryViewSet(CategoryDeleteMixin, AdminModelViewSet):
    serializer_class = ProductSubCategoryAdminSerializer
    filterset_class = ProductSubCategoryFilter
    search_fields = ("name_ru", "name_uz", "name_en", "code")
    ordering_fields = ("id", "name", "children_count", "products_count", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return ProductSubCategory.objects.select_related("product_category").annotate(
            children_count=Count("product_sub_category", distinct=True),
            products_count=Count("product_sub_category__product_item_category", distinct=True),
        )


class ProductItemCategoryViewSet(CategoryDeleteMixin, AdminModelViewSet):
    serializer_class = ProductItemCategoryAdminSerializer
    filterset_class = ProductItemCategoryFilter
    search_fields = ("name_ru", "name_uz", "name_en", "code")
    ordering_fields = ("id", "name", "products_count", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return ProductItemCategory.objects.select_related("product_sub_category__product_category").annotate(
            products_count=Count("product_item_category"),
        )
