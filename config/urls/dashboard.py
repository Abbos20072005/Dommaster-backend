# Admin (dashboard) API, mounted at api/v1/admin/
from django.urls import path, include

urlpatterns = [
    path("auth/", include("authorization.api.v1.admin.urls")),
]
