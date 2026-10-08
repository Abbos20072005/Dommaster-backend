from rest_framework.routers import SimpleRouter
from .views import StaffViewSet

# SimpleRouter: DefaultRouter's API-root view would shadow the list route at the empty prefix
router = SimpleRouter()
router.register("", StaffViewSet, basename="admin_staff")

urlpatterns = router.urls
