from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.static import serve

admin.site.site_header = 'Dommaster Admin'
admin.site.site_title = 'Dommaster Admin'
admin.site.index_title = 'Welcome to Dommaster dashboard'

urlpatterns = [
    path("admin/", admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path("api/v1/admin/", include("config.urls.dashboard")),
    path("", include("config.urls.client")),

    re_path(r'static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    re_path(r'media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.SHOW_SWAGGER:
    urlpatterns += [path("", include("config.urls.swagger"))]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
