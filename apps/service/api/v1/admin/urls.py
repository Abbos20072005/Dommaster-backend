from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import OrderViewSet, ProductViewSet
from .dashboard_views import DashboardAPIView

# SimpleRouter: mounted at the admin root, DefaultRouter's API-root view would take `api/v1/admin/`
router = SimpleRouter()
router.register("orders", OrderViewSet, basename="admin_order")
router.register("products", ProductViewSet, basename="admin_product")

urlpatterns = router.urls + [
    path("dashboard/", DashboardAPIView.as_view(), name="admin_dashboard"),
]
