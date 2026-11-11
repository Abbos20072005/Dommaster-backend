from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import DestroyModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.service import search_log
from apps.service.models import SearchRequest, SearchSynonym
from utils.admin_views import AdminModelViewSet, AdminViewMixin
from ..filters import SearchRequestFilter, SearchSynonymFilter
from ..serializers import NotFoundSearchExportQuerySerializer, NotFoundSearchQuerySerializer, \
    NotFoundSearchRowSerializer, SearchRequestAdminSerializer, SearchSynonymSerializer
from .dashboard import summary_range


class SearchSynonymViewSet(AdminModelViewSet):
    queryset = SearchSynonym.objects.all()
    serializer_class = SearchSynonymSerializer
    filterset_class = SearchSynonymFilter
    search_fields = ("terms",)
    ordering_fields = ("id", "created_at", "updated_at")
    ordering = ("-id",)


class NotFoundSearchViewSet(AdminViewMixin, ListModelMixin, GenericViewSet):
    """Catalog searches that found nothing, one row per query. `export/` = the same rows as XLSX."""
    serializer_class = NotFoundSearchRowSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ("normalized",)
    ordering_fields = ("normalized", "searches", "viewers", "first_searched_at", "last_searched_at")
    ordering = ("-searches", "-last_searched_at", "normalized")

    def query_params(self):
        serializer_class = (NotFoundSearchExportQuerySerializer if self.action == "export"
                            else NotFoundSearchQuerySerializer)
        query = serializer_class(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return query.validated_data

    def get_queryset(self):
        params = self.query_params()
        return search_log.report(*summary_range(params), params.get("language"), params.get("platform"))

    @action(detail=False, methods=["get"])
    def export(self, request):
        rows = self.filter_queryset(self.get_queryset())
        data = search_log.export_workbook(rows, self.query_params()["export_language"])
        response = HttpResponse(
            data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="search_not_found_{timezone.now():%Y%m%d_%H%M}.xlsx"'
        return response


class SearchRequestViewSet(AdminViewMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin,
                           DestroyModelMixin, GenericViewSet):
    """"Не нашли — оставьте заявку" requests; the manager changes `status` / `manager_comment` only."""
    queryset = SearchRequest.objects.select_related("customer")
    serializer_class = SearchRequestAdminSerializer
    filterset_class = SearchRequestFilter
    search_fields = ("query", "phone_number", "company")
    ordering_fields = ("id", "status", "created_at", "updated_at")
    ordering = ("-id",)
    http_method_names = ["get", "patch", "delete"]

    @action(detail=False, methods=["get"])
    def stats(self, request):
        counts = dict(SearchRequest.objects.values_list("status").annotate(n=Count("id")))
        result = {status: counts.get(status, 0) for status, _ in SearchRequest.STATUS_CHOICES}
        return Response({"total": sum(result.values()), **result})
