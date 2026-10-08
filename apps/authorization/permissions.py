from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Use together with `AdminJwtAuthentication`."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)


class IsSuperAdmin(IsAdmin):
    """Settings-level sections (staff management): only `is_superuser` admins."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_superuser
