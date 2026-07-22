from django.urls import path
from .one_c import OneCIntegrationViewSet

urlpatterns = [
    path(
        "1c/product/create/",
        OneCIntegrationViewSet.as_view({"post": "product_create"}),
        name="one_c_product_create",
    ),
    path(
        "1c/brand/create/",
        OneCIntegrationViewSet.as_view({"post": "brand_create"}),
        name="one_c_brand_create",
    ),
    path(
        "1c/category/create/",
        OneCIntegrationViewSet.as_view({"post": "category_create"}),
        name="one_c_category_create",
    ),
    path(
        "1c/sub-category/create/",
        OneCIntegrationViewSet.as_view({"post": "sub_category_create"}),
        name="one_c_sub_category_create",
    ),
    path(
        "1c/item-category/create/",
        OneCIntegrationViewSet.as_view({"post": "item_category_create"}),
        name="one_c_item_category_create",
    ),
    path(
        "1c/unit/create/",
        OneCIntegrationViewSet.as_view({"post": "unit_create"}),
        name="one_c_unit_create",
    ),
]
