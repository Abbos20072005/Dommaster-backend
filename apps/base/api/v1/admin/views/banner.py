from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.base.models import Banner
from apps.service.api.v1.admin.serializers import CategoryReorderSerializer
from utils.admin_views import AdminModelViewSet
from ..filters import BannerFilter
from ..serializers import BannerSerializer, BannerStatsSerializer


class BannerViewSet(AdminModelViewSet):
    queryset = Banner.objects.prefetch_related("content_object")
    serializer_class = BannerSerializer
    filterset_class = BannerFilter
    search_fields = ("title_ru", "title_uz", "title_en", "link", "page")
    ordering_fields = ("id", "title", "position", "starts_at", "ends_at", "is_visible", "created_at", "updated_at")
    ordering = ("position", "id")

    def perform_destroy(self, instance):
        for image in (instance.desktop_image, instance.mobile_image):
            if image:
                image.delete(save=False)
        instance.delete()

    @action(detail=False, methods=["get"], filter_backends=[], pagination_class=None,
            serializer_class=BannerStatsSerializer)
    def stats(self, request):
        """Cards and tab counters of the banners page (all banners, list filters are not applied)."""
        shown = Q(is_visible=True)
        data = Banner.objects.aggregate(
            active=Count("id", filter=Banner.status_q(Banner.ACTIVE)),
            scheduled=Count("id", filter=Banner.status_q(Banner.SCHEDULED)),
            expired=Count("id", filter=Banner.status_q(Banner.EXPIRED)),
            archived=Count("id", filter=Banner.status_q(Banner.ARCHIVED)),
            external=Count("id", filter=shown & Q(link_type=Banner.URL)),
            **{placement: Count("id", filter=shown & Q(placement=placement))
               for placement, _ in Banner.PLACEMENT_CHOICES},
        )
        return Response(self.get_serializer(data).data)

    @action(detail=False, methods=["post"], serializer_class=CategoryReorderSerializer)
    def reorder(self, request):
        """Drag & drop inside a tab: `ids` = banners of one placement in the new order, list index becomes
        `position`."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
