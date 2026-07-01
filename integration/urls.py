from django.urls import path
from .one_c import OneCIntegrationViewSet

urlpatterns = [
    path(
        "1c/product/create/",
        OneCIntegrationViewSet.as_view({"post": "product_create"}),
        name="one_c_product_create",
    ),
]
