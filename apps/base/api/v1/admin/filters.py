import django_filters
from django.db.models import Q
from apps.base.models import MarketBranch, Banner, Chat, Messages


class MarketBranchFilter(django_filters.FilterSet):
    class Meta:
        model = MarketBranch
        fields = ("branch_type", "is_active")


class BannerFilter(django_filters.FilterSet):
    # target model name: product, productcategory, ...
    target_model = django_filters.CharFilter(field_name="content_type__model")
    has_target = django_filters.BooleanFilter(field_name="object_id", lookup_expr="isnull", exclude=True)
    # active / scheduled / expired / archived
    status = django_filters.ChoiceFilter(choices=Banner.STATUS_CHOICES, method="filter_status")

    class Meta:
        model = Banner
        fields = ("is_visible", "placement", "link_type", "show_on_site", "show_on_ios", "show_on_android")

    def filter_status(self, queryset, name, value):
        return queryset.filter(Banner.status_q(value))


class ChatFilter(django_filters.FilterSet):
    # last message is the customer's (same rule as the dashboard); uses the view's `last_is_answer` annotation
    unanswered = django_filters.BooleanFilter(method="filter_unanswered")
    is_guest = django_filters.BooleanFilter(field_name="customer", lookup_expr="isnull")
    from_activity = django_filters.DateFilter(field_name="last_activity_at", lookup_expr="date__gte")
    to_activity = django_filters.DateFilter(field_name="last_activity_at", lookup_expr="date__lte")

    class Meta:
        model = Chat
        fields = ("customer",)

    def filter_unanswered(self, queryset, name, value):
        answered = Q(last_is_answer=True) | Q(last_is_answer__isnull=True)
        return queryset.exclude(answered) if value else queryset.filter(answered)


class MessageFilter(django_filters.FilterSet):
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Messages
        fields = ("chat", "is_answer")


class CreatedRangeFilter(django_filters.FilterSet):
    """News / articles / videos: only the creation date range."""
    from_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_created = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
