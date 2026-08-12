from django.contrib import admin, messages
from django.db.models import Count
from django.shortcuts import render
from .models import Product, ProductCategory, ProductSubCategory, ProductItemCategory, Comment, Order, \
    OrderItem, Tag, Brand, Sale, AddsBrands, ProductImage, Favourites, Cart, CartItem, Questions, \
    ProductCharacteristics, RecentlyViewedProducts, Service, CommentImages, CommentReply, QuestionsReply, \
    ProductVariantGroup, ProductVariantItem, \
    Announcements, ProductItemCategoryFilterSchema, ProductFilterNumericValue, ProductUnit, ProductRemaining
from .signals import clear_category_filter_cache
from unfold.admin import ModelAdmin, TabularInline
from base.admin_actions import make_visible, make_hidden, activate, deactivate, get_model_fields, \
    mark_as_main, mark_as_not_main, status_collecting, status_delivering, status_completed, status_canceled


@admin.register(QuestionsReply)
class QuestionsReplyAdmin(ModelAdmin):
    list_display = get_model_fields(QuestionsReply)
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "answer")
    list_filter = ("is_admin", "is_visible", "created_at")
    autocomplete_fields = ("customer", "question")
    date_hierarchy = "created_at"
    actions = [make_visible, make_hidden]


@admin.register(CommentReply)
class CommentReplyAdmin(ModelAdmin):
    list_display = get_model_fields(CommentReply)
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "reply_comment")
    list_filter = ("is_admin", "is_visible", "created_at")
    autocomplete_fields = ("customer", "comment")
    date_hierarchy = "created_at"
    actions = [make_visible, make_hidden]

    def save_model(self, request, obj, form, change):
        obj.is_admin = True
        obj.save()


@admin.register(CommentImages)
class CommentImagesAdmin(ModelAdmin):
    list_display = get_model_fields(CommentImages)
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number")
    autocomplete_fields = ("customer", "comment")
    date_hierarchy = "created_at"


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = get_model_fields(Service)
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(RecentlyViewedProducts)
class RecentlyViewedProductsAdmin(ModelAdmin):
    list_display = get_model_fields(RecentlyViewedProducts)
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "product__name")
    list_filter = ("created_at",)
    autocomplete_fields = ("customer", "product")
    date_hierarchy = "created_at"


@admin.register(ProductCharacteristics)
class ProductCharacteristicsAdmin(ModelAdmin):
    list_display = get_model_fields(ProductCharacteristics)
    list_display_links = ("id", "product")
    search_fields = ("name", "value", "product__name")
    list_filter = ("unit",)
    autocomplete_fields = ("product",)


@admin.register(Questions)
class QuestionsAdmin(ModelAdmin):
    list_display = get_model_fields(Questions)
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "question", "product__name")
    list_filter = ("is_visible", "created_at")
    autocomplete_fields = ("customer", "product")
    date_hierarchy = "created_at"
    actions = [make_visible, make_hidden]


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = get_model_fields(Cart)
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "cart_token")
    list_filter = ("created_at",)
    autocomplete_fields = ("customer",)
    date_hierarchy = "created_at"


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = get_model_fields(CartItem)
    list_display_links = ("id", "cart")
    search_fields = ("cart__customer__full_name", "product__name", "cart__cart_token")
    list_filter = ("is_checked",)
    autocomplete_fields = ("cart", "product")


@admin.register(Favourites)
class FavouriteAdmin(ModelAdmin):
    list_display = get_model_fields(Favourites)
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "product__name")
    list_filter = ("created_at",)
    autocomplete_fields = ("customer", "product")
    date_hierarchy = "created_at"


class BrandProductImageFilter(admin.SimpleListFilter):
    title = "Бренд"
    parameter_name = "brand"

    def lookups(self, request, model_admin):
        return Brand.objects.filter(product_brand__isnull=False).distinct().values_list("id", "name")

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(product__brand_id=self.value())
        return queryset


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    list_display = ("id", "product", "get_brand", "created_at")
    list_display_links = ("id", "product")
    search_fields = ("product__name",)
    list_filter = (BrandProductImageFilter, "created_at")
    autocomplete_fields = ("product",)
    date_hierarchy = "created_at"

    @admin.display(description="Бренд")
    def get_brand(self, obj):
        return obj.product.brand.name if obj.product and obj.product.brand else "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product__brand")


