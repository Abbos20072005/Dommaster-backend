from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from authorization.models import Customer
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .serializers import ProductCategorySerializer, ProductCategoryListSerializer, ProductSubCategorySerializer, \
    ProductItemCategorySerializer, ProductSerializer, CommentSerializer, BrandSerializer, FilterSerializer, \
    PaginationSerializer, BrandDetailSerializer, SaleSerializer, AddsBrandsSerializer, AddsBrandsDetailSerializer, \
    SearchByNameSerializer, CommentUpdateSerializer, FavouriteSerializer, FavouriteListSerializer, CartSerializer, \
    CartItemSerializer, CartItemUpdateSerializer, CartItemBulkUpdateSerializer, CommentParamSerializer, \
    CommentCreateSerializer, CartItemCreateSerializer, QuestionsSerializer, QuestionsUpdateSerializer, \
    QuestionsCreateSerializer, FavouriteCreateSerializer, FavouriteResponseSerializer
from .models import ProductCategory, ProductSubCategory, ProductItemCategory, Product, Comment, Brand, Sale, AddsBrands, \
    Favourites, Cart, CartItem, Questions, Order, OrderItem
from rest_framework import status
from django.db.models import Q, Sum, Exists, OuterRef, Value, BooleanField
from .paginations.get_products_pagination import get_products_paginator
from .paginations.get_comments import get_comments_paginator
from .paginations.get_question import get_questions_paginator
from django.db.models import Count
from django.core.cache import cache
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Greatest
import secrets
from django.db import transaction


# TODO: in cart product quantity

