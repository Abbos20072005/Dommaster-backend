from django.contrib import admin
from .models import Product, ProductCategory, ProductSubCategory, ProductItemCategory, Comment, Order, \
    OrderItem, Tag, Brand, Sale, AddsBrands, ProductImage, Favourites, Cart, CartItem, Questions, \
    ProductCharacteristics, RecentlyViewedProducts, Service, CommentImages, CommentReply, QuestionsReply, \
    CategoryAttribute, CategoryAttributeValue, ProductAttributeValue

@admin.register(QuestionsReply)
class QuestionsReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "question", "is_admin", "is_visible")
    list_display_links = ("id", "customer")
    list_filter = ("is_admin", "is_visible")

@admin.register(CommentReply)
class CommentReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "comment", "is_admin", "is_visible")
    list_display_links = ("id", "customer")
    list_filter = ("is_admin", "is_visible")

    def save_model(self, request, obj, form, change):
        obj.is_admin = True
        obj.save()

@admin.register(CommentImages)
class CommentImagesAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "comment")
    list_display_links = ("id", "customer")

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    list_display_links = ("id", "name")
    search_fields = ("name",)


@admin.register(RecentlyViewedProducts)
class RecentlyViewedProductsAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "product")
    list_display_links = ("id", "customer")


@admin.register(ProductCharacteristics)
class ProductCharacteristicsAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "name", "unit", "value")
    list_display_links = ("id", "product")
    search_fields = ("name",)
    list_filter = ("unit",)


class CategoryAttributeValueInline(admin.TabularInline):
    model = CategoryAttributeValue
    extra = 1


@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "is_filterable", "position")
    list_display_links = ("id", "name")
    list_filter = ("category", "is_filterable")
    search_fields = ("name",)
    inlines = [CategoryAttributeValueInline]


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 1


@admin.register(Questions)
class QuestionsAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "product", "is_visible")
    list_display_links = ("id", "customer")
    search_fields = ("message",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "customer")
    list_display_links = ("id", "customer")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product")
    list_display_links = ("id", "cart")


@admin.register(Favourites)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "product")
    list_display_links = ("id", "customer")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product")
    list_display_links = ("id", "product")


@admin.register(AddsBrands)
class AddsBrandsAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_visible")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_visible",)
    autocomplete_fields = ("products",)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "discount_from", "discount_to", "is_main", "is_visible")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_visible",)
    autocomplete_fields = ("products",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_visible")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_visible",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_active",)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductCharacteristicsInline(admin.TabularInline):
    model = ProductCharacteristics
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "rating", "product_item_category")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("price", "rating")
    readonly_fields = ("discount_price",)
    inlines = (ProductImageInline, ProductCharacteristicsInline, ProductAttributeValueInline)

    def save_model(self, request, obj, form, change):
        if obj.discount:
            obj.discount_price = obj.price * (1 - (obj.discount / 100))
        obj.save()


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


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total_price")
    list_display_links = ("id", "customer")
    list_filter = ("status",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity")
    list_display_links = ("id", "order")
