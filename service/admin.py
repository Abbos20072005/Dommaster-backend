from django.contrib import admin
from .models import Product, ProductCategory, ProductSubCategory, ProductItemCategory, Comment, Order, \
    OrderItem, Tag, Brand, Sale, AddsBrands, ProductImage, Favourites, Cart, CartItem, Questions, \
    ProductCharacteristics, RecentlyViewedProducts, Service, CommentImages, CommentReply, QuestionsReply, \
    CategoryAttribute, CategoryAttributeValue, ProductAttributeValue, ProductVariantGroup, ProductVariantItem, \
    Announcements
from unfold.admin import ModelAdmin, TabularInline


@admin.register(QuestionsReply)
class QuestionsReplyAdmin(ModelAdmin):
    list_display = ("id", "customer", "question", "is_admin", "is_visible", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "answer")
    list_filter = ("is_admin", "is_visible", "created_at")
    autocomplete_fields = ("customer", "question")
    date_hierarchy = "created_at"


@admin.register(CommentReply)
class CommentReplyAdmin(ModelAdmin):
    list_display = ("id", "customer", "comment", "is_admin", "is_visible", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "reply_comment")
    list_filter = ("is_admin", "is_visible", "created_at")
    autocomplete_fields = ("customer", "comment")
    date_hierarchy = "created_at"

    def save_model(self, request, obj, form, change):
        obj.is_admin = True
        obj.save()


@admin.register(CommentImages)
class CommentImagesAdmin(ModelAdmin):
    list_display = ("id", "customer", "comment", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number")
    autocomplete_fields = ("customer", "comment")
    date_hierarchy = "created_at"


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ("id", "name", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(RecentlyViewedProducts)
class RecentlyViewedProductsAdmin(ModelAdmin):
    list_display = ("id", "customer", "product", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "product__name")
    list_filter = ("created_at",)
    autocomplete_fields = ("customer", "product")
    date_hierarchy = "created_at"


@admin.register(ProductCharacteristics)
class ProductCharacteristicsAdmin(ModelAdmin):
    list_display = ("id", "product", "name", "unit", "value")
    list_display_links = ("id", "product")
    search_fields = ("name", "value", "product__name")
    list_filter = ("unit",)
    autocomplete_fields = ("product",)


class CategoryAttributeValueInline(TabularInline):
    model = CategoryAttributeValue
    extra = 1


@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(ModelAdmin):
    list_display = ("id", "name", "category", "is_filterable", "position")
    list_display_links = ("id", "name")
    list_filter = ("category", "is_filterable")
    search_fields = ("name", "category__name")
    autocomplete_fields = ("category",)
    inlines = [CategoryAttributeValueInline]


class ProductAttributeValueInline(TabularInline):
    model = ProductAttributeValue
    extra = 1


@admin.register(Questions)
class QuestionsAdmin(ModelAdmin):
    list_display = ("id", "customer", "product", "is_visible", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "question", "product__name")
    list_filter = ("is_visible", "created_at")
    autocomplete_fields = ("customer", "product")
    date_hierarchy = "created_at"


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ("id", "customer", "total_price", "total_items", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "cart_token")
    list_filter = ("created_at",)
    autocomplete_fields = ("customer",)
    date_hierarchy = "created_at"


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ("id", "cart", "product", "quantity", "is_checked")
    list_display_links = ("id", "cart")
    search_fields = ("cart__customer__full_name", "product__name", "cart__cart_token")
    list_filter = ("is_checked",)
    autocomplete_fields = ("cart", "product")


@admin.register(Favourites)
class FavouriteAdmin(ModelAdmin):
    list_display = ("id", "customer", "product", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "product__name")
    list_filter = ("created_at",)
    autocomplete_fields = ("customer", "product")
    date_hierarchy = "created_at"


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    list_display = ("id", "product", "created_at")
    list_display_links = ("id", "product")
    search_fields = ("product__name",)
    list_filter = ("created_at",)
    autocomplete_fields = ("product",)
    date_hierarchy = "created_at"


@admin.register(AddsBrands)
class AddsBrandsAdmin(ModelAdmin):
    list_display = ("id", "name", "brand", "is_visible", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name", "brand__name", "title")
    list_filter = ("is_visible", "created_at")
    autocomplete_fields = ("products", "brand")
    date_hierarchy = "created_at"


@admin.register(Sale)
class SaleAdmin(ModelAdmin):
    list_display = ("id", "name", "discount_from", "discount_to", "is_main", "is_visible")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_main", "is_visible", "discount_from", "discount_to")
    autocomplete_fields = ("products",)
    date_hierarchy = "created_at"


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ("id", "name", "is_visible", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_visible", "created_at")
    date_hierarchy = "created_at"


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_active", "created_at")
    date_hierarchy = "created_at"


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1


class ProductCharacteristicsInline(TabularInline):
    model = ProductCharacteristics
    extra = 1


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("id", "name", "price", "discount_price", "rating", "quantity", "is_active", "product_item_category", "brand")
    list_display_links = ("id", "name")
    search_fields = ("name", "brand__name", "product_item_category__name")
    list_filter = ("brand", "product_item_category", "is_active", "unit", "created_at")
    readonly_fields = ("discount_price",)
    autocomplete_fields = ("brand", "product_item_category")
    inlines = (ProductImageInline, ProductCharacteristicsInline, ProductAttributeValueInline)
    date_hierarchy = "created_at"
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        if obj.discount:
            obj.discount_price = obj.price * (1 - (obj.discount / 100))
        obj.save()


@admin.register(ProductCategory)
class ProductCategoryAdmin(ModelAdmin):
    list_display = ("id", "name", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(ProductSubCategory)
class ProductSubCategoryAdmin(ModelAdmin):
    list_display = ("id", "name", "product_category", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name", "product_category__name")
    list_filter = ("product_category", "created_at")
    autocomplete_fields = ("product_category",)
    date_hierarchy = "created_at"


@admin.register(ProductItemCategory)
class ProductItemCategoryAdmin(ModelAdmin):
    list_display = ("id", "name", "product_sub_category", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name", "product_sub_category__name")
    list_filter = ("product_sub_category", "created_at")
    autocomplete_fields = ("product_sub_category",)
    date_hierarchy = "created_at"


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("id", "customer", "product", "product_rating", "is_visible", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "comment", "product__name")
    list_filter = ("product_rating", "is_visible", "created_at")
    autocomplete_fields = ("customer", "product")
    date_hierarchy = "created_at"


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ("id", "customer", "status", "payment_status", "delivery_type", "total_price", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "id")
    list_filter = ("status", "payment_status", "delivery_type", "created_at")
    autocomplete_fields = ("customer", "promocode", "order_location")
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "created_at")
    list_display_links = ("id", "order")
    search_fields = ("order__id", "order__customer__full_name", "product__name")
    list_filter = ("created_at",)
    autocomplete_fields = ("order", "product")
    date_hierarchy = "created_at"


class ProductVariantItemInline(TabularInline):
    model = ProductVariantItem
    extra = 1
    autocomplete_fields = ("product",)


@admin.register(ProductVariantGroup)
class ProductVariantGroupAdmin(ModelAdmin):
    list_display = ("id", "name", "display_type", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("display_type", "created_at")
    inlines = [ProductVariantItemInline]
    date_hierarchy = "created_at"


@admin.register(Announcements)
class AnnouncementsAdmin(ModelAdmin):
    list_display = ("id", "title", "created_at")
    list_display_links = ("id", "title")
    search_fields = ("title", "description")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"
