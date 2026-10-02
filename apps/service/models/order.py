from django.db import models

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer, CustomerAddresses
from apps.base.models import Promocodes, MarketBranch
from django.conf import settings
from .choices import ORDER_STATUS, PAYMENT_STATUS, DELIVERY_TYPE, PAYMENT_TYPE, CASH_PAYMENT_METHOD
from .product import Product


class Manager(BaseModel):
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Менеджер"
        verbose_name_plural = "Менеджеры"


class Order(BaseModel):
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, blank=True, null=True, related_name="orders",
                                verbose_name="Менеджер")
    hold_id = models.BigIntegerField(null=True, blank=True)
    promocode = models.ForeignKey(Promocodes, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Промокод")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Покупатель")
    status = models.IntegerField(choices=ORDER_STATUS, default=0, verbose_name="Статус")
    total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость")
    payment_status = models.IntegerField(choices=PAYMENT_STATUS, default=0, verbose_name="Статус оплаты")
    order_location = models.ForeignKey(CustomerAddresses, on_delete=models.SET_NULL, blank=True, null=True,
                                       verbose_name="Локация доставки")
    delivery_type = models.IntegerField(choices=DELIVERY_TYPE, default=0, verbose_name="Тип доставки")
    pickup_branch = models.ForeignKey(MarketBranch, on_delete=models.SET_NULL, blank=True, null=True,
                                      verbose_name="Филиал самовывоза")
    payment_type = models.IntegerField(choices=PAYMENT_TYPE, null=True, blank=True, verbose_name="Тип оплаты")
    payment_method = models.CharField(max_length=10, choices=CASH_PAYMENT_METHOD, blank=True, null=True, verbose_name="Способ оплаты при получении")
    receiver_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Имя получателя")
    receiver_phone = models.CharField(max_length=14, blank=True, null=True, verbose_name="Телефон получателя")
    saved_price = models.FloatField(default=0.0, verbose_name="Сэкономленная сумма")
    products_total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость продуктов")
    ofd_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Ссылка на чек")
    delivery_price = models.DecimalField(max_digits=18, decimal_places=4, default=0.0,
                                         verbose_name="Стоимость доставки")
    yandex_claim_id = models.CharField(max_length=64, blank=True, null=True, verbose_name="ID заявки Яндекс Доставки")
    yandex_claim_status = models.CharField(max_length=50, blank=True, null=True, verbose_name="Статус заявки Яндекс Доставки")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        indexes = [
            models.Index(fields=['customer', 'status'], name='idx_order_cust_status'),
        ]


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items", verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_order_item",
                                verbose_name="Продукт")
    quantity = models.IntegerField(default=0, verbose_name="Количество")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Заказ продукта"
        verbose_name_plural = "Заказы продуктов"


class OrderComment(BaseModel):
    """Internal note on an order: admin panel only, never shown to the customer."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="comments", verbose_name="Заказ")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                               related_name="order_comments", verbose_name="Автор")
    text = models.TextField(verbose_name="Комментарий")
    is_system = models.BooleanField(default=False, verbose_name="Системный")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Внутренний комментарий к заказу"
        verbose_name_plural = "Внутренние комментарии к заказам"
        ordering = ("-created_at",)