# TODO: need to do sale function
class ProductViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Search products by name",
        operation_description="Search products by name",
        manual_parameters=[
            openapi.Parameter(name="q", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Search param")
        ],
        responses={200: SearchByNameSerializer(many=True)},
        tags=["Product"]
    )
    def search_by_name(self, request):
        param = request.query_params.get("q")
        if not param:
            return Response(data={"result": [], "ok": True}, status=status.HTTP_200_OK)

        param_data = param.strip().lower()
        cache_key = f"{param_data}"

        query = cache.get(cache_key)
        if not query:
            product = Product.objects.annotate(
                similarity=Greatest(
                    TrigramSimilarity("name", param_data),
                    TrigramSimilarity("name_uz", param_data),
                    TrigramSimilarity("name_ru", param_data),
                    TrigramSimilarity("name_en", param_data)
                )
            ).filter(similarity__gt=0.1).order_by('-similarity').values_list("name", flat=True)
            cache.set(cache_key, product, timeout=300)

        return Response(data={"result": cache.get(cache_key), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Most sold products",
        operation_description="Most sold products",
        responses={200: ProductSerializer(many=True)},
        tags=["Product"]
    )
    def most_sold(self, request):
        products = Product.objects.annotate(most_solds=Sum("product_order_item__quantity")).order_by("-most_solds")[:20]
        serializer = ProductSerializer(products, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product categories list",
        operation_description="Product categories list",
        responses={200: ProductCategoryListSerializer(many=True)},
        tags=["Product"]
    )
    def categories_list(self, request):
        category = ProductCategory.objects.all()
        serializer = ProductCategoryListSerializer(category, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product category detail and sub categories list",
        operation_description="Product category detail and sub categories list",
        responses={200: ProductCategorySerializer()},
        tags=["Product"]
    )
    def sub_category_list(self, request, pk):
        category = ProductCategory.objects.filter(id=pk).first()
        if not category:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ProductCategorySerializer(category, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product sub category detail and item category list",
        operation_description="Product sub category detail and item category list",
        responses={200: ProductSubCategorySerializer()},
        tags=["Product"]
    )
    def item_category_list(self, request, pk):
        sub_category = ProductSubCategory.objects.filter(id=pk).first()
        if not sub_category:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ProductSubCategorySerializer(sub_category, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="",
        operation_description="",
        responses={200: ProductItemCategorySerializer()},
        tags=["Product"]
    )
    def item_category_detail(self, request, pk):
        item_category = ProductItemCategory.objects.filter(id=pk).first()
        if not item_category:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = ProductItemCategorySerializer(item_category, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Product detail",
        operation_description="Product detail",
        responses={200: ProductSerializer()},
        tags=["Product"]
    )
    def product_detail(self, request, pk):
        products = Product.objects.filter(id=pk).first()
        serializer = ProductSerializer(products, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Products filter",
        operation_description="Products filter",
        request_body=FilterSerializer(),
        responses={200: FilterSerializer(many=True)},
        tags=["Product"]
    )
    def product_filter(self, request):
        data = request.data
        serializer = FilterSerializer(data=data)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        page = serializer.validated_data.get("page")
        page_size = serializer.validated_data.get("page_size")
        q = serializer.validated_data.get("q")
        price_from = serializer.validated_data.get("price_from", 0)
        price_to = serializer.validated_data.get("price_to", 0)
        sort_by = serializer.validated_data.get("sort_by")
        brand = serializer.validated_data.get("brand")
        item_category = serializer.validated_data.get("item_category")

        filters = Q()
        if q:
            filters &= Q(name__icontains=q) | Q(name_uz__icontains=q) | Q(name_ru__icontains=q) | Q(
                name_en__icontains=q)

        sort = "created_at"
        if sort_by:
            sort = {
                "newest": "-created_at",
                "price": "price",
                "rating": "-rating"
            }.get(sort_by, "created_at")

        if price_from or price_to:
            filters &= Q(price__gte=price_from)
            filters &= Q(price__lte=price_to)

        if brand:
            filters &= Q(brand=brand)

        if item_category:
            filters &= Q(product_item_category=item_category)

        products = Product.objects.filter(filters).order_by(sort)
        return Response(data={"result": get_products_paginator(response_data=products, page=page, page_size=page_size,
                                                               context={"request": request}), "ok": True},
                        status=status.HTTP_200_OK)


class CommentViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Get product comments",
        operation_description="Get product comments",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='product_id', in_=openapi.IN_QUERY, description='Product id', type=openapi.TYPE_INTEGER),
        ],
        responses={200: CommentSerializer(many=True)},
        tags=["Comment"]
    )
    def product_comments(self, request):
        params = request.query_params
        param_serializer = CommentParamSerializer(data=params)
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        comments = Comment.objects.filter(product=param_serializer.validated_data.get("product_id"))
        return Response(data={
            "result": get_comments_paginator(response_data=comments, page=param_serializer.validated_data.get("page"),
                                             page_size=param_serializer.validated_data.get("page_size"),
                                             context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Write comment to product, pk receive product id",
        operation_description="Write comment to product, pk receive product id",
        manual_parameters=[
            openapi.Parameter(name="product_id", in_=openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                              description="Product id")
        ],
        request_body=CommentCreateSerializer(),
        responses={201: CommentCreateSerializer()},
        tags=["Comment"]
    )
    def comment_create(self, request):
        param = request.query_params
        product = Product.objects.filter(id=param.get("product_id")).first()
        if not product:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        comment = Comment.objects.filter(customer_id=request.user.id, product_id=product.id).first()
        if comment:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="Your comment already exist")

        data = request.data
        data["customer"] = request.user.id
        data["product"] = param.get("product_id")
        serializer = CommentCreateSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Comment update",
        operation_description="Comment update",
        request_body=CommentUpdateSerializer(),
        responses={200: CommentSerializer()},
        tags=["Comment"]
    )
    def comment_update(self, request, pk):
        comment = Comment.objects.filter(id=pk).first()
        if not comment:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        if comment.customer.id != request.user.id:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="You could not update this comment")

        serializer = CommentUpdateSerializer(comment, data=request.data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Comment delete",
        operation_description="Comment delete",
        responses={204: "Your comment successfully deleted"},
        tags=["Comment"]
    )
    def comment_delete(self, request, pk):
        comment = Comment.objects.filter(id=pk).first()
        if not comment:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        if comment.customer.id != request.user.id:
            raise CustomApiException(error_code=ErrorCodes.INVALID_INPUT, message="You could not delete the comment")

        comment.delete()
        return Response(data={"result": "Your comment successfully deleted", "ok": True},
                        status=status.HTTP_204_NO_CONTENT)


class BrandViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Brands list",
        operation_description="Brands list",
        responses={200: BrandSerializer(many=True)},
        tags=["Brand"]
    )
    def brand_list(self, request):
        brands = Brand.objects.filter(is_visible=True)
        serializer = BrandSerializer(brands, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Brand detail",
        operation_description="Brand detail",
        responses={200: BrandDetailSerializer()},
        tags=["Brand"]
    )
    def brand_detail(self, request, pk):
        brand = Brand.objects.annotate(products_count=Count("product_brand")).filter(id=pk).first()
        if not brand:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = BrandDetailSerializer(brand, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class SaleViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Sale products list",
        operation_description="Sale products list",
        responses={200: SaleSerializer(many=True)},
        tags=["Sale"]
    )
    def sale_products(self, request):
        sale = Sale.objects.filter(is_visible=True).prefetch_related("products")
        serializer = SaleSerializer(sale, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class AddsBrandsViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Adds brands list",
        operation_description="Adds brands list",
        responses={200: AddsBrandsSerializer(many=True)},
        tags=["AddsBrands"]
    )
    def adds_brands(self, request):
        adds_brands = AddsBrands.objects.filter(is_visible=True).prefetch_related("products")
        serializer = AddsBrandsSerializer(adds_brands, many=True, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Adds brands detail, pk receive adds brands id",
        operation_description="Adds brands detail, pk receive adds brands id",
        responses={200: AddsBrandsDetailSerializer()},
        tags=["AddsBrands"]
    )
    def adds_brands_detail(self, request, pk):
        adds_brands = AddsBrands.objects.filter(id=pk).first()
        serializer = AddsBrandsDetailSerializer(adds_brands, context={"request": request})
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)


class FavouriteViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Create favourite product or delete it from favourite",
        operation_description="Create favourite product or delete it from favourite",
        request_body=FavouriteCreateSerializer(),
        responses={201: FavouriteSerializer(), 204: "Product successfully removed from favourite"},
        tags=["Favourite"]
    )
    def create_favourite(self, request):
        data = request.data
        customer = request.user.id

        data_serializer = FavouriteCreateSerializer(data=data, context={"request": request})
        if not data_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=data_serializer.errors)

        if not customer:
            token = request.COOKIES.get("favourite_token")
            if not token:
                token = secrets.token_hex(16)

            favourite = Favourites.objects.filter(favourite_token=token,
                                                  product_id=data_serializer.validated_data.get("product")).first()
            if favourite:
                favourite.delete()
                return Response(data={"result": "Product successfully removed from favourite", "ok": True},
                                status=status.HTTP_204_NO_CONTENT)

            data["favourite_token"] = token
            favourite_serializer = FavouriteSerializer(data=data, context={"request": request})
            if not favourite_serializer.is_valid():
                raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=favourite_serializer.errors)

            favourite_serializer.save()
            resp = Response(data={"result": favourite_serializer.data, "ok": True}, status=status.HTTP_200_OK)
            resp.set_cookie("favourite_token", favourite_serializer.validated_data.get("favourite_token"),
                            httponly=False,
                            secure=True, samesite="Lax")

            return resp

        favourite = Favourites.objects.filter(customer_id=customer,
                                              product_id=data_serializer.validated_data.get("product")).first()
        if favourite:
            favourite.delete()
            return Response(data={"result": "Product successfully removed from favourite", "ok": True},
                            status=status.HTTP_204_NO_CONTENT)

        data["customer"] = customer
        serializer = FavouriteSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Favourite products list",
        operation_description="Favourite products list",
        responses={200: FavouriteListSerializer(many=True)},
        tags=["Favourite"]
    )
    def favourite_list(self, request):
        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("favourite_token")
            if not token:
                token = secrets.token_hex(16)

            favourite = Favourites.objects.filter(favourite_token=token)
            serializer = FavouriteResponseSerializer(favourite, many=True, context={"request": request})

            resp = Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)
            resp.set_cookie("favourite_token", token,
                            httponly=False,
                            secure=True, samesite="Lax")

            return resp

        token = request.COOKIES.get("favourite_token")
        guest_favourite = None
        if token:
            guest_favourite = Favourites.objects.filter(favourite_token=token, customer__isnull=True)

        if guest_favourite:
            with transaction.atomic():
                for item in guest_favourite.all():
                    favourite_item = Favourites.objects.filter(customer_id=customer, product=item.product).first()

                    if not favourite_item:
                        Favourites.objects.create(customer_id=customer, product=item.product)
                        item.delete()
        favourites = Favourites.objects.filter(customer_id=customer)
        resp = Response(
            data={"result": FavouriteResponseSerializer(favourites, many=True, context={"request": request}).data,
                  "ok": True},
            status=status.HTTP_200_OK)

        resp.delete_cookie("cart_token")
        return resp


class CartViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Get cart",
        operation_description="Get cart",
        responses={200: CartSerializer(many=True)},
        tags=["Cart"]
    )
    def get_cart(self, request):
        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("cart_token")
            if not token:
                token = secrets.token_hex(16)

            cart = Cart.objects.filter(cart_token=token).first()
            if not cart:
                cart = Cart.objects.create(cart_token=token)

            resp = Response(data={"result": CartSerializer(cart, context={"request": request}).data, "ok": True},
                            status=status.HTTP_200_OK)

            resp.set_cookie("cart_token", cart.cart_token, httponly=False,
                            secure=True, samesite="Lax")

            return resp

        cart = Cart.objects.filter(customer_id=customer).first()
        if not cart:
            cart = Cart.objects.create(customer_id=customer)

        token = request.COOKIES.get("cart_token")
        guest_cart = None
        if token:
            guest_cart = Cart.objects.filter(cart_token=token, customer__isnull=True).first()

        if guest_cart:
            with transaction.atomic():
                for item in guest_cart.cart_item.all():
                    cart_item = CartItem.objects.filter(cart_id=cart.id, product=item.product).first()

                    if not cart_item:
                        CartItem.objects.create(cart_id=cart.id, product=item.product,
                                                quantity=item.quantity)
                        item.delete()
                        continue

                    cart_item.quantity += item.quantity
                    cart_item.save(update_fields=["quantity"])
                    item.delete()

                guest_cart.delete()

        resp = Response(data={"result": CartSerializer(cart, context={"request": request}).data, "ok": True},
                        status=status.HTTP_200_OK)

        resp.delete_cookie("cart_token")
        return resp

    @swagger_auto_schema(
        operation_summary="Create cart item",
        operation_description="Create cart item",
        request_body=CartItemCreateSerializer(),
        responses={200: CartSerializer()},
        tags=["Cart"]
    )
    def create_cart_item(self, request):
        data = request.data
        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("cart_token")
            cart = Cart.objects.filter(cart_token=token).first()
        else:
            cart = Cart.objects.filter(customer=customer).first()

        data["cart"] = cart.id
        serializer = CartItemCreateSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update cart item",
        operation_description="Update cart item",
        request_body=CartItemUpdateSerializer(),
        responses={202: CartItemSerializer(), 204: "Product successfully deleted from cart"},
        tags=["Cart"]
    )
    def update_cart_item(self, request):
        data = request.data
        data_serializer = CartItemUpdateSerializer(data=data, context={"request": request})
        if not data_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=data_serializer.errors)

        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("cart_token")
            cart_item = CartItem.objects.filter(cart__cart_token=token,
                                                product=data_serializer.validated_data.get("product").id).first()
            if not cart_item:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Product does not exist")
            if cart_item and data_serializer.validated_data.get("quantity") == 0:
                cart_item.delete()
                return Response(data={"result": "Product successfully deleted from cart", "ok": True},
                                status=status.HTTP_204_NO_CONTENT)
        else:
            cart_item = CartItem.objects.filter(cart__customer=customer,
                                                product=data_serializer.validated_data.get("product").id).first()
            if not cart_item:
                raise CustomApiException(error_code=ErrorCodes.NOT_FOUND, message="Product does not exist")

            if cart_item and data_serializer.validated_data.get("quantity") == 0:
                cart_item.delete()
                return Response(data={"result": "Product successfully deleted from cart", "ok": True},
                                status=status.HTTP_204_NO_CONTENT)

        data["cart"] = cart_item.cart.id
        serializer = CartItemUpdateSerializer(cart_item, data=data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        operation_summary="Cart item bulk update",
        operation_description="Cart item bulk update",
        request_body=CartItemBulkUpdateSerializer(),
        responses={200: CartItemSerializer()},
        tags=["Cart"]
    )
    def cart_bulk_update(self, request):
        data = request.data
        bulk_serializer = CartItemBulkUpdateSerializer(data=data)
        if not bulk_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=bulk_serializer.errors)

        customer = request.user.id
        if not customer:
            token = request.COOKIES.get("cart_token")
            cart_items = CartItem.objects.filter(cart__cart_token=token)
        else:
            cart_items = CartItem.objects.filter(cart__customer=customer)

        for cart_item in cart_items:
            cart_item.is_checked = bulk_serializer.validated_data.get("is_checked")
            cart_item.save(update_fields=["is_checked"])

        return Response(data={"result": "All products is_checked status successfully updated", "ok": True},
                        status=status.HTTP_202_ACCEPTED)


