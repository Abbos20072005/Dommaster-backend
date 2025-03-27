from django.urls import path
from .views import ProductViewSet

urlpatterns = [
    path("categories/", ProductViewSet.as_view({"get": "categories_list"}), name="categories list"),
    path("sub/categories/<int:pk>/", ProductViewSet.as_view({"get": "sub_category_list"}), name="sub categories list"),
    path("item/categories/<int:pk>/", ProductViewSet.as_view({"get": "item_category_list"}),
         name="item categories list"),
    path("categories/products/<int:pk>/", ProductViewSet.as_view({"get": "categories_product_list"}),
         name="categories product list")
]
