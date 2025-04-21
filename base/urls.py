from django.urls import path
from .views import BannerViewSet, ChatViewSet, AboutUsViewSet, QuestionsViewSet

urlpatterns = [
    path("banner/", BannerViewSet.as_view({"get": "banner_list"}), name="banner list"),
    path("chat/", ChatViewSet.as_view({"get": "message_list", "post": "message_create"}), name="chat message list"),
    path("about/", AboutUsViewSet.as_view({"get": "about_us"}), name="about us"),
    path("questions/", QuestionsViewSet.as_view({"get": "questions_list"}), name="question list"),
    path("questions/<int:pk>/",
         QuestionsViewSet.as_view({"post": "question_create", "patch": "update_question", "delete": "delete_question"}),
         name="create question")
]
