from django.contrib import admin
from .models import Product, ProductCategory, ProductSubCategory, ProductItemCategory, Comment, CommentReply

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "price", "rating", "product_item_category")
    list_display_links = ("id", "name")
    search_fields = ("name", "code")
    list_filter = ("price", "rating")

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    list_display_links = ("id", "name")
    search_fields = ("name",)

@admin.register(ProductSubCategory)
class ProductSubCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "product_category")
    list_display_links = ("id", "name")
    search_fields = ("name",)

@admin.register(ProductItemCategory)
class ProductItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "product_sub_category")
    list_display_links = ("id", "name")
    search_fields = ("name",)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "commentator_name", "product_rating", "product")
    list_display_links = ("id", "commentator_name")
    search_fields = ("commentator_name",)
    list_filter = ("product_rating",)

@admin.register(CommentReply)
class CommentReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "defendant_name", "comment")
    list_display_links = ("id", "defendant_name")
    search_fields = ("defendant_name",)

