from django.urls import path

from .yandex_delivery import YandexDeliveryIntegrationViewSet


urlpatterns = [
    path(
        "yandex/check-price/",
        YandexDeliveryIntegrationViewSet.as_view({"post": "check_price"}),
        name="yandex_delivery_check_price",
    ),
]
