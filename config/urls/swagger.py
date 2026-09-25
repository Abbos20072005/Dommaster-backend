from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
import config.schema_extensions  # noqa: F401  registers auth schemes


def docs_urls(prefix, name, patterns, custom_settings=None):
    """OpenAPI schema + swagger ui + redoc for one set of `patterns`, under `prefix`."""
    return [
        path(f"{prefix}schema/", SpectacularAPIView.as_view(patterns=patterns, custom_settings=custom_settings),
             name=name),
        path(f"{prefix}swagger/", SpectacularSwaggerView.as_view(url_name=name), name=f"{name}-swagger-ui"),
        path(f"{prefix}redoc/", SpectacularRedocView.as_view(url_name=name), name=f"{name}-redoc"),
    ]


urlpatterns = [
    # admin docs not under `admin/` — django admin's catch-all would swallow it
    *docs_urls(
        "api/v1/admin/", "admin-schema",
        [path("api/v1/admin/", include("config.urls.dashboard"))],
        {
            "TITLE": "Dommaster Admin APIv1",
            "DESCRIPTION": "Dashboard API. Auth: Bearer token from /api/v1/admin/auth/login/",
            # tag operations by the first segment after this prefix (auth, products, ...)
            "SCHEMA_PATH_PREFIX": "/api/v1/admin/",
        },
    ),
    *docs_urls("", "schema", [path("", include("config.urls.client"))]),
]