@admin.register(AddsBrands)
class AddsBrandsAdmin(ModelAdmin):
    list_display = get_model_fields(AddsBrands)
    list_display_links = ("id", "name")
    search_fields = ("name", "brand__name", "title")
    list_filter = ("is_visible", "created_at")
    autocomplete_fields = ("products", "brand")
    date_hierarchy = "created_at"
    actions = [make_visible, make_hidden]


@admin.register(Sale)
class SaleAdmin(ModelAdmin):
    list_display = get_model_fields(Sale)
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_main", "is_visible", "discount_from", "discount_to")
    autocomplete_fields = ("products",)
    date_hierarchy = "created_at"
    actions = [make_visible, make_hidden, mark_as_main, mark_as_not_main]


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = get_model_fields(Brand) + ["product_images_count"]
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_visible", "created_at")
    date_hierarchy = "created_at"
    actions = [make_visible, make_hidden]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _product_images_count=Count("product_brand__product_image", distinct=True)
        )

    @admin.display(description="Изображений", ordering="_product_images_count")
    def product_images_count(self, obj):
        return obj._product_images_count


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = get_model_fields(Tag)
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_active", "created_at")
    date_hierarchy = "created_at"
    actions = [activate, deactivate]


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1


class ProductCharacteristicsInline(TabularInline):
    model = ProductCharacteristics
    extra = 1


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = get_model_fields(Product)
    list_display_links = ("id", "name")
    search_fields = ("name", "brand__name", "product_item_category__name")
    list_filter = ("brand", "product_item_category", "is_active", "unit", "created_at")
    readonly_fields = ("discount_price",)
    autocomplete_fields = ("brand", "product_item_category")
    inlines = (ProductImageInline, ProductCharacteristicsInline)
    fieldsets = (
        (None, {
            "fields": ("name", "short_description", "description", "price", "discount",
                       "discount_price", "quantity", "comments_quantity", "questions_quantity",
                       "rating", "is_active", "brand", "product_item_category", "unit")
        }),
        ("Данные из 1С", {
            "classes": ("collapse",),
            "fields": ("telegram_id", "articul_code", "barcode", "product_code"),
        }),
        ("Доставка", {
            "classes": ("collapse",),
            "fields": ("weight", "length", "width", "height"),
            "description": "Вес в кг, размеры в метрах. Используются для расчёта доставки Яндекс."
        }),
        ("Данные для фильтров", {
            "classes": ("collapse",),
            "fields": ("filter_data",),
            "description": "Формат: {\"ключ_фильтра\": \"значение\"}. Для checkbox/radio фильтров."
        }),
    )
    date_hierarchy = "created_at"
    list_per_page = 25
    actions = [activate, deactivate]

    def save_model(self, request, obj, form, change):
        if obj.discount:
            obj.discount_price = obj.price * (1 - (obj.discount / 100))
        obj.save()


@admin.register(ProductCategory)
class ProductCategoryAdmin(ModelAdmin):
    list_display = get_model_fields(ProductCategory)
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(ProductSubCategory)
class ProductSubCategoryAdmin(ModelAdmin):
    list_display = get_model_fields(ProductSubCategory)
    list_display_links = ("id", "name")
    search_fields = ("name", "product_category__name")
    list_filter = ("product_category", "created_at")
    autocomplete_fields = ("product_category",)
    date_hierarchy = "created_at"


@admin.register(ProductItemCategory)
class ProductItemCategoryAdmin(ModelAdmin):
    list_display = get_model_fields(ProductItemCategory)
    list_display_links = ("id", "name")
    search_fields = ("name", "product_sub_category__name")
    list_filter = ("product_sub_category", "created_at")
    autocomplete_fields = ("product_sub_category",)
    date_hierarchy = "created_at"


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = get_model_fields(Comment)
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "comment", "product__name")
    list_filter = ("product_rating", "is_visible", "created_at")
    autocomplete_fields = ("customer", "product")
    date_hierarchy = "created_at"
    actions = [make_visible, make_hidden]


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ("id", "customer", "status", "payment_status", "payment_type", "payment_method", "delivery_type", "pickup_branch", "total_price", "delivery_price", "created_at")
    list_display_links = ("id", "customer")
    search_fields = ("customer__full_name", "customer__phone_number", "id")
    list_filter = ("status", "payment_status", "payment_type", "payment_method", "delivery_type", "created_at")
    autocomplete_fields = ("customer", "promocode", "order_location", "pickup_branch")
    readonly_fields = ("delivery_price", "yandex_claim_id", "yandex_claim_status")
    date_hierarchy = "created_at"
    list_per_page = 25
    actions = [status_collecting, status_delivering, status_completed, status_canceled]


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = get_model_fields(OrderItem)
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
    list_display = get_model_fields(ProductVariantGroup)
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("display_type", "created_at")
    inlines = [ProductVariantItemInline]
    date_hierarchy = "created_at"


