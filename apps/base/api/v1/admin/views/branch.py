from rest_framework.exceptions import ValidationError
from apps.base.models import MarketBranch
from utils.admin_views import AdminModelViewSet
from ..filters import MarketBranchFilter
from ..serializers import MarketBranchSerializer


class MarketBranchViewSet(AdminModelViewSet):
    queryset = MarketBranch.objects.all()
    serializer_class = MarketBranchSerializer
    filterset_class = MarketBranchFilter
    search_fields = ("name_ru", "name_uz", "name_en", "address", "phone_number", "code")
    ordering_fields = ("id", "name", "position", "created_at", "updated_at")
    ordering = ("position", "id")

    def perform_destroy(self, instance):
        # ProductRemaining.branch is CASCADE: deleting would wipe the branch stock synced from 1C
        if instance.branch_remaining.exists():
            raise ValidationError({"detail": "Branch has product stock, deactivate it instead (is_active=false)."})
        if instance.image:
            instance.image.delete(save=False)
        instance.delete()
