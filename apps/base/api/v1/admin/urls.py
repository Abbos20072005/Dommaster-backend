from rest_framework.routers import SimpleRouter
from .views import MarketBranchViewSet, ChatViewSet, MessageViewSet

router = SimpleRouter()
router.register("branches", MarketBranchViewSet, basename="admin_branch")
router.register("chats", ChatViewSet, basename="admin_chat")
router.register("messages", MessageViewSet, basename="admin_message")

urlpatterns = router.urls
