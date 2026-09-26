from django.urls import path
from .views import AdminLoginAPIView, AdminTokenRefreshAPIView, AdminMeAPIView

urlpatterns = [
    path("login/", AdminLoginAPIView.as_view(), name="admin_login"),
    path("token/refresh/", AdminTokenRefreshAPIView.as_view(), name="admin_token_refresh"),
    path("me/", AdminMeAPIView.as_view(), name="admin_me"),
]
