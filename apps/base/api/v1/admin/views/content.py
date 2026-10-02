from apps.base.models import Articles, News, Video
from utils.admin_views import AdminModelViewSet
from ..filters import CreatedRangeFilter
from ..serializers import ArticlesListSerializer, ArticlesSerializer, NewsListSerializer, NewsSerializer, \
    VideoSerializer


class NewsViewSet(AdminModelViewSet):
    queryset = News.objects.all()
    filterset_class = CreatedRangeFilter
    search_fields = ("title_ru", "title_uz", "title_en")
    ordering_fields = ("id", "title", "created_at", "updated_at")
    ordering = ("-id",)

    def get_serializer_class(self):
        if self.action == "list":
            return NewsListSerializer
        return NewsSerializer

    def perform_destroy(self, instance):
        if instance.image:
            instance.image.delete(save=False)
        instance.delete()


class ArticlesViewSet(AdminModelViewSet):
    queryset = Articles.objects.all()
    filterset_class = CreatedRangeFilter
    search_fields = ("title", "short_description")
    ordering_fields = ("id", "title", "created_at", "updated_at")
    ordering = ("-id",)

    def get_serializer_class(self):
        if self.action == "list":
            return ArticlesListSerializer
        return ArticlesSerializer


class VideoViewSet(AdminModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    filterset_class = CreatedRangeFilter
    search_fields = ("name_ru", "name_uz", "name_en", "url")
    ordering_fields = ("id", "name", "created_at", "updated_at")
    ordering = ("-id",)
