from django.urls import path, include
from apps.integration.one_c import OneCIntegrationViewSet

urlpatterns = [
    path("api/v1/auth/", include("apps.authorization.api.v1.client.urls")),
    path("api/v1/base/", include("apps.base.api.v1.client.urls")),
    path("api/v1/", include("apps.service.api.v1.client.urls")),
    path("api/v1/integration/", include("apps.integration.urls")),
    path(
        "api/v1/orders/<int:order_id>/status/",
        OneCIntegrationViewSet.as_view({"patch": "order_status_update"}),
        name="one_c_order_status",
    ),
    path("", include("apps.payment.api.v1.client.urls")),
]
