import re
import django_filters
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework.filters import SearchFilter
from apps.service.models import AddsBrands, Brand, PartnerBrand, ProductModel, ProductBadge, ProductCategory, \
    ProductSubCategory, ProductItemCategory, ProductAttribute, Order, OrderItem, Product, Comment, CommentReply, \
    Questions, QuestionsReply, ORDER_STATUS, Sale, HomeBlock, ProductModeration, FilterPage, Project, ContentImport
from apps.service.filter_pages import open_pages


def all_words(words, *lookups):
    """Every word is found in at least one of the lookups."""
    query = Q()
    for word in words:
        word_query = Q()
        for lookup in lookups:
            word_query |= Q(**{f"{lookup}__icontains": word})
        query &= word_query
    return query


class OrderSearchFilter(SearchFilter):
    """`?search=` of the orders list: order number, customer / receiver name, any part of the phone,
    product name or SKU. A query of digits only (spaces, `+`, `-`, brackets, `#`, `№` are ignored) is a number:
    the order id, a part of a phone, a part of a product code. Anything else is text: every word must be in
    the name of the customer / receiver, or in the name / codes of one product of the order."""
    search_description = "Order number, customer name, part of the phone, product name or SKU"
    NUMBER_NOISE = re.compile(r"[\s+\-()#№]")
    PRODUCT_CODES = ("product__articul_code", "product__product_code", "product__barcode")
    PRODUCT_NAMES = ("product__name_uz", "product__name_ru")

    def filter_queryset(self, request, queryset, view):
        search = (request.query_params.get(self.search_param) or "").replace("\x00", "").strip()
        if not search:
            return queryset
        items = OrderItem.objects.filter(order=OuterRef("pk"))
        number = self.NUMBER_NOISE.sub("", search)
        if number.isdigit():
            return queryset.filter(
                Q(id=number) | Q(receiver_phone__contains=number) | Q(customer__phone_number__contains=number)
                | Exists(items.filter(all_words([number], *self.PRODUCT_CODES)))
            )
        words = search.split()
        return queryset.filter(
            all_words(words, "receiver_name", "customer__full_name")
            | Exists(items.filter(all_words(words, *self.PRODUCT_NAMES, *self.PRODUCT_CODES)))
        )


class OrderFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=ORDER_STATUS, label="?status=0&status=1")
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    min_total = django_filters.NumberFilter(field_name="total_price", lookup_expr="gte")
    max_total = django_filters.NumberFilter(field_name="total_price", lookup_expr="lte")
    has_manager = django_filters.BooleanFilter(field_name="manager", lookup_expr="isnull", exclude=True)
    pickup_expired = django_filters.BooleanFilter(method="filter_pickup_expired")

    class Meta:
        model = Order
        fields = ("id", "channel", "payment_status", "payment_type", "payment_method", "delivery_type", "customer",
                  "pickup_branch", "manager")

    def filter_pickup_expired(self, queryset, name, value):
        expired = Q(status=Order.READY_FOR_PICKUP, pickup_deadline__lt=timezone.now())
        return queryset.filter(expired) if value else queryset.exclude(expired)


class ProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="product_item_category__product_sub_category__product_category")
    sub_category = django_filters.NumberFilter(field_name="product_item_category__product_sub_category")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    badge = django_filters.NumberFilter(field_name="badges")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")
    has_discount = django_filters.BooleanFilter(field_name="discount_price", lookup_expr="isnull", exclude=True)
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Product
        fields = ("brand", "product_model", "product_item_category", "is_active", "erp_active", "publish_status",
                  "purchasable", "on_order", "unit")

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(quantity__gt=0) if value else queryset.filter(quantity__lte=0)


class BrandFilter(django_filters.FilterSet):
    has_products = django_filters.BooleanFilter(field_name="product_brand", lookup_expr="isnull", exclude=True,
                                                distinct=True)

    class Meta:
        model = Brand
        fields = ("is_visible", "show_on_home", "country")


class PartnerBrandFilter(django_filters.FilterSet):
    class Meta:
        model = PartnerBrand
        fields = ("is_active",)


class AddsBrandsFilter(django_filters.FilterSet):
    has_brand = django_filters.BooleanFilter(field_name="brand", lookup_expr="isnull", exclude=True)

    class Meta:
        model = AddsBrands
        fields = ("is_visible", "brand")


class ProductBadgeFilter(django_filters.FilterSet):
    class Meta:
        model = ProductBadge
        fields = ("is_active", "kind", "rule_field")


class CountFilterMixin:
    """`has_*` filters over the `*_count` annotations of the view queryset."""

    def filter_has_count(self, queryset, name, value):
        return queryset.filter(**{f"{name}__gt": 0}) if value else queryset.filter(**{name: 0})


class ProductModelFilter(CountFilterMixin, django_filters.FilterSet):
    has_products = django_filters.BooleanFilter(field_name="products_count", method="filter_has_count")

    class Meta:
        model = ProductModel
        fields = ("brand", "is_active")


class ProductCategoryFilter(CountFilterMixin, django_filters.FilterSet):
    has_children = django_filters.BooleanFilter(field_name="children_count", method="filter_has_count")
    has_products = django_filters.BooleanFilter(field_name="products_count", method="filter_has_count")

    class Meta:
        model = ProductCategory
        fields = ("is_active", "show_on_site", "show_in_app")


