from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
import config.schema_extensions  # noqa: F401  registers auth schemes


def docs_urls(suffix, name, patterns, custom_settings=None):
    """OpenAPI schema + swagger ui + redoc for one set of `patterns`: schema/<suffix>, swagger/<suffix>, redoc/<suffix>"""
    return [
        path(f"schema/{suffix}", SpectacularAPIView.as_view(patterns=patterns, custom_settings=custom_settings),
             name=name),
        path(f"swagger/{suffix}", SpectacularSwaggerView.as_view(url_name=name), name=f"{name}-swagger-ui"),
        path(f"redoc/{suffix}", SpectacularRedocView.as_view(url_name=name), name=f"{name}-redoc"),
    ]


urlpatterns = [
    *docs_urls(
        "admin/", "admin-schema",
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
