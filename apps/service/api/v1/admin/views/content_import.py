from django.db import transaction
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from apps.service.models import ContentImport
from utils.admin_views import AdminViewMixin
from utils.background import run_in_background
from ..filters import ContentImportFilter
from ..serializers import ContentImportListSerializer, ContentImportSerializer, ContentImportChangeSerializer


class ContentImportViewSet(AdminViewMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                           mixins.CreateModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    """Bulk content import (the audit log of the batches): upload the workbook of `products/content-export/`
    → validated in the background (`status` validating → ready / invalid) → `apply/` writes every change at
    once (applying → applied / failed)."""
    filterset_class = ContentImportFilter
    search_fields = ("file_name",)
    ordering_fields = ("id", "created_at", "applied_at")
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return ContentImport.objects.select_related("created_by__staff_profile", "applied_by__staff_profile")

    def get_serializer_class(self):
        if self.action == "list":
            return ContentImportListSerializer
        if self.action == "changes":
            return ContentImportChangeSerializer
        return ContentImportSerializer

    def perform_destroy(self, instance):
        if instance.status in (ContentImport.VALIDATING, ContentImport.APPLYING, ContentImport.APPLIED):
            raise ValidationError({"detail": "An applied or running import stays in the log."})
        instance.file.delete(save=False)
        instance.delete()

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        """Applies every change of a `ready` import in one transaction, in the background."""
        from apps.service import tasks
        instance = self.get_object()
        if instance.status != ContentImport.READY:
            raise ValidationError({"detail": f"Import is {instance.status}, only a ready one can be applied."})
        if not instance.changes_count:
            raise ValidationError({"detail": "Nothing to change."})
        updated = ContentImport.objects.filter(pk=instance.pk, status=ContentImport.READY) \
            .update(status=ContentImport.APPLYING, applied_by=request.user)
        if not updated:
            raise ValidationError({"detail": "Import is already being applied."})
        transaction.on_commit(lambda: run_in_background(tasks.apply_content_import, instance.pk))
        instance.refresh_from_db()
        return Response(ContentImportSerializer(instance, context=self.get_serializer_context()).data,
                        status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"])
    def changes(self, request, pk=None):
        """Every field the import changes (or changed): `?product=`, `?field=`."""
        instance = self.get_object()
        qs = instance.changes.select_related("product")
        product = request.query_params.get("product")
        if product:
            if not product.isdigit():
                raise ValidationError({"product": "A number expected."})
            qs = qs.filter(product_id=product)
        field = request.query_params.get("field")
        if field:
            qs = qs.filter(field=field)
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