class ProductSubCategoryFilter(CountFilterMixin, django_filters.FilterSet):
    has_children = django_filters.BooleanFilter(field_name="children_count", method="filter_has_count")
    has_products = django_filters.BooleanFilter(field_name="products_count", method="filter_has_count")

    class Meta:
        model = ProductSubCategory
        fields = ("product_category", "is_active", "show_on_site", "show_in_app")


class ProductItemCategoryFilter(CountFilterMixin, django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="product_sub_category__product_category")
    has_products = django_filters.BooleanFilter(field_name="products_count", method="filter_has_count")

    class Meta:
        model = ProductItemCategory
        fields = ("product_sub_category", "is_active", "show_on_site", "show_in_app")


class ProductAttributeFilter(CountFilterMixin, django_filters.FilterSet):
    item_category = django_filters.NumberFilter(field_name="item_categories")
    sub_category = django_filters.NumberFilter(field_name="item_categories__product_sub_category")
    category = django_filters.NumberFilter(field_name="item_categories__product_sub_category__product_category")
    in_use = django_filters.BooleanFilter(field_name="item_categories_count", method="filter_has_count")

    class Meta:
        model = ProductAttribute
        fields = ("value_type", "is_filterable", "is_active")


def comment_answered():
    """A comment/question counts as answered once the admin has replied (same rule as the dashboard)."""
    return Exists(CommentReply.objects.filter(comment=OuterRef("pk"), is_admin=True))


def question_answered():
    return Exists(QuestionsReply.objects.filter(question=OuterRef("pk"), is_admin=True))


class CommentFilter(django_filters.FilterSet):
    product_rating = django_filters.MultipleChoiceFilter(choices=[(i, i) for i in range(1, 6)],
                                                         label="?product_rating=1&product_rating=2")
    answered = django_filters.BooleanFilter(method="filter_answered")
    has_images = django_filters.BooleanFilter(field_name="comment_image", lookup_expr="isnull", exclude=True,
                                              distinct=True)
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Comment
        fields = ("product", "customer", "is_visible")

    def filter_answered(self, queryset, name, value):
        return queryset.annotate(_answered=comment_answered()).filter(_answered=value)


class QuestionFilter(django_filters.FilterSet):
    answered = django_filters.BooleanFilter(method="filter_answered")
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Questions
        fields = ("product", "customer", "is_visible")

    def filter_answered(self, queryset, name, value):
        return queryset.annotate(_answered=question_answered()).filter(_answered=value)


class SaleFilter(django_filters.FilterSet):
    from_discount = django_filters.DateFilter(field_name="discount_from", lookup_expr="gte")
    to_discount = django_filters.DateFilter(field_name="discount_to", lookup_expr="lte")

    class Meta:
        model = Sale
        fields = ("is_main", "is_visible")


class CommentReplyFilter(django_filters.FilterSet):
    class Meta:
        model = CommentReply
        fields = ("comment", "customer", "is_admin", "is_visible")


class QuestionReplyFilter(django_filters.FilterSet):
    class Meta:
        model = QuestionsReply
        fields = ("question", "customer", "is_admin", "is_visible")


class HomeBlockFilter(django_filters.FilterSet):
    # the tab of the page: blocks shown on the site / in the app
    channel = django_filters.ChoiceFilter(choices=(("site", "site"), ("app", "app")), method="filter_channel")

    class Meta:
        model = HomeBlock
        fields = ("type", "is_visible", "show_on_site", "show_in_app")

    def filter_channel(self, queryset, name, value):
        return queryset.filter(**{"show_on_site" if value == "site" else "show_in_app": True})


class ProductModerationFilter(django_filters.FilterSet):
    reviewed_from = django_filters.DateFilter(field_name="reviewed_at", lookup_expr="date__gte")
    reviewed_to = django_filters.DateFilter(field_name="reviewed_at", lookup_expr="date__lte")

    class Meta:
        model = ProductModeration
        fields = ("status", "product", "submitted_by", "reviewed_by")


class ContentImportFilter(django_filters.FilterSet):
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = ContentImport
        fields = ("status", "created_by", "applied_by")


class FilterPageFilter(django_filters.FilterSet):
    # open = shown to clients and in the sitemap (filter_pages.open_pages)
    is_open = django_filters.BooleanFilter(method="filter_is_open")
    has_brand = django_filters.BooleanFilter(field_name="brand", lookup_expr="isnull", exclude=True)

    class Meta:
        model = FilterPage
        fields = ("is_active", "item_category", "brand")

    def filter_is_open(self, queryset, name, value):
        ids = open_pages().values("id")
        return queryset.filter(id__in=ids) if value else queryset.exclude(id__in=ids)


class ProjectFilter(django_filters.FilterSet):
    has_items = django_filters.BooleanFilter(method="filter_has_items")

    class Meta:
        model = Project
        fields = ("customer", "status")

    def filter_has_items(self, queryset, name, value):
        # `items_count` is annotated in ProjectViewSet.get_queryset
        return queryset.filter(items_count__gt=0) if value else queryset.filter(items_count=0)
