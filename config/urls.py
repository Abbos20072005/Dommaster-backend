from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.static import serve
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

admin.site.site_header = 'Dommaster Admin'
admin.site.site_title = 'Dommaster Admin'
admin.site.index_title = 'Welcome to Dommaster dashboard'

schema_view = get_schema_view(
    openapi.Info(
        title="Dommaster APIv1",
        default_version="v1",
        description="API for project Dommaster",
        terms_of_service="",
        contact=openapi.Contact(email="hikmatullaevabbos24@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path("api/v1/auth/", include("authorization.urls")),
    path("api/v1/base/", include("base.urls")),
    path("api/v1/", include("service.urls")),
    path("click/", include("payment.urls")),
    path('payment/', include('payment.urls')),

    re_path(r'static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    re_path(r'media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.SHOW_SWAGGER:
    urlpatterns += [
        re_path(
            r"^swagger(?P<format>\.json|\.yaml)$",
            schema_view.without_ui(cache_timeout=0),
            name="schema-json",
        ),
        re_path(
            r"^swagger/$",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
        re_path(
            r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
        )
    ]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)