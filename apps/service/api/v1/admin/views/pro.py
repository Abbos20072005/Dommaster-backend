from django.db.models import Count
from rest_framework.viewsets import ReadOnlyModelViewSet
from apps.service.models import Project
from utils.admin_views import AdminViewMixin
from ..filters import ProjectFilter
from ..serializers import ProjectSerializer, ProjectDetailSerializer


class ProjectViewSet(AdminViewMixin, ReadOnlyModelViewSet):
    """PRO customers' projects, read-only (also those of customers that are no longer PRO)."""
    filterset_class = ProjectFilter
    search_fields = ("name", "address", "customer__full_name", "customer__phone_number")
    ordering_fields = ("id", "name", "created_at", "updated_at", "items_count")
    ordering = ("-created_at", "-id")

    def get_queryset(self):
        return Project.objects.select_related("customer").annotate(
            items_count=Count("order_items", distinct=True),
            orders_count=Count("order_items__order", distinct=True),
        )

    def get_serializer_class(self):
        return ProjectDetailSerializer if self.action == "retrieve" else ProjectSerializer
