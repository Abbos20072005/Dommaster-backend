import django_filters
from django.db.models import Exists, OuterRef
from apps.service.models import Brand, PartnerBrand, ProductBadge, ProductCategory, ProductSubCategory, \
    ProductItemCategory, ProductAttribute, Order, Product, Comment, CommentReply, Questions, QuestionsReply, \
    ORDER_STATUS


class OrderFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=ORDER_STATUS, label="?status=0&status=1")
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    min_total = django_filters.NumberFilter(field_name="total_price", lookup_expr="gte")
    max_total = django_filters.NumberFilter(field_name="total_price", lookup_expr="lte")
    has_manager = django_filters.BooleanFilter(field_name="manager", lookup_expr="isnull", exclude=True)

    class Meta:
        model = Order
        fields = ("id", "payment_status", "payment_type", "payment_method", "delivery_type", "customer",
                  "pickup_branch", "manager")


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
        fields = ("brand", "product_item_category", "is_active", "erp_active", "publish_status", "purchasable",
                  "unit")

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(quantity__gt=0) if value else queryset.filter(quantity__lte=0)


class BrandFilter(django_filters.FilterSet):
    has_products = django_filters.BooleanFilter(field_name="product_brand", lookup_expr="isnull", exclude=True,
                                                distinct=True)

    class Meta:
        model = Brand
        fields = ("is_visible", "country")


class PartnerBrandFilter(django_filters.FilterSet):
    class Meta:
        model = PartnerBrand
        fields = ("is_active",)


class ProductBadgeFilter(django_filters.FilterSet):
    class Meta:
        model = ProductBadge
        fields = ("is_active", "kind", "rule_field")


class CountFilterMixin:
    """`has_*` filters over the `*_count` annotations of the view queryset."""

    def filter_has_count(self, queryset, name, value):
        return queryset.filter(**{f"{name}__gt": 0}) if value else queryset.filter(**{name: 0})


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


class CommentReplyFilter(django_filters.FilterSet):
    class Meta:
        model = CommentReply
        fields = ("comment", "customer", "is_admin", "is_visible")


class QuestionReplyFilter(django_filters.FilterSet):
    class Meta:
        model = QuestionsReply
        fields = ("question", "customer", "is_admin", "is_visible")
