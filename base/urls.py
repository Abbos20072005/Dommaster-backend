from django.urls import path
from .views import BannerViewSet, ChatViewSet, AboutUsViewSet

urlpatterns = [
    path("banner/", BannerViewSet.as_view({"get": "banner_list"}), name="banner list"),
    path("chat/list/", ChatViewSet.as_view({"get": "message_list"}), name="chat message list"),
    path("chat/create/", ChatViewSet.as_view({"post": "message_create"}), name="chat message create"),
    path("about/", AboutUsViewSet.as_view({"get": "about_us"}), name="about us")
]