from apps.base.models import Banner
from utils.admin_views import AdminModelViewSet
from ..filters import BannerFilter
from ..serializers import BannerSerializer


class BannerViewSet(AdminModelViewSet):
    queryset = Banner.objects.prefetch_related("content_object")
    serializer_class = BannerSerializer
    filterset_class = BannerFilter
    search_fields = ("title_ru", "title_uz", "title_en", "link")
    ordering_fields = ("id", "title", "is_visible", "created_at", "updated_at")
    ordering = ("-id",)

    def perform_destroy(self, instance):
        for image in (instance.desktop_image, instance.mobile_image):
            if image:
                image.delete(save=False)
        instance.delete()
