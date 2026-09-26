from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.viewsets import ModelViewSet
from apps.authorization.custom_jwt import AdminJwtAuthentication
from apps.authorization.permissions import IsAdmin
from utils.pagination import AdminPagination


class AdminViewMixin:
    """Auth + permission + pagination + filtering for every admin (dashboard) view.
    Views set `filterset_class`/`filterset_fields` (django-filter), `search_fields` (?search=), `ordering_fields` (?ordering=)."""
    authentication_classes = [AdminJwtAuthentication]
    permission_classes = [IsAdmin]
    pagination_class = AdminPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]


class AdminModelViewSet(AdminViewMixin, ModelViewSet):
    pass
