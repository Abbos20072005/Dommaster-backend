from django.urls import path
from .views import BannerViewSet, ChatViewSet, AboutUsViewSet, PromocodeViewSet, NewsViewSet, ArticlesViewSet, ReviewsViewSet, VideoViewSet

urlpatterns = [
    path("banner/", BannerViewSet.as_view({"get": "banner_list"}), name="banner list"),
    path("chat/", ChatViewSet.as_view({"get": "message_list", "post": "message_create"}), name="chat message list"),
    path("about/", AboutUsViewSet.as_view({"get": "about_us"}), name="about us"),
    path("promocode/checker/", PromocodeViewSet.as_view({"post": "promocode_checker"}), name="promocode checker"),
    path("promocodes/", PromocodeViewSet.as_view({"get": "promocode_list"}), name="promocode list"),
    path("news/", NewsViewSet.as_view({"get": "news_list"}), name="news list"),
    path("news/<int:pk>/", NewsViewSet.as_view({"get": "news_detail"}), name="news detail"),
    path("articles/", ArticlesViewSet.as_view({"get": "articles_list"}), name="articles list"),
    path("articles/<int:pk>/", ArticlesViewSet.as_view({"get": "articles_detail"}), name="articles detail"),
    path("reviews/", ReviewsViewSet.as_view({"get": "reviews_list"}), name="reviews list"),
    path("reviews/<int:pk>/", ReviewsViewSet.as_view({"get": "reviews_detail"}), name="reviews detail"),
    path("video/", VideoViewSet.as_view({"get": "video_list"}), name="video list"),
    path("video/<int:pk>/", VideoViewSet.as_view({"get": "video_detail"}), name="video detail"),

]
