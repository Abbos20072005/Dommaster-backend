from rest_framework.routers import SimpleRouter
from .views import BannerViewSet, MarketBranchViewSet, ChatViewSet, MessageViewSet, NewsViewSet, ArticlesViewSet, \
    VideoViewSet

router = SimpleRouter()
router.register("banners", BannerViewSet, basename="admin_banner")
router.register("branches", MarketBranchViewSet, basename="admin_branch")
router.register("chats", ChatViewSet, basename="admin_chat")
router.register("messages", MessageViewSet, basename="admin_message")
router.register("news", NewsViewSet, basename="admin_news")
router.register("articles", ArticlesViewSet, basename="admin_articles")
router.register("videos", VideoViewSet, basename="admin_video")

urlpatterns = router.urls