@admin.register(ProductVariantItem)
class ProductVariantItemAdmin(ModelAdmin):
    list_display = get_model_fields(ProductVariantItem)
    list_display_links = ("id", "display_value")
    search_fields = ("display_value", "group__name", "product__name")
    list_filter = ("group", "created_at")
    autocomplete_fields = ("group", "product")
    date_hierarchy = "created_at"
    list_per_page = 25


class ProductFilterNumericValueInline(TabularInline):
    model = ProductFilterNumericValue
    extra = 0
    autocomplete_fields = ("product",)


@admin.action(description="Lock type for selected filters")
def lock_filter_type(modeladmin, request, queryset):
    updated = queryset.update(type_locked=True)
    messages.success(request, f"{updated} filter schemas locked.")


@admin.action(description="Unlock type for selected filters")
def unlock_filter_type(modeladmin, request, queryset):
    updated = queryset.update(type_locked=False)
    messages.success(request, f"{updated} filter schemas unlocked.")


class ItemCategoryFilter(admin.SimpleListFilter):
    title = "item category"
    parameter_name = "item_category_search"
    template = "admin/input_filter.html"

    def lookups(self, request, model_admin):
        return ()

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(item_category__name__icontains=value)
        return queryset


@admin.action(description="Change type for selected filters")
def change_filter_type(modeladmin, request, queryset):
    if "apply" in request.POST:
        new_type = request.POST.get("new_type")
        if new_type not in dict(ProductItemCategoryFilterSchema._meta.get_field("type").choices):
            messages.error(request, "Invalid type selected.")
            return

        category_ids = set(queryset.values_list("item_category_id", flat=True))
        updated = queryset.update(type=new_type)
        for cat_id in category_ids:
            clear_category_filter_cache(cat_id)
        messages.success(request, f"{updated} filter schemas updated to {dict(ProductItemCategoryFilterSchema._meta.get_field('type').choices)[new_type]}.")
        return

    context = {
        **modeladmin.admin_site.each_context(request),
        "queryset": queryset,
        "opts": modeladmin.model._meta,
        "filter_types": ProductItemCategoryFilterSchema._meta.get_field("type").choices,
        "objects_name": "filter schemas",
    }
    return render(request, "admin/change_filter_type.html", context)


@admin.register(ProductItemCategoryFilterSchema)
class ProductItemCategoryFilterSchemaAdmin(ModelAdmin):
    actions = [change_filter_type, lock_filter_type, unlock_filter_type]
    list_display = get_model_fields(ProductItemCategoryFilterSchema)
    list_display_links = ("id", "key")
    search_fields = ("key", "label_ru", "item_category__name")
    list_filter = ("type", "is_filterable", "type_locked", ItemCategoryFilter)
    autocomplete_fields = ("item_category",)
    inlines = [ProductFilterNumericValueInline]


@admin.register(ProductFilterNumericValue)
class ProductFilterNumericValueAdmin(ModelAdmin):
    list_display = get_model_fields(ProductFilterNumericValue)
    list_display_links = ("id", "product")
    search_fields = ("product__name", "schema__key")
    list_filter = ("schema__item_category",)
    autocomplete_fields = ("product", "schema")


@admin.register(Announcements)
class AnnouncementsAdmin(ModelAdmin):
    list_display = get_model_fields(Announcements)
    list_display_links = ("id", "title")
    search_fields = ("title", "description")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(ProductUnit)
class ProductUnitAdmin(ModelAdmin):
    list_display = get_model_fields(ProductUnit)
    list_display_links = ("id", "name")
    search_fields = ("name",)
    list_filter = ("is_active",)
    actions = [activate, deactivate]


@admin.register(ProductRemaining)
class ProductRemainingAdmin(ModelAdmin):
    list_display = get_model_fields(ProductRemaining)
    list_display_links = ("id", "product")
    search_fields = ("branch__name", "branch__code", "product__name", "product__product_code")
    list_filter = ("branch", "created_at")
    autocomplete_fields = ("branch", "product")
    date_hierarchy = "created_at"
    list_per_page = 25
