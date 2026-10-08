from django.contrib.auth import get_user_model
from django.db.models import F
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.authorization.models import StaffProfile
from apps.authorization.permissions import IsSuperAdmin
from utils.admin_views import AdminModelViewSet
from ..filters import StaffFilter
from ..serializers import StaffSerializer, StaffCreateSerializer, StaffResetPasswordSerializer


class StaffViewSet(AdminModelViewSet):
    """Dashboard accounts (django `User` with `is_staff`). Super admins only."""
    permission_classes = [IsSuperAdmin]
    filterset_class = StaffFilter
    search_fields = ("staff_profile__full_name", "username")
    ordering_fields = ("id", "username", "full_name", "last_login", "created_at")
    ordering = ("id",)

    def get_queryset(self):
        return get_user_model().objects.filter(is_staff=True).select_related(
            "staff_profile__created_by__staff_profile",
        ).annotate(full_name=F("staff_profile__full_name"), created_at=F("date_joined"))

    def get_serializer_class(self):
        if self.action == "create":
            return StaffCreateSerializer
        if self.action == "reset_password":
            return StaffResetPasswordSerializer
        return StaffSerializer

    def get_other_staff(self, message):
        """Object of a detail action that an admin may not run on their own account."""
        staff = self.get_object()
        if staff == self.request.user:
            raise ValidationError(message)
        return staff

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise ValidationError("You cannot delete your own account")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        staff = self.get_other_staff("You cannot block your own account")
        StaffProfile.of(staff).block()
        return Response(self.get_serializer(staff).data)

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        staff = self.get_object()
        StaffProfile.of(staff).unblock()
        return Response(self.get_serializer(staff).data)
