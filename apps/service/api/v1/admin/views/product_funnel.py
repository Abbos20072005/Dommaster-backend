from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from apps.authorization.api.v1.admin.filters import NullsLastOrderingFilter
from apps.service import funnel
from utils.admin_views import AdminViewMixin
from ..serializers import ProductFunnelExportQuerySerializer, ProductFunnelQuerySerializer, ProductFunnelRowSerializer
from .dashboard import summary_range


class FunnelOrderingFilter(NullsLastOrderingFilter):
    """Many rows share a number (zeros), so `id` keeps the pages stable."""

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view) or []
        return [*ordering, "id"] if "id" not in ordering and "-id" not in ordering else ordering


class ProductFunnelViewSet(AdminViewMixin, ListModelMixin, GenericViewSet):
    """Product funnel of the "Savdo" page: views / cart additions / checkout starts / purchases per product
    (BLD-372). `export/` = the same rows (filters + ordering) as XLSX, without pagination."""
    serializer_class = ProductFunnelRowSerializer
    filter_backends = [SearchFilter, FunnelOrderingFilter]
    search_fields = ["name_ru", "name_uz", "articul_code"]
    ordering_fields = ["id", "name_ru", "articul_code", "views", "add_to_cart", "checkout_start", "purchases",
                       "incomplete", "completion_rate", "other_purchases"]
    ordering = ["-views", "-purchases"]

    def query_params(self):
        serializer_class = (ProductFunnelExportQuerySerializer if self.action == "export"
                            else ProductFunnelQuerySerializer)
        query = serializer_class(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return query.validated_data

    def get_queryset(self):
        params = self.query_params()
        return funnel.report(*summary_range(params), params["channel"])

    @action(detail=False, methods=["get"])
    def export(self, request):
        products = self.filter_queryset(self.get_queryset())
        data = funnel.export_workbook(products, self.query_params()["language"])
        response = HttpResponse(
            data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="product_funnel_{timezone.now():%Y%m%d_%H%M}.xlsx"'
        return response
