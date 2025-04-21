from rest_framework import serializers

from authorization.serializers import CustomerSerializer
from .models import Product, ProductCategory, ProductItemCategory, ProductSubCategory, ProductImage, Comment, \
    Order, OrderItem, Brand, Sale, AddsBrands, Favourites, Cart, CartItem, ProductCharacteristics, Questions
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from config import settings
from django.db.models import Exists, OuterRef


class ProductCharacteristicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCharacteristics
        fields = (
            "id",
            "name",
            "unit",
            "value"
        )


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
        product = Product.objects.filter(id=attrs.get("product").id).first()
        if product.quantity == 0:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not exist in warehouse")
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
        product = Product.objects.filter(id=attrs.get("product").id).first()
        if product.quantity == 0:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not exist in warehouse")
        return attrs


class CartItemBulkUpdateSerializer(serializers.Serializer):
    is_checked = serializers.BooleanField()


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


class SearchByNameSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)


class AddsBrandsDetailSerializer(serializers.ModelSerializer):
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

    def validate(self, attrs):
        price_from = attrs.get("price_from")
        price_to = attrs.get("price_to")
        if price_from and price_to and price_from > price_to:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT,
                                     message="Price_from could not be more than price_to")
        return attrs


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = (
            "id",
            "name",
            "image"
        )


class CommentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "customer",
            "product",
            "product_rating",
            "comment",
            "created_at"
        )


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = (
            "id",
            "customer",
            "product",
            "product_rating",
            "comment",
            "created_at"
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


class ProductSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        language = 'ru'
        if request and request.META.get('HTTP_ACCEPT_LANGUAGE') in settings.MODELTRANSLATION_LANGUAGES:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        self.fields["name"] = serializers.CharField(source=f'name_{language}')
        self.fields["description"] = serializers.CharField(source=f'description_{language}')

    images = ProductImageSerializer(source="product_image", many=True, read_only=True)
    in_cart = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    characteristics = ProductCharacteristicsSerializer(source="product_characteristics", many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "product_item_category",
            "name",
            "is_favourite",
            "in_cart",
            "description",
            "price",
            "quantity",
            "rating",
            "discount",
            "discount_price",
            "comments_quantity",
            "characteristics",
            "images",
        )

    def get_in_cart(self, obj):
        print("Working")
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
        print(attrs)
        product = Product.objects.filter(id=attrs.get("product").id).first()
        if product.quantity == 0:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Product is not exist in warehouse")
        return attrs


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(source="cart_item", many=True, read_only=True)

    class Meta:
        model = Cart
        fields = (
            "id",
            "customer",
            "cart_token",
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


class AddsBrandsSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = AddsBrands
        fields = (
            "id",
            "name",
            "brand",
            "products"
        )

    def get_products(self, obj):
        request = self.context.get("request")
        if not request:
            return []

        customer_id = getattr(request.user, "id", None)
        token = request.COOKIES.get("cart_token")

        products_qs = Product.objects.filter(brand_id=obj.brand.id).order_by("id")
        print(products_qs)

        if customer_id:
            cart_filter = CartItem.objects.filter(
                cart__customer_id=customer_id,
                product=OuterRef("pk")
            )
        else:
            cart_filter = CartItem.objects.filter(
                cart__cart_token=token,
                product=OuterRef("pk")
            )

        products_qs = products_qs.annotate(
            in_cart=Exists(cart_filter)
        )

        return ProductSerializer(products_qs, many=True, context={"request": request}).data


class SaleSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id",
            "name",
            "discount_from",
            "discount_to",
            "is_main",
            "products"
        )


class BrandDetailSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        fields = (
            "id",
            "name",
            "image",
            "products_count"
        )


class ProductItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductItemCategory
        fields = (
            "id",
            "name",
            "image"
        )


class ProductSubCategorySerializer(serializers.ModelSerializer):
    product_item_categories = ProductItemCategorySerializer(source="product_sub_category", many=True, read_only=True)

    class Meta:
        model = ProductSubCategory
        fields = (
            "id",
            "name",
            "image",
            "product_item_categories"
        )


class ProductCategorySerializer(serializers.ModelSerializer):
    sub_categories = ProductSubCategorySerializer(source="product_category", many=True, read_only=True)

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name",
            "image",
            "sub_categories"
        )


class ProductCategoryListSerializer(serializers.ModelSerializer):
    sub_categories = ProductSubCategorySerializer(source="product_category", many=True, read_only=True)

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "name",
            "icon",
            "image",
            "sub_categories"
        )


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "id",
            "customer",
            "status",
            "total_price"
        )


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "order",
            "product",
            "quantity"
        )


class QuestionsSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = Questions
        fields = (
            "id",
            "customer",
            "product",
            "question",
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
