from django.urls import path
from .views import AuthViewSet

urlpatterns = [
    path("login/", AuthViewSet.as_view({'post': 'login'}), name='login'),
    path("register/", AuthViewSet.as_view({'post': 'register'}), name='register'),
    path("auth/me/", AuthViewSet.as_view({'get': 'auth_me'}), name='auth_me')
]