from django.urls import path, include
from integration.one_c import OneCIntegrationViewSet

urlpatterns = [
    path("api/v1/auth/", include("authorization.api.v1.client.urls")),
    path("api/v1/base/", include("base.api.v1.client.urls")),
    path("api/v1/", include("service.api.v1.client.urls")),
    path("api/v1/integration/", include("integration.urls")),
    path(
        "api/v1/orders/<int:order_id>/status/",
        OneCIntegrationViewSet.as_view({"patch": "order_status_update"}),
        name="one_c_order_status",
    ),
    path("", include("payment.api.v1.client.urls")),
]
