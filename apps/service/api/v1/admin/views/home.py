from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from apps.service.models import HomeBlock, HomePage
from utils.admin_views import AdminModelViewSet, AdminViewMixin
from ..filters import HomeBlockFilter
from ..serializers import HomeBlockSerializer, HomeBlockReorderSerializer, HomePageSerializer, \
    HomePagePublishSerializer


class HomeBlockViewSet(AdminModelViewSet):
    """Blocks of the home page (the draft; customers get what `home-page/publish/` stored)."""
    queryset = HomeBlock.objects.select_related("banner", "badge", "sale")
    serializer_class = HomeBlockSerializer
    filterset_class = HomeBlockFilter
    search_fields = ("title_ru", "title_uz", "title_en")
    ordering_fields = ("id", "position", "created_at", "updated_at")
    ordering = ("position", "id")
    # the whole page is one drag & drop list
    pagination_class = None

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "home_page": HomePage.load()}

    @action(detail=False, methods=["post"], serializer_class=HomeBlockReorderSerializer)
    def reorder(self, request):
        """`ids` in the new order: all blocks, or the blocks of one tab (they are rearranged within their places)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class HomePageAPIView(AdminViewMixin, RetrieveUpdateAPIView):
    """Display rules of the home page + its publish state."""
    serializer_class = HomePageSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return HomePage.load()


class HomePagePublishAPIView(AdminViewMixin, GenericAPIView):
    """Publish the draft (blocks + rules)."""
    serializer_class = HomePagePublishSerializer

    def post(self, request):
        serializer = self.get_serializer(HomePage.load(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
