from django.urls import path
from .views import (
    PreparePaymentView,
    CompletePaymentView,
    MerchantAPIView,
    UzumBankCheckView,
    UzumBankCreateView,
    UzumBankConfirmView,
    UzumBankReverseView,
    UzumBankStatusView
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
]
