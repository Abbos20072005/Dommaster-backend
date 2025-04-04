from django.contrib import admin
from .models import Product, ProductCategory, ProductSubCategory, ProductItemCategory, Comment, CommentReply, Order, \
    OrderItem, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_active",)


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
    list_display = ("id", "customer", "product_rating", "product")
    list_display_links = ("id", "customer")
    list_filter = ("product_rating",)


@admin.register(CommentReply)
class CommentReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "defendant_name", "comment")
    list_display_links = ("id", "defendant_name")
    search_fields = ("defendant_name",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total_price")
    list_display_links = ("id", "customer")
    list_filter = ("status",)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity")
    list_display_links = ("id", "order")
