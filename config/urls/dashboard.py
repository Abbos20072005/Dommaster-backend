# Admin (dashboard) API, mounted at api/v1/admin/
from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.authorization.api.v1.admin.urls")),
    path("customers/", include("apps.authorization.api.v1.admin.customer_urls")),
    path("", include("apps.service.api.v1.admin.urls")),
]
