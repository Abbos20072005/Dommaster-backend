from django.urls import path
from .views import ProductViewSet, BrandViewSet, SaleViewSet

urlpatterns = [
    path("categories/", ProductViewSet.as_view({"get": "categories_list"}), name="categories list"),
    path("sub/categories/<int:pk>/", ProductViewSet.as_view({"get": "sub_category_list"}), name="sub categories list"),
    path("item/categories/<int:pk>/", ProductViewSet.as_view({"get": "item_category_list"}),
         name="item categories list"),
    path("categories/products/<int:pk>/", ProductViewSet.as_view({"get": "categories_product_list"}),
         name="categories product list"),
    path("products/<int:pk>/", ProductViewSet.as_view({"get": "product_detail"}), name="products detail"),
    path("brands/", BrandViewSet.as_view({"get": "brand_list"}), name="brand list"),
    path("brands/<int:pk>/", BrandViewSet.as_view({"get": "brand_detail"}), name="brand detail"),
    path("brands/products/<int:pk>/", BrandViewSet.as_view({"get": "brand_products"}), name="brand products"),
    path("sale/", SaleViewSet.as_view({"get": "sale_products"}), name="sale products")
]
