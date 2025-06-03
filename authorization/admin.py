from django.contrib import admin
from .models import Customer, OTP, FcmToken, CustomerAddresses
from django.contrib.auth.hashers import make_password


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone_number', 'email')
    list_display_links = ('id', 'full_name')
    search_fields = ('full_name', 'phone_number', 'email')

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get('password')
        if password and not change or form.initial['password'] != password:
            obj.password = make_password(password)
        super().save_model(request, obj, form, change)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "resend", "count_attempts", "expire_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer",)
    list_filter = ("resend",)


@admin.register(FcmToken)
class FcmTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "customer")
    list_display_links = ("id", "customer")
    search_fields = ("customer",)

@admin.register(CustomerAddresses)
class CustomerAddressesAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "name")
    list_display_links = ("id", "customer")
    search_fields = ("name", "location_name")

