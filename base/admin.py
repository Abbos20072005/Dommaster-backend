from django.contrib import admin
from .models import Banner, Chat, AboutUs, Messages, Promocodes, News, Articles, Reviews, Video, DeleteButton, LoyaltyCard, Notification
from base.admin_actions import make_visible, make_hidden, activate, deactivate, mark_as_answer


@admin.register(DeleteButton)
class DeleteButtonAdmin(admin.ModelAdmin):
    list_display = ("id", "is_deleted", "created_at")
    list_display_links = ("id", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("id",)
    list_per_page = 25
    actions = [make_visible, make_hidden]


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at")
    list_display_links = ("id", "title")
    search_fields = ("title",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Articles)
class ArticlesAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at")
    list_display_links = ("id", "title")
    search_fields = ("title", "short_description")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Reviews)
class ReviewsAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at")
    list_display_links = ("id", "title")
    search_fields = ("title", "short_description")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name", "url")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "chat_token", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "chat_token")
    list_filter = ("created_at",)
    autocomplete_fields = ("customer",)
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(Promocodes)
class PromocodesAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "customer", "discount_precent", "discount_price", "expires_at", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name", "code", "customer__full_name", "customer__phone_number")
    list_filter = ("expires_at", "created_at")
    autocomplete_fields = ("customer",)
    date_hierarchy = "created_at"
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        obj.name = obj.name.lower()
        obj.save()


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_visible', 'created_at')
    list_display_links = ('id', 'title')
    search_fields = ('title', 'link')
    list_filter = ('is_visible', 'created_at')
    date_hierarchy = "created_at"
    actions = [make_visible, make_hidden]


@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "is_answer", "created_at")
    list_display_links = ("id", "chat")
    list_filter = ("is_answer", "created_at")
    search_fields = ("chat__id", "message")
    readonly_fields = ("is_answer",)
    date_hierarchy = "created_at"
    list_per_page = 25
    actions = [mark_as_answer]

    def save_model(self, request, obj, form, change):
        obj.is_answer = True
        obj.save()


@admin.register(AboutUs)
class AboutUsAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "updated_at")


@admin.register(LoyaltyCard)
class LoyaltyCardAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "card_number", "customer", "is_active", "created_at")
    list_display_links = ("id", "full_name")
    search_fields = ("full_name", "card_number", "customer__full_name", "customer__phone_number")
    list_filter = ("is_active", "created_at")
    autocomplete_fields = ("customer",)
    date_hierarchy = "created_at"
    actions = [activate, deactivate]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at")
    list_display_links = ("id", "title")
    search_fields = ("title", "description")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"
