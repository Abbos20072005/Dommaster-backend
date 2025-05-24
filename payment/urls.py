from django.urls import path
from .views import PreparePaymentView, CompletePaymentView, MerchantAPIView, UzumBankPaymentView

urlpatterns = [
    path('click/prepare/', PreparePaymentView.as_view()),
    path('click/complete/', CompletePaymentView.as_view()),

    path('uzum/payment/check/', UzumBankPaymentView.as_view({'post':"transaction_check"})),
    path('uzum/payment/create/', UzumBankPaymentView.as_view({'post':"transaction_create"})),
    path('uzum/payment/confirm/', UzumBankPaymentView.as_view({'post':"transaction_confirm"})),
    path('uzum/payment/reverse/', UzumBankPaymentView.as_view({'post':"transaction_reverse"})),
    path('uzum/payment/status/', UzumBankPaymentView.as_view({'post':"transaction_status"})),

    path('payment/', MerchantAPIView.as_view()),
]
