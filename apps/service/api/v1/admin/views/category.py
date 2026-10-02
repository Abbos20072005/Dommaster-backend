from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.service.models import ProductCategory, ProductSubCategory, ProductItemCategory, \
    ProductItemCategoryFilterSchema
from utils.admin_views import AdminModelViewSet
from ..filters import ProductCategoryFilter, ProductSubCategoryFilter, ProductItemCategoryFilter
from ..serializers import ProductCategorySerializer, ProductSubCategoryAdminSerializer, \
    ProductItemCategoryAdminSerializer, ItemCategoryAttributesSerializer, CategoryReorderSerializer


def filters_count(path):
    """Distinct filterable filter keys of the item categories under a category (`path`: schema -> that category)."""
    schemas = ProductItemCategoryFilterSchema.objects.filter(is_filterable=True, **{path: OuterRef("pk")}) \
        .order_by().values(path).annotate(count=Count("key", distinct=True)).values("count")
    return Coalesce(Subquery(schemas), 0)


# reverse names: category -> "product_category" (subs) -> "product_sub_category" (items)
#   -> "product_item_category" (products)
def category_queryset():
    return ProductCategory.objects.annotate(
        children_count=Count("product_category", distinct=True),
        products_count=Count("product_category__product_sub_category__product_item_category", distinct=True),
        filters_count=filters_count("item_category__product_sub_category__product_category"),
    )


def sub_category_queryset():
    return ProductSubCategory.objects.annotate(
        children_count=Count("product_sub_category", distinct=True),
        products_count=Count("product_sub_category__product_item_category", distinct=True),
        filters_count=filters_count("item_category__product_sub_category"),
    )


def item_category_queryset():
    return ProductItemCategory.objects.annotate(
        products_count=Count("product_item_category"),
        filters_count=filters_count("item_category"),
    )


class CategoryActionsMixin:
    def perform_destroy(self, instance):
        # children and Product.product_item_category are CASCADE: deleting would wipe the products (and order items)
        if instance.products_count:
            raise ValidationError({"detail": "Category has products, move them to another category first."})
        instance.delete()

    @action(detail=False, methods=["post"], serializer_class=CategoryReorderSerializer)
    def reorder(self, request):
        """Drag & drop: `ids` = categories of one level in the new order, list index becomes `position`."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProductCategoryViewSet(CategoryActionsMixin, AdminModelViewSet):
    serializer_class = ProductCategorySerializer
    filterset_class = ProductCategoryFilter
    search_fields = ("name_ru", "name_uz", "name_en", "code", "slug")
    ordering_fields = ("id", "name", "position", "children_count", "products_count", "created_at", "updated_at")
    ordering = ("position", "id")

    def get_queryset(self):
        return category_queryset()


class ProductSubCategoryViewSet(CategoryActionsMixin, AdminModelViewSet):
    serializer_class = ProductSubCategoryAdminSerializer
    filterset_class = ProductSubCategoryFilter
    search_fields = ("name_ru", "name_uz", "name_en", "code", "slug")
    ordering_fields = ("id", "name", "position", "children_count", "products_count", "created_at", "updated_at")
    ordering = ("position", "id")

    def get_queryset(self):
        return sub_category_queryset().select_related("product_category")


class ProductItemCategoryViewSet(CategoryActionsMixin, AdminModelViewSet):
    serializer_class = ProductItemCategoryAdminSerializer
    filterset_class = ProductItemCategoryFilter
    search_fields = ("name_ru", "name_uz", "name_en", "code", "slug")
    ordering_fields = ("id", "name", "position", "products_count", "created_at", "updated_at")
    ordering = ("position", "id")

    def get_queryset(self):
        return item_category_queryset().select_related("product_sub_category__product_category")

    @action(detail=True, methods=["get", "put"], serializer_class=ItemCategoryAttributesSerializer)
    def attributes(self, request, pk=None):
        """Attributes of the item category. PUT replaces the whole list, list order = position."""
        item_category = self.get_object()
        if request.method == "GET":
            return Response(self.get_serializer(item_category).data)
        serializer = self.get_serializer(item_category, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
