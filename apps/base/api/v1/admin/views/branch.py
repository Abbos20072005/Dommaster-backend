from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.base.models import MarketBranch
from utils.admin_views import AdminModelViewSet
from ..filters import MarketBranchFilter
from ..serializers import MarketBranchReorderSerializer, MarketBranchSerializer


class MarketBranchViewSet(AdminModelViewSet):
    """Branches = stores (pickup points) and 1C warehouses. JSON or multipart (`image`; `schedule` as a JSON
    string)."""
    queryset = MarketBranch.objects.annotate(orders_count=Count("order"))
    serializer_class = MarketBranchSerializer
    filterset_class = MarketBranchFilter
    search_fields = ("name_ru", "name_uz", "address_ru", "address_uz", "phone_number", "code")
    ordering_fields = ("id", "name", "position", "created_at", "updated_at")
    ordering = ("position", "id")

    def perform_destroy(self, instance):
        # ProductRemaining.branch is CASCADE: deleting would wipe the branch stock synced from 1C
        if instance.branch_remaining.exists():
            raise ValidationError({"detail": "Branch has product stock, deactivate it instead (is_active=false)."})
        if instance.order_set.exists():
            raise ValidationError({"detail": "Branch has orders, deactivate it instead (is_active=false)."})
        if instance.image:
            instance.image.delete(save=False)
        instance.delete()

    @action(detail=False, methods=["post"], serializer_class=MarketBranchReorderSerializer)
    def reorder(self, request):
        """Drag & drop: `ids` in the new order, list index becomes `position`."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
