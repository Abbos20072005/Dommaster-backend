from django.urls import path
from .views import AuthViewSet, OTPViewSet

urlpatterns = [
    path("login/", AuthViewSet.as_view({"post": "login"}), name="login"),
    path("register/", AuthViewSet.as_view({"post": "register"}), name="register"),
    path("auth/me/", AuthViewSet.as_view({"get": "auth_me"}), name="auth_me"),
    path("change/password/", AuthViewSet.as_view({"patch": "change_password"}), name="change_password"),
    path("forgot/password/", AuthViewSet.as_view({"patch": "forgot_password"}), name="forgot_password"),
    path("reset/password/verify/", AuthViewSet.as_view({"post": "verify_reset_otp"}), name="verify_reset_otp"),
    path("reset/password/", AuthViewSet.as_view({"post": "reset_password"}), name="reset_password"),
    path("otp/verify/", OTPViewSet.as_view({"post": "otp_verify"}), name="otp_verify"),
    path("otp/resend/", OTPViewSet.as_view({"post": "otp_resend"}), name="otp_resend"),
    path("customer/update/", AuthViewSet.as_view({"patch": "update_customer_info"}), name="update_customer_info"),
    path("customer/addresses/", AuthViewSet.as_view({"get": "addresses_list", "post": "address_create"}), name="addresses_list"),
    path("customer/addresses/<int:pk>/", AuthViewSet.as_view({"patch": "addresses_update", "delete": "delete_address"}), name="address_update"),
]