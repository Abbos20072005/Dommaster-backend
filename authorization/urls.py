from django.urls import path
from .views import AuthViewSet, OTPViewSet

urlpatterns = [
    path("login/", AuthViewSet.as_view({"post": "login"}), name="login"),
    path("register/", AuthViewSet.as_view({"post": "register"}), name="register"),
    path("auth/me/", AuthViewSet.as_view({"get": "auth_me"}), name="auth_me"),
    path("change/password/", AuthViewSet.as_view({"patch": "change_password"}), name="change password"),
    path("forgot/password/", AuthViewSet.as_view({"patch": "forgot_password"}), name="forgot password"),
    path("otp/verify/", OTPViewSet.as_view({"post": "otp_verify"}), name="otp verify"),
    path("otp/resend/", OTPViewSet.as_view({"post": "otp_resend"}), name="otp resend"),
    path("customer/update/", AuthViewSet.as_view({"patch": "update_customer_info"}), name="update customer info"),
    path("customer/address/", AuthViewSet.as_view({"get": "addresses_list"}), name="addresses list"),
    path("customer/address/create/", AuthViewSet.as_view({"post": "address_create"}), name="address create"),
    path("customer/address/update/<int:pk>/", AuthViewSet.as_view({"patch": "addresses_update"}), name="address update"),
    path("customer/address/delete/<int:pk>/", AuthViewSet.as_view({"delete": "delete_address"}), name="delete address")
]