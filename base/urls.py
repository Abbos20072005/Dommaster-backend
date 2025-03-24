from django.urls import path
from .views import BaseViewSet

urlpatterns = [
    path("banner/", BaseViewSet.as_view({"get": "banner_list"}), name="banner list")
]