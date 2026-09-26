from rest_framework.routers import SimpleRouter
from .views import CustomerViewSet

# SimpleRouter: DefaultRouter's API-root view would shadow the list route at the empty prefix
router = SimpleRouter()
router.register("", CustomerViewSet, basename="admin_customer")

urlpatterns = router.urls
