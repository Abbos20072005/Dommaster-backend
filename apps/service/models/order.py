from datetime import timedelta
from decimal import Decimal

from django.db import models

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer, CustomerAddresses
from apps.base.models import Promocodes, MarketBranch
from django.conf import settings
from .choices import ORDER_STATUS, PAYMENT_STATUS, DELIVERY_TYPE, PAYMENT_TYPE, CASH_PAYMENT_METHOD, ORDER_CHANNEL
from .catalog import ProductCategory
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
    # null = unknown: orders placed before the field, by an old app version or from the admin panel
    channel = models.CharField(max_length=10, choices=ORDER_CHANNEL, blank=True, null=True, verbose_name="Канал")
    total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость")
    payment_status = models.IntegerField(choices=PAYMENT_STATUS, default=0, verbose_name="Статус оплаты")
    order_location = models.ForeignKey(CustomerAddresses, on_delete=models.SET_NULL, blank=True, null=True,
                                       verbose_name="Локация доставки")
    # copy of the address details at the time of the order (CustomerAddresses.details()) - the address may change later
    apartment = models.CharField(max_length=50, blank=True, default="", verbose_name="Квартира / офис")
    intercom = models.CharField(max_length=50, blank=True, default="", verbose_name="Домофон")
    entrance = models.CharField(max_length=20, blank=True, default="", verbose_name="Подъезд")
    floor = models.CharField(max_length=20, blank=True, default="", verbose_name="Этаж")
    courier_comment = models.CharField(max_length=500, blank=True, default="", verbose_name="Комментарий для курьера")
    delivery_type = models.IntegerField(choices=DELIVERY_TYPE, default=0, verbose_name="Тип доставки")
    pickup_branch = models.ForeignKey(MarketBranch, on_delete=models.SET_NULL, blank=True, null=True,
                                      verbose_name="Филиал самовывоза")
    pickup_store_snapshot = models.JSONField(blank=True, null=True, verbose_name="Магазин самовывоза (снимок)")
    ready_for_pickup_at = models.DateTimeField(blank=True, null=True, verbose_name="Готов к выдаче")
    pickup_deadline = models.DateTimeField(blank=True, null=True, verbose_name="Забрать до")
    pickup_expired_at = models.DateTimeField(blank=True, null=True, verbose_name="Срок хранения истёк")
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
    # customer's role when the order was placed (set in save(); prorab = PRO); null = order older than the field
    role_at_order = models.CharField(max_length=20, choices=Customer.Role.choices, blank=True, null=True,
                                     verbose_name="Роль клиента при заказе")
    # promocode discount taken off the goods; null = order older than the field (derived from the totals)
    promocode_discount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True,
                                             verbose_name="Скидка по промокоду")

    PENDING, COLLECTING, DELIVERING, COMPLETED, CANCELED, READY_FOR_PICKUP = 0, 1, 2, 3, 4, 5
    DELIVERY, PICKUP = 0, 1
    PICKUP_DAYS = 2
    DEPENDENT_FIELDS = {
        "status": ("ready_for_pickup_at", "pickup_deadline", "pickup_expired_at"),
        "pickup_branch": ("pickup_store_snapshot",),
    }

    def __str__(self):
        return str(self.id)

    @property
    def pickup_expired(self):
        """Ready for pickup and the deadline has passed (nobody came)."""
        from apps.base.stores import tashkent_now
        return (self.status == self.READY_FOR_PICKUP and self.pickup_deadline is not None
                and self.pickup_deadline < tashkent_now())

    @classmethod
    def deadline_from(cls, ready_at):
        return ready_at + timedelta(days=cls.PICKUP_DAYS)

    def save(self, *args, **kwargs):
        if self._state.adding and self.role_at_order is None and self.customer_id:
            self.role_at_order = Customer.objects.filter(pk=self.customer_id).values_list("role", flat=True).first()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            for field, dependent in self.DEPENDENT_FIELDS.items():
                if field in update_fields or f"{field}_id" in update_fields:
                    update_fields.update(dependent)
            kwargs["update_fields"] = update_fields
        super().save(*args, **kwargs)

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
    # price of one unit at the time of the order, after the product discount; null = item older than the field
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True,
                                     verbose_name="Цена за единицу")
    # PRO project the item is linked to (apps/service/pro.py) + the product's root category at linking time
    project = models.ForeignKey("service.Project", on_delete=models.SET_NULL, blank=True, null=True,
                                related_name="order_items", verbose_name="Проект")
    category_root = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name="+", verbose_name="Категория при привязке")

    def __str__(self):
        return str(self.id)

    @staticmethod
    def unit_price_of(product):
        """What the cart charges for one unit: the discount price when set."""
        price = product.discount_price if product.discount_price is not None else product.price
        return Decimal(str(price or 0)).quantize(Decimal("0.01"))

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