class ServiceViewSet(ViewSet):
    pass


class QuestionsViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="Product questions list",
        operation_description="Product questions list",
        manual_parameters=[
            openapi.Parameter(
                name='page', in_=openapi.IN_QUERY, description='Page', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='page_size', in_=openapi.IN_QUERY, description='Page size', type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                name='product_id', in_=openapi.IN_QUERY, description='Product id', type=openapi.TYPE_INTEGER),
        ],
        responses={200: QuestionsSerializer(many=True)},
        tags=["Question"]
    )
    def questions_list(self, request):
        param = request.query_params
        param_serializer = CommentParamSerializer(data=param)
        if not param_serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=param_serializer.errors)

        questions = Questions.objects.filter(product=param_serializer.validated_data.get("product_id"))
        return Response(data={
            "result": get_questions_paginator(response_data=questions, page=param_serializer.validated_data.get("page"),
                                              page_size=param_serializer.validated_data.get("page_size"),
                                              context={"request": request}), "ok": True}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create product question",
        operation_description="Create product question",
        manual_parameters=[
            openapi.Parameter(name="product_id", in_=openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                              description="Product id")
        ],
        request_body=QuestionsCreateSerializer(),
        responses={201: QuestionsCreateSerializer()},
        tags=["Question"]
    )
    def question_create(self, request):
        param = request.query_params
        data = request.data
        data["customer"] = request.user.id
        data["product"] = param.get("product_id")
        serializer = QuestionsCreateSerializer(data=data, context={"reqeust": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Update product question",
        operation_description="Update product question",
        request_body=QuestionsUpdateSerializer(),
        responses={204: QuestionsUpdateSerializer()},
        tags=["Question"]
    )
    def update_question(self, request, pk):
        data = request.data
        question = Questions.objects.filter(id=pk, customer_id=request.user.id).first()
        if not question:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        serializer = QuestionsUpdateSerializer(question, data=data, partial=True, context={"request": request})
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)

        serializer.save()
        return Response(data={"result": serializer.data, "ok": True}, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        operation_summary="Delete product question",
        operation_description="Delete product question",
        responses={204: "Question successfully deleted"},
        tags=["Question"]
    )
    def delete_question(self, request, pk):
        question = Questions.objects.filter(id=pk, customer=request.user.id).first()
        if not question:
            raise CustomApiException(error_code=ErrorCodes.NOT_FOUND)

        question.delete()
        return Response(data={"result": "Question successfully deleted", "ok": True}, status=status.HTTP_204_NO_CONTENT)


    # @swagger_auto_schema(
    #     operation_summary="Create order",
    #     operation_description="Create order",
    #     request_body=,
    #     responses={201: },
    #     tags=["Order"]
    # )
    # def create_order(self, request):
    #     order = Order.objects.filter
    #     cart_items = CartItem.objects.filter(cart__customer_id=request.user.id)