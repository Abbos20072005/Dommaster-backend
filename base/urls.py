from django.urls import path
from .views import BannerViewSet, ChatViewSet, AboutUsViewSet, PromocodeViewSet, NewsViewSet, ArticlesViewSet, \
    ReviewsViewSet, VideoViewSet, DeleteButtonViewSet, BaseInformationViewSet, BranchViewSet

urlpatterns = [
    path("banner/", BannerViewSet.as_view({"get": "banner_list"}), name="banner_list"),
    path("branches/", BranchViewSet.as_view({"get": "branch_list"}), name="branch_list"),
    path("branches/<int:pk>/", BranchViewSet.as_view({"get": "branch_detail"}), name="branch_detail"),
    path("chat/", ChatViewSet.as_view({"get": "message_list", "post": "message_create"}), name="chat_message_list"),
    path("about/", AboutUsViewSet.as_view({"get": "about_us"}), name="about_us"),
    path("promocode/checker/", PromocodeViewSet.as_view({"post": "promocode_checker"}), name="promocode_checker"),
    path("promocodes/", PromocodeViewSet.as_view({"get": "promocode_list"}), name="promocode_list"),
    path("news/", NewsViewSet.as_view({"get": "news_list"}), name="news_list"),
    path("news/<int:pk>/", NewsViewSet.as_view({"get": "news_detail"}), name="news_detail"),
    path("articles/", ArticlesViewSet.as_view({"get": "articles_list"}), name="articles_list"),
    path("articles/<int:pk>/", ArticlesViewSet.as_view({"get": "articles_detail"}), name="articles_detail"),
    path("reviews/", ReviewsViewSet.as_view({"get": "reviews_list"}), name="reviews_list"),
    path("reviews/<int:pk>/", ReviewsViewSet.as_view({"get": "reviews_detail"}), name="reviews_detail"),
    path("video/", VideoViewSet.as_view({"get": "video_list"}), name="video_list"),
    path("video/<int:pk>/", VideoViewSet.as_view({"get": "video_detail"}), name="video_detail"),
    path("delete-button/", DeleteButtonViewSet.as_view({"get": "delete_button"}), name="delete_button"),
    path("info/", BaseInformationViewSet.as_view({"get": "base_info"}), name="base_info"),
]
