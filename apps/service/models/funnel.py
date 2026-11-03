from django.db import models

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer
from .choices import ORDER_CHANNEL
from .product import Product


class ProductEvent(BaseModel):
    # Product funnel events (BLD-371 / 372): one row per product. Purchases are not stored here, they come from
    # the orders. Logic: apps/service/funnel.py
    VIEW, ADD_TO_CART, CHECKOUT_START = "product_view", "add_to_cart", "checkout_start"
    TYPE_CHOICES = (
        (VIEW, "Просмотр карточки"),
        (ADD_TO_CART, "Добавление в корзину"),
        (CHECKOUT_START, "Начало оформления"),
    )

    event_type = models.CharField(max_length=16, choices=TYPE_CHOICES, verbose_name="Тип события")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="funnel_events",
                                verbose_name="Продукт")
    # "" = the client did not say (an old app version adding to the cart)
    platform = models.CharField(max_length=10, choices=ORDER_CHANNEL, blank=True, default="",
                                verbose_name="Платформа")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name="funnel_events", verbose_name="Клиент")
    # a visitor who is not logged in: the `X-Device-Id` header, else the `cart_token` cookie
    session_id = models.CharField(max_length=300, blank=True, default="", verbose_name="ID сессии")

    def __str__(self):
        return f"{self.event_type} #{self.product_id}"

    class Meta:
        verbose_name = "Событие воронки"
        verbose_name_plural = "События воронки"
        indexes = [
            models.Index(fields=["created_at"], name="idx_prodevent_created"),
            models.Index(fields=["product", "created_at"], name="idx_prodevent_product_created"),
        ]


class ProductFunnelDaily(models.Model):
    # The events of one day per product and platform, built every night from ProductEvent (kept forever,
    # the raw events only `funnel.EVENT_DAYS`)
    date = models.DateField(verbose_name="Дата")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="funnel_days",
                                verbose_name="Продукт")
    platform = models.CharField(max_length=10, choices=ORDER_CHANNEL, blank=True, default="",
                                verbose_name="Платформа")
    views = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    # distinct customers / sessions that opened the card that day (views without any id are not in it)
    viewers = models.PositiveIntegerField(default=0, verbose_name="Уникальные зрители")
    add_to_cart = models.PositiveIntegerField(default=0, verbose_name="Добавления в корзину")
    checkout_start = models.PositiveIntegerField(default=0, verbose_name="Начала оформления")

    def __str__(self):
        return f"{self.date} #{self.product_id} {self.platform}"

    class Meta:
        verbose_name = "Воронка товара за день"
        verbose_name_plural = "Воронка товаров по дням"
        constraints = [
            models.UniqueConstraint(fields=["date", "product", "platform"], name="uniq_funnel_day_product_platform"),
        ]
        indexes = [
            models.Index(fields=["date"], name="idx_funnel_day_date"),
            models.Index(fields=["product", "date"], name="idx_funnel_day_product_date"),
        ]
