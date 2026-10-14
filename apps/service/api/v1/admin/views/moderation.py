from django.db.models import Avg, Count, DateTimeField, DurationField, ExpressionWrapper, F, Min, Q, Value
from django.utils import timezone
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from apps.service import moderation
from apps.service.models import ProductModeration
from utils.admin_views import AdminViewMixin
from ..filters import ProductModerationFilter
from ..serializers import ProductModerationListSerializer, ProductModerationSerializer, ModerationRejectSerializer, \
    ModerationBulkApproveSerializer, ModerationBulkApproveResultSerializer, ModerationStatsSerializer

PENDING = ProductModeration.PENDING
APPROVED = ProductModeration.APPROVED
REJECTED = ProductModeration.REJECTED


class ProductModerationViewSet(AdminViewMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    """Moderation queue ("Moderatsiya"): `?status=pending` = the queue (oldest first), approved / rejected = the
    reviewed rows (latest review first). A row gets into the queue when the product form sets
    `publish_status=review`."""
    filterset_class = ProductModerationFilter
    search_fields = ("product__name_ru", "product__name_uz", "product__product_code", "product__articul_code",
                     "product__barcode")
    ordering_fields = ("id", "submitted_at", "reviewed_at")

    def get_queryset(self):
        qs = ProductModeration.objects.all()
        if self.action == "stats":
            return qs
        qs = qs.select_related("product__brand", "submitted_by__staff_profile", "reviewed_by__staff_profile") \
            .prefetch_related(*moderation.readiness_prefetch("product__"))
        if self.action == "retrieve":
            qs = qs.select_related("product__product_item_category__product_sub_category__product_category") \
                .prefetch_related("product__attribute_values__attribute")
        status = self.request.query_params.get("status")
        if status == PENDING:
            return qs.order_by("submitted_at", "id")
        if status in (APPROVED, REJECTED):
            return qs.order_by("-reviewed_at", "-id")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProductModerationListSerializer
        if self.action == "reject":
            return ModerationRejectSerializer
        if self.action == "bulk_approve":
            return ModerationBulkApproveSerializer
        if self.action == "stats":
            return ModerationStatsSerializer
        return ProductModerationSerializer

    def _detail(self, pk):
        return Response(ProductModerationSerializer(self.get_queryset().get(pk=pk),
                                                    context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approves the row and publishes the product (`publish_status=published`). Refused while the product
        fails a readiness check (`missing` = the failed checks)."""
        row = self.get_object()
        try:
            moderation.approve(row.pk, request.user)
        except moderation.ModerationError as error:
            if error.reason == moderation.NOT_READY:
                raise ValidationError({"detail": "The product is not ready.", "missing": error.missing})
            raise ValidationError({"detail": "The row is already reviewed."})
        return self._detail(row.pk)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Returns the product to draft (`publish_status=draft`) with the reason."""
        row = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            moderation.reject(row.pk, request.user, serializer.validated_data["reason"])
        except moderation.ModerationError:
            raise ValidationError({"detail": "The row is already reviewed."})
        return self._detail(row.pk)

    @action(detail=False, methods=["post"], url_path="bulk-approve")
    def bulk_approve(self, request):
        """Approves the selected rows: the ready pending ones are approved, the rest are listed in `skipped`."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approved, skipped = [], []
        for pk in dict.fromkeys(serializer.validated_data["ids"]):
            try:
                moderation.approve(pk, request.user)
                approved.append(pk)
            except moderation.ModerationError as error:
                skipped.append({"id": pk, "reason": error.reason, "missing": error.missing})
        return Response(ModerationBulkApproveResultSerializer({"approved": approved, "skipped": skipped}).data)

    @action(detail=False, methods=["get"], pagination_class=None, filter_backends=[])
    def stats(self, request):
        """Cards and tab counters of the page (ignores the list filters)."""
        now = timezone.now()
        pending = Q(status=PENDING)
        today = Q(reviewed_at__date=now.date())  # USE_TZ=False -> naive local time
        waiting = ExpressionWrapper(Value(now, output_field=DateTimeField()) - F("submitted_at"),
                                    output_field=DurationField())
        data = ProductModeration.objects.aggregate(
            pending=Count("id", filter=pending),
            approved=Count("id", filter=Q(status=APPROVED)),
            rejected=Count("id", filter=Q(status=REJECTED)),
            approved_today=Count("id", filter=Q(status=APPROVED) & today),
            rejected_today=Count("id", filter=Q(status=REJECTED) & today),
            avg_wait=Avg(waiting, filter=pending),
            oldest_submitted_at=Min("submitted_at", filter=pending),
        )
        avg_wait = data.pop("avg_wait")
        data["avg_wait_seconds"] = int(avg_wait.total_seconds()) if avg_wait is not None else None
        oldest = data["oldest_submitted_at"]
        data["oldest_wait_seconds"] = max(int((now - oldest).total_seconds()), 0) if oldest else None
        return Response(self.get_serializer(data).data)
