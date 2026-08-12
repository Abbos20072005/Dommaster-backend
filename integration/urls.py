from django.urls import path
from .one_c import OneCIntegrationViewSet
from .yandex_delivery import YandexDeliveryIntegrationViewSet

urlpatterns = [
    path(
        "yandex/check-price/",
        YandexDeliveryIntegrationViewSet.as_view({"post": "check_price"}),
        name="yandex_delivery_check_price",
    ),
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
    path(
        "1c/price-list/create/",
        OneCIntegrationViewSet.as_view({"post": "price_list_create"}),
        name="one_c_price_list_create",
    ),
    path(
        "1c/warehouse/create/",
        OneCIntegrationViewSet.as_view({"post": "warehouse_create"}),
        name="one_c_warehouse_create",
    ),
    path(
        "1c/remaining/create/",
        OneCIntegrationViewSet.as_view({"post": "remaining_create"}),
        name="one_c_remaining_create",
    ),
]
