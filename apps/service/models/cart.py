import secrets

from django.db import models
from django.db.models import F, Sum, Case, When, FloatField as DjangoFloatField, Value

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer
from .product import Product


class Cart(BaseModel):
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.CASCADE, verbose_name="Клиент")
    cart_token = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Токен карзины")
    total_price = models.FloatField(default=0.0, verbose_name="Общая цена")
    saved_price = models.FloatField(default=0.0, verbose_name="Сэкономленная сумма")
    products_total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость продуктов")

    def total_items(self):
        return self.cart_item.aggregate(total=Sum('quantity'))['total'] or 0

    def calculate_total_price(self):
        agg = self.cart_item.filter(
            is_checked=True, product__isnull=False
        ).aggregate(
            total=Sum(
                Case(
                    When(
                        product__discount_price__isnull=False,
                        then=F('product__discount_price') * F('quantity')
                    ),
                    default=F('product__price') * F('quantity'),
                    output_field=DjangoFloatField()
                )
            ),
            saved=Sum(
                Case(
                    When(
                        product__discount_price__isnull=False,
                        then=(F('product__price') - F('product__discount_price')) * F('quantity')
                    ),
                    default=Value(0.0),
                    output_field=DjangoFloatField()
                )
            ),
            products_total=Sum(
                F('product__price') * F('quantity'),
                output_field=DjangoFloatField()
            )
        )
        self.total_price = agg['total'] or 0.0
        self.saved_price = agg['saved'] or 0.0
        self.products_total_price = agg['products_total'] or 0.0
        return self.total_price, self.saved_price, self.products_total_price

    def save(self, *args, **kwargs):
        if not self.cart_token:
            self.cart_token = secrets.token_hex(16)
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Карзина"
        verbose_name_plural = "Карзины"
        ordering = ("-created_at",)


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, related_name="cart_item", on_delete=models.CASCADE, verbose_name="Карзина")
    product = models.ForeignKey(Product, related_name="cart_product", on_delete=models.SET_NULL, null=True,
                                verbose_name="Продукт")
    quantity = models.IntegerField(default=1, verbose_name="Количество")
    is_checked = models.BooleanField(default=True, verbose_name="Вабран")

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = ("cart", "product")
        verbose_name = "Вещь в корзине"
        verbose_name_plural = "Вещи в корзине"
        ordering = ("-created_at",)


class Favourites(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Клиент")
    favourite_token = models.CharField(max_length=64, blank=True, null=True, verbose_name="Токен карзины")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")

    def __str__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        if not self.favourite_token:
            self.favourite_token = secrets.token_hex(16)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Избранный"
        verbose_name_plural = "Избранные"
        indexes = [
            models.Index(fields=['customer', 'product'], name='idx_fav_cust_prod'),
            models.Index(fields=['favourite_token'], name='idx_fav_token'),
        ]


class RecentlyViewedProducts(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recently_viewed_products",
                                verbose_name="Продукт")

    def __str__(self):
        return self.customer.full_name

    class Meta:
        verbose_name = "Недавно просмотренный продукт"
        verbose_name_plural = "Недавно просмотренные продукты"
        ordering = ("-created_at",)
