from rest_framework.viewsets import ModelViewSet
from authorization.custom_jwt import AdminJwtAuthentication
from authorization.permissions import IsAdmin
from utils.pagination import AdminPagination


class AdminViewMixin:
    """Auth + permission + pagination for every admin (dashboard) view."""
    authentication_classes = [AdminJwtAuthentication]
    permission_classes = [IsAdmin]
    pagination_class = AdminPagination


class AdminModelViewSet(AdminViewMixin, ModelViewSet):
    pass
