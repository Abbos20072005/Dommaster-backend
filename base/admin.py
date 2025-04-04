from django.contrib import admin
from .models import Banner, Chat

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    list_display_links = ('id', 'title')
    search_fields = ('title', 'short_description')

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "is_answer")
    list_display_links = ("id", "customer")
    list_filter = ("is_answer",)
