from rest_framework.routers import SimpleRouter
from .views import OrderViewSet

# SimpleRouter: mounted at the admin root, DefaultRouter's API-root view would take `api/v1/admin/`
router = SimpleRouter()
router.register("orders", OrderViewSet, basename="admin_order")

urlpatterns = router.urls
