from django.contrib import admin
from .models import Customer
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

