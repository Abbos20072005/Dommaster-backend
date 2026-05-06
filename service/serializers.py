from rest_framework import serializers
from authorization.serializers import CustomerSerializer, CustomerAddressesSerializer
from .models import Product, ProductCategory, ProductItemCategory, ProductSubCategory, ProductImage, Comment, \
    Order, OrderItem, Brand, Sale, AddsBrands, Favourites, Cart, CartItem, ProductCharacteristics, Questions, \
    RecentlyViewedProducts, Service, CommentReply, CommentImages, QuestionsReply, CategoryAttribute, \
    CategoryAttributeValue, ProductAttributeValue
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from config import settings
from base.serializers import PromocodeSerializer


class TranslatedSerializerMixin:
    """Mixin to resolve the current language from the request Accept-Language header."""
    def get_language(self):
        request = self.context.get('request')
        lang = request.META.get('HTTP_ACCEPT_LANGUAGE', 'ru') if request else 'ru'
        return lang if lang in settings.MODELTRANSLATION_LANGUAGES else 'ru'


class ProductAnnotationMixin:
    """
    Mixin for product serializers that reads annotation-based fields
    (_is_in_cart, _is_favourite, _cart_quantity) set at the queryset level
    in views, eliminating N+1 queries. Falls back to per-object DB queries
    if annotations are not present (e.g. single-object detail views).
    """
    def get_in_cart(self, obj):
        if hasattr(obj, '_is_in_cart'):
            return obj._is_in_cart
        # Fallback for non-annotated querysets
        request = self.context.get("request")
        if not request:
            return False
        customer = getattr(request.user, 'id', None)
        token = request.COOKIES.get("cart_token")
        if customer:
            return CartItem.objects.filter(cart__customer_id=customer, product=obj).exists()
        elif token:
            return CartItem.objects.filter(cart__cart_token=token, product=obj).exists()
        return False

    def get_is_favourite(self, obj):
        if hasattr(obj, '_is_favourite'):
            return obj._is_favourite
        request = self.context.get("request")
        if not request:
            return False
        customer = getattr(request.user, 'id', None)
        fav_token = request.COOKIES.get("favourite_token")
        if customer:
            return Favourites.objects.filter(customer_id=customer, product=obj).exists()
        elif fav_token:
            return Favourites.objects.filter(favourite_token=fav_token, product=obj).exists()
        return False

    def get_in_cart_quantity(self, obj):
        if hasattr(obj, '_cart_quantity'):
            return obj._cart_quantity or 0
        request = self.context.get("request")
        if not request:
            return 0
        customer = getattr(request.user, 'id', None)
        token = request.COOKIES.get("cart_token")
        if customer:
            cart_item = CartItem.objects.filter(cart__customer_id=customer, product_id=obj.id).first()
            return cart_item.quantity if cart_item else 0
        elif token:
            cart_item = CartItem.objects.filter(cart__cart_token=token, product_id=obj.id).first()
            return cart_item.quantity if cart_item else 0
        return 0

class OrderCreateSerializer(serializers.Serializer):
    promocode = serializers.CharField(max_length=15, required=False)
    payment_type = serializers.IntegerField(required=True)
    is_web = serializers.BooleanField(required=False)
    address_id = serializers.IntegerField(required=False)

class OrderCancelSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=True)

class OrderPaySerializer(serializers.Serializer):
    payment_type = serializers.IntegerField(required=True)
    is_web = serializers.BooleanField(required=False)
    order_id = serializers.IntegerField(required=True)

class QuestionsReplySerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = QuestionsReply
        fields = (
            "id",
            "customer",
            "created_at",
            "answer",
            "is_admin"
        )

class QuestionsReplyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionsReply
        fields = (
            "id",
            "customer",
            "question",
            "answer"
        )

class QuestionsReplyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionsReply
        fields = (
            "id",
            "answer"
        )

class CommentImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentImages
        fields = (
            "id",
            "image"
        )

class CommentImagesCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentImages
        fields = (
            "id",
            "customer",
            "comment",
            "image"
        )

class CommentReplySerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = CommentReply
        fields = (
            "id",
            "customer",
            "is_admin",
            "reply_comment",
            "created_at"
        )


class CommentReplyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentReply
        fields = (
            "id",
            "customer",
            "comment",
            "reply_comment"
        )

class CommentReplyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentReply
        fields = (
            "id",
            "reply_comment"
        )

class ServiceSerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')

    class Meta:
        model = Service
        fields = (
            "id",
            "name",
            "icon"
        )

class ServiceDetailSerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')
        self.fields["description"] = serializers.CharField(source=f'description_{language}')

    class Meta:
        model = Service
        fields = (
            "id",
            "name",
            "icon",
            "description"
        )

class ProductCharacteristicsSerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')
        self.fields["unit"] = serializers.CharField(source=f'unit_{language}')
        self.fields["value"] = serializers.CharField(source=f'value_{language}')


    class Meta:
        model = ProductCharacteristics
        fields = (
            "id",
            "name",
            "unit",
            "value"
        )

class ProductCharacteristicsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCharacteristics
        fields = (
            "id",
            "product",
            "name",
            "name_uz",
            "name_en",
            "unit",
            "value",
            "value_uz",
            "value_en"
        )


class CategoryAttributeValueSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    value = serializers.CharField()
    product_count = serializers.IntegerField(read_only=True, default=0)


class CategoryAttributeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    is_filterable = serializers.BooleanField()
    position = serializers.IntegerField()
    values = CategoryAttributeValueSerializer(source="attribute_values", many=True, read_only=True)


class ProductAttributeValueSerializer(TranslatedSerializerMixin, serializers.Serializer):
    attribute = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    attribute_id = serializers.IntegerField(source="attribute.id", read_only=True)
    value_id = serializers.IntegerField(source="attribute_value.id", read_only=True)

    def get_attribute(self, obj):
        language = self.get_language()
        return getattr(obj.attribute, f'name_{language}')

    def get_value(self, obj):
        language = self.get_language()
        return getattr(obj.attribute_value, f'value_{language}')


class CartItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = (
            "id",
            "cart",
            "product",
            "quantity",
            "is_checked"
        )

    def validate(self, attrs):
        product = Product.objects.filter(id=attrs.get("product").id, is_active=True).first()
        if not product:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not available")
        if product.quantity == 0:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not exist in warehouse")
        elif product and attrs.get("quantity") and product.quantity < attrs.get("quantity"):
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT,
                                     message="We don't have enough product in warehouse")
        return attrs


class CartItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "quantity",
            "is_checked"
        )

    def validate(self, attrs):
        product = Product.objects.filter(id=attrs.get("product").id, is_active=True).first()
        if not product:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not available")
        if product and product.quantity == 0:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not exist in warehouse")
        elif product and attrs.get("quantity") and product.quantity < attrs.get("quantity"):
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT,
                                     message="We don't have enough product in warehouse")
        return attrs


class CartItemBulkUpdateSerializer(serializers.Serializer):
    is_checked = serializers.BooleanField(required=False)
    is_delete = serializers.BooleanField(required=False)


class FavouriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favourites
        fields = (
            "id",
            "customer",
            "favourite_token",
            "product",
        )


class FavouriteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favourites
        fields = (
            "id",
            "product"
        )
        
    def validate(self, attrs):
        product = attrs.get("product")
        if not product or not product.is_active:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not available")
        return attrs


class SearchByNameSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)


class AddsBrandsDetailSerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["title"] = serializers.CharField(source=f'title_{language}')
        self.fields["description"] = serializers.CharField(source=f'description_{language}')

    class Meta:
        model = AddsBrands
        fields = (
            "id",
            "title",
            "description"
        )


class PaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField(
        required=False,
        default=1
    )
    page_size = serializers.IntegerField(
        required=False,
        default=10
    )

    def validate(self, attrs):
        page = attrs.get('page')
        page_size = attrs.get('page_size')
        if page < 0 or page_size < 0:
            raise CustomApiException(ErrorCodes.INVALID_INPUT, message="page or page_size is invalid")
        return super().validate(attrs)


class CommentParamSerializer(serializers.Serializer):
    page = serializers.IntegerField(
        required=False,
        default=1
    )
    page_size = serializers.IntegerField(
        required=False,
        default=10
    )
    product_id = serializers.IntegerField(
        required=True
    )

    def validate(self, attrs):
        page = attrs.get('page')
        page_size = attrs.get('page_size')
        if page < 0 or page_size < 0:
            raise CustomApiException(ErrorCodes.INVALID_INPUT, message="page or page_size is invalid")
        return super().validate(attrs)


class FilterSerializer(PaginationSerializer):
    q = serializers.CharField(required=False)
    sort_by = serializers.CharField(required=False)
    price_from = serializers.FloatField(required=False)
    price_to = serializers.FloatField(required=False)
    brand = serializers.IntegerField(required=False)
    item_category = serializers.IntegerField(required=False)
    sale_id = serializers.IntegerField(required=False)
    attributes = serializers.DictField(required=False, child=serializers.ListField(child=serializers.IntegerField()))

    def validate(self, attrs):
        price_from = attrs.get("price_from")
        price_to = attrs.get("price_to")
        if price_from and price_to and price_from > price_to:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT,
                                     message="Price_from could not be more than price_to")
        return attrs


class BrandSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    image = serializers.ImageField()

class BrandByItemCategoriesSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

class CommentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    images = CommentImagesSerializer(source="comment_image", many=True, read_only=True)
    reply_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "customer",
            "product",
            "product_rating",
            "comment",
            "created_at",
            "reply_count",
            "images"
        )


class CommentCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)

    class Meta:
        model = Comment
        fields = (
            "id",
            "customer",
            "product",
            "product_rating",
            "comment",
            "created_at",
            "images"
        )


class CommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            "id",
            "product_rating",
            "comment"
        )


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "product", "image")

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "id",
            "product_item_category",
            "brand",
            "name",
            "name_uz",
            "name_en",
            "description",
            "description_uz",
            "description_en",
            "price",
            "unit",
            "quantity"
        )

class ProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "id",
            "name_ru"
        )

class ProductDetailSerializer(ProductAnnotationMixin, serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    is_favourite = serializers.SerializerMethodField()
    rating = serializers.FloatField()
    price = serializers.FloatField()
    unit = serializers.CharField()
    quantity = serializers.IntegerField()
    in_cart = serializers.SerializerMethodField()
    in_cart_quantity = serializers.SerializerMethodField()
    discount = serializers.IntegerField()
    discount_price = serializers.FloatField()
    breadcrumbs = serializers.SerializerMethodField()
    comments_quantity = serializers.IntegerField()
    questions_quantity = serializers.IntegerField()
    characteristics = ProductCharacteristicsSerializer(source="product_characteristics", many=True, read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)
    brand = BrandSerializer(read_only=True)

    def get_breadcrumbs(self, obj):
        return obj.get_breadcrumbs()


class ProductSerializer(ProductAnnotationMixin, TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')
        self.fields["description"] = serializers.CharField(source=f'description_{language}')

    images = ProductImageSerializer(source="product_image", many=True, read_only=True)
    in_cart = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    in_cart_quantity = serializers.SerializerMethodField()
    breadcrumbs = serializers.SerializerMethodField()
    characteristics = ProductCharacteristicsSerializer(source="product_characteristics", many=True, read_only=True)
    attributes = ProductAttributeValueSerializer(source="product_attribute_values", many=True, read_only=True)
    brand = BrandSerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "product_item_category",
            "brand",
            "name",
            "is_favourite",
            "in_cart",
            "in_cart_quantity",
            "short_description",
            "description",
            "price",
            "unit",
            "quantity",
            "rating",
            "discount",
            "discount_price",
            "comments_quantity",
            "questions_quantity",
            "characteristics",
            "attributes",
            "breadcrumbs",
            "images",
        )

    def get_breadcrumbs(self, obj):
        return obj.get_breadcrumbs()

class ProductShortSerializer(ProductAnnotationMixin, serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    is_favourite = serializers.SerializerMethodField()
    rating = serializers.FloatField()
    price = serializers.FloatField()
    unit = serializers.CharField()
    quantity = serializers.IntegerField()
    in_cart = serializers.SerializerMethodField()
    in_cart_quantity = serializers.SerializerMethodField()
    discount = serializers.IntegerField()
    discount_price = serializers.FloatField()
    brand = BrandSerializer(read_only=True)
    images = ProductImageSerializer(source="product_image", many=True, read_only=True)

class RecentlyViewedProductsSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = RecentlyViewedProducts
        fields = (
            "id",
            # "customer",
            "product",
            "created_at"
        )


class FavouriteResponseSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Favourites
        fields = (
            "id",
            "customer",
            "favourite_token",
            "product",
        )


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = (
            "id",
            "cart",
            "product",
            "quantity",
            "is_checked"
        )

    def validate(self, attrs):
        product = Product.objects.filter(id=attrs.get("product").id, is_active=True).first()
        if not product:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not available")
        if product.quantity == 0:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not exist in warehouse")
        elif product and attrs.get("quantity") and product.quantity < attrs.get("quantity"):
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT,
                                     message="We don't have enough product in warehouse")
        return attrs


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(source="cart_item", many=True, read_only=True)

    class Meta:
        model = Cart
        fields = (
            "id",
            "customer",
            "cart_token",
            "total_price",
            "saved_price",
            "products_total_price",
            "cart_items"
        )


class FavouriteListSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Favourites
        fields = (
            "id",
            "customer",
            "product",
        )


class AddsBrandsSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    brand = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    def get_brand(self, obj):
        return obj.brand.id if obj.brand else None

    def get_products(self, obj):
        qs = obj.products.filter(is_active=True)
        return ProductShortSerializer(qs, many=True, context=self.context).data


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = (
            "id",
            "name",
            "discount_from",
            "discount_to",
            "image"
        )

class SaleMainSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    def get_products(self, obj):
        qs = obj.products.filter(is_active=True)
        return ProductSerializer(qs, many=True, context=self.context).data

    class Meta:
        model = Sale
        fields = (
            "id",
            "name",
            "discount_from",
            "discount_to",
            "bg_image",
            "products"
        )


class BrandDetailSerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')

    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        fields = (
            "id",
            "name",
            "image",
            "products_count"
        )


class ProductItemCategoryFilterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    image = serializers.ImageField()

class ProductSubCategoryFilterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    product_item_categories = serializers.SerializerMethodField()

    def get_product_item_categories(self, obj):
        qs = obj.product_sub_category.filter(product_item_category__id__isnull=False).distinct()
        return ProductItemCategoryFilterSerializer(qs, many=True, context=self.context).data

class ProductCategoryFilterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    sub_categories = serializers.SerializerMethodField()

    def get_sub_categories(self, obj):
        qs = obj.product_category.filter(product_sub_category__product_item_category__id__isnull=False).distinct()
        return ProductSubCategoryFilterSerializer(qs, many=True, context=self.context).data

class ProductItemCategorySerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')

    breadcrumbs = serializers.SerializerMethodField()
    product_amount = serializers.SerializerMethodField()

    class Meta:
        model = ProductItemCategory
        fields = (
            "id",
            "name",
            "image",
            "product_amount",
            "breadcrumbs"
        )

    def get_product_amount(self, obj):
        return obj.product_item_category.count()

    def get_breadcrumbs(self, obj):
        return obj.get_breadcrumbs()


class ProductSubCategorySerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')

    product_item_categories = ProductItemCategorySerializer(source="product_sub_category", many=True, read_only=True)
    breadcrumbs = serializers.SerializerMethodField()

    class Meta:
        model = ProductSubCategory
        fields = (
            "id",
            "name",
            "image",
            "breadcrumbs",
            "product_item_categories"
        )

    def get_breadcrumbs(self, obj):
        return obj.get_breadcrumbs()

class ProductCategorySearchSerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name",
            "image"
        )

class ProductCategorySerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = self.get_language()
        self.fields["name"] = serializers.CharField(source=f'name_{language}')

    sub_categories = ProductSubCategorySerializer(source="product_category", many=True, read_only=True)
    breadcrumbs = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name",
            "image",
            "icon",
            "breadcrumbs",
            "sub_categories"
        )

    def get_breadcrumbs(self, obj):
        return obj.get_breadcrumbs()
    
class ProductItemCategoryTreeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    
class ProductSubCategoryTreeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    image = serializers.ImageField()
    product_item_categories = serializers.SerializerMethodField()

    def get_product_item_categories(self, obj):
        qs = obj.product_sub_category.all()
        return ProductItemCategoryFilterSerializer(qs, many=True, context=self.context).data
    

class ProducgtCategoryTreeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    image = serializers.ImageField()
    icon = serializers.ImageField()
    sub_categories = serializers.SerializerMethodField()

    def get_sub_categories(self, obj):
        qs = obj.product_category.all()
        return ProductSubCategoryTreeSerializer(qs, many=True, context=self.context).data



class ProductCategoryListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    icon = serializers.ImageField()
    image = serializers.ImageField()

class ProductSubCategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSubCategory
        fields = (
            "id",
            "product_category",
            "name",
            "image"
        )

class ProductItemCategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductItemCategory
        fields = (
            "id",
            "product_sub_category",
            "name",
            "name_uz",
            "name_en",
            "image"
        )


class OrderItemImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "image",
        )

    def get_image(self, obj):
        request = self.context.get("request")
        first_image = obj.product.product_image.first()
        if first_image:
            return request.build_absolute_uri(first_image.image.url)
        return None

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemImageSerializer(many=True, read_only=True)
    order_location = CustomerAddressesSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "customer",
            "status",
            "total_price",
            "order_location",
            "created_at",
            "order_items"
        )

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "quantity",
            "product"
        )


class OrderDetailSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    order_location = CustomerAddressesSerializer(read_only=True)
    promocode = PromocodeSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "promocode",
            "total_price",
            "order_location",
            "ofd_url",
            "created_at",
            "order_items"
        )


class QuestionsSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    reply_count = serializers.IntegerField(read_only=True)


    class Meta:
        model = Questions
        fields = (
            "id",
            "customer",
            "product",
            "question",
            "reply_count",
            "created_at"
        )


class QuestionsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Questions
        fields = (
            "id",
            "customer",
            "product",
            "question"
        )


class QuestionsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Questions
        fields = (
            "id",
            "question"
        )
