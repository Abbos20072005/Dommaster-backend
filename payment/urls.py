from django.urls import path
from .views import PreparePaymentView, CompletePaymentView, MerchantAPIView

urlpatterns = [
    path('prepare/', PreparePaymentView.as_view()),
    path('complete/', CompletePaymentView.as_view()),
    path('', MerchantAPIView.as_view()),
]
