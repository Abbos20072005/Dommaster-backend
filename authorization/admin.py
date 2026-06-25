from django.contrib import admin
from .models import Customer, OTP, FcmToken, CustomerAddresses, PasswordResetToken
from django.contrib.auth.hashers import make_password
from unfold.admin import ModelAdmin
from base.admin_actions import mark_verified, mark_unverified, mark_default


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ('id', 'full_name', 'phone_number', 'email', 'verified', 'created_at')
    list_display_links = ('id', 'full_name')
    search_fields = ('full_name', 'phone_number', 'email')
    list_filter = ('verified', 'created_at')
    date_hierarchy = "created_at"
    actions = [mark_verified, mark_unverified]

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get('password')
        if password and not change or form.initial['password'] != password:
            obj.password = make_password(password)
        super().save_model(request, obj, form, change)


@admin.register(OTP)
class OTPAdmin(ModelAdmin):
    list_display = ("id", "customer", "otp_code", "resend", "count_attempts", "expire_at", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "otp_code")
    list_filter = ("resend", "created_at")
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(FcmToken)
class FcmTokenAdmin(ModelAdmin):
    list_display = ("id", "customer", "device_id", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "device_id", "fcm_token")
    list_filter = ("created_at",)
    autocomplete_fields = ("customer",)
    date_hierarchy = "created_at"


@admin.register(CustomerAddresses)
class CustomerAddressesAdmin(ModelAdmin):
    list_display = ("id", "customer", "name", "location_name", "is_default", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("name", "location_name", "customer__full_name", "customer__phone_number")
    list_filter = ("is_default", "created_at")
    autocomplete_fields = ("customer",)
    date_hierarchy = "created_at"
    actions = [mark_default]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(ModelAdmin):
    list_display = ("id", "customer", "is_used", "expires_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "token")
    list_filter = ("is_used", "expires_at")
    autocomplete_fields = ("customer",)
