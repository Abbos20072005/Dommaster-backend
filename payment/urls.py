from django.urls import path
from .views import (
    PreparePaymentView,
    CompletePaymentView,
    MerchantAPIView,
    UzumBankCheckView,
    UzumBankCreateView,
    UzumBankConfirmView,
    UzumBankReverseView,
    UzumBankStatusView,
    AtmosCreateHoldView,
    AtmosChargeHoldView,
    AtmosCancelHoldView,
    AtmosCardBindCheckoutView,
    AtmosCardBindCallbackView,
    CustomerCardViewSet
)

urlpatterns = [
    path('click/prepare/', PreparePaymentView.as_view()),
    path('click/complete/', CompletePaymentView.as_view()),

    path('uzum/payment/check', UzumBankCheckView.as_view(), name='check'),
    path('uzum/payment/create', UzumBankCreateView.as_view(), name='create'),
    path('uzum/payment/confirm', UzumBankConfirmView.as_view(), name='confirm'),
    path('uzum/payment/reverse', UzumBankReverseView.as_view(), name='reverse'),
    path('uzum/payment/status',UzumBankStatusView.as_view(), name='status'),

    path('payment/', MerchantAPIView.as_view()),

    path("atmos/card-bind/init/", AtmosCardBindCheckoutView.as_view(), name="atmos-card-bind-init"),
    path("atmos/card-bind/callback/", AtmosCardBindCallbackView.as_view(), name="atmos-card-bind-callback"),
    path("payment/hold/create/", AtmosCreateHoldView.as_view()),
    path("payment/hold/charge/", AtmosChargeHoldView.as_view()),
    path("payment/hold/cancel/", AtmosCancelHoldView.as_view()),

    path("customer/cards/", CustomerCardViewSet.as_view({"get": "cards_list"}), name="customer-cards-list"),
    path("customer/cards/<int:pk>/", CustomerCardViewSet.as_view({"get": "card_detail", "patch": "card_update", "delete": "card_delete"}), name="customer-card-detail"),
]
