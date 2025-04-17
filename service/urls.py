from django.urls import path
from .views import ProductViewSet, BrandViewSet, SaleViewSet, AddsBrandsViewSet, CommentViewSet, FavouriteViewSet, \
    CartViewSet

urlpatterns = [
    path("categories/", ProductViewSet.as_view({"get": "categories_list"}), name="categories list"),
    path("sub/categories/<int:pk>/", ProductViewSet.as_view({"get": "sub_category_list"}), name="sub categories list"),
    path("item/categories/<int:pk>/", ProductViewSet.as_view({"get": "item_category_list"}),
         name="item categories list"),
    path("products/<int:pk>/", ProductViewSet.as_view({"get": "product_detail"}), name="products detail"),
    path("brands/", BrandViewSet.as_view({"get": "brand_list"}), name="brand list"),
    path("brands/<int:pk>/", BrandViewSet.as_view({"get": "brand_detail"}), name="brand detail"),
    path("sale/", SaleViewSet.as_view({"get": "sale_products"}), name="sale products"),
    path("adds/brands/", AddsBrandsViewSet.as_view({"get": "adds_brands"}), name="adds brands"),
    path("adds/brands/<int:pk>/", AddsBrandsViewSet.as_view({"get": "adds_brands_detail"}), name="adds brands detail"),
    path("search/", ProductViewSet.as_view({"get": "search_by_name"}), name="search by name"),
    path("product/filter/", ProductViewSet.as_view({"post": "product_filter"}), name="product filter"),
    path("comment/create/<int:pk>/", CommentViewSet.as_view({"post": "comment_create"}), name="comment create"),
    path("comment/update/<int:pk>/", CommentViewSet.as_view({"patch": "comment_update"}), name="comment update"),
    path("comment/delete/<int:pk>/", CommentViewSet.as_view({"delete": "comment_delete"}), name="comment delete"),
    path("most/sold/", ProductViewSet.as_view({"get": "most_sold"}), name="most sold"),
    path("favourite/create/", FavouriteViewSet.as_view({"post": "create_favourite"}), name="create favourite"),
    path("favourite/list/", FavouriteViewSet.as_view({"get": "favourite_list"}), name="favourite list"),
    path("cart/", CartViewSet.as_view({"get": "get_cart"}), name="get cart"),
    path("cart/item/create/", CartViewSet.as_view({"post": "create_cart_item"}), name="create cart item"),
    path("cart/item/update/", CartViewSet.as_view({"patch": "update_cart_item"}), name="update cart item")

]
