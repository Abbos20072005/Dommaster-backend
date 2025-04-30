from django.contrib import admin
from .models import Banner, Chat, AboutUs, Messages, Promocodes, News, Articles, Reviews, Video


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("id", "title")
    list_display_links = ("id", "title")
    search_fields = ("title",)

@admin.register(Articles)
class ArticlesAdmin(admin.ModelAdmin):
    list_display = ("id", "title")
    list_display_links = ("id", "title")
    search_fields = ("title",)

@admin.register(Reviews)
class ReviewsAdmin(admin.ModelAdmin):
    list_display = ("id", "title")
    list_display_links = ("id", "title")
    search_fields = ("title",)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    list_display_links = ("id", "name")
    search_fields = ("name",)

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "customer")
    list_display_links = ("id", "customer")


@admin.register(Promocodes)
class PromocodesAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "customer", "expires_at")
    list_display_links = ("id", "name")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        obj.name = obj.name.lower()
        obj.save()


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title')
    list_display_links = ('id', 'title')
    search_fields = ('title', 'short_description')


@admin.register(Messages)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "is_answer")
    list_display_links = ("id", "chat")
    list_filter = ("is_answer",)
    readonly_fields = ("is_answer",)

    def save_model(self, request, obj, form, change):
        obj.is_answer = True
        obj.save()


@admin.register(AboutUs)
class AboutUsAdmin(admin.ModelAdmin):
    list_display = ("id",)
