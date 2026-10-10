from django.db import models

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer
from .product import Product


class InterestEvent(BaseModel):
    # What a customer / a device looked at and searched for: the signals of the personal feed that no other table
    # keeps (purchases, cart and favourites are read from their own tables). Logic: apps/service/feed.py
    VIEW, SEARCH = "view", "search"
    TYPE_CHOICES = (
        (VIEW, "Просмотр товара"),
        (SEARCH, "Поиск"),
    )

    event_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Тип события")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name="interest_events", verbose_name="Клиент")
    # the `X-Device-Id` header: the only identity of a visitor who is not logged in
    device_id = models.CharField(max_length=300, blank=True, default="", verbose_name="ID устройства")
    # view
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True,
                                related_name="interest_events", verbose_name="Продукт")
    # search: the text, the item categories most of the found products are in, how many were found (0 = nothing)
    query = models.CharField(max_length=255, blank=True, default="", verbose_name="Поисковый запрос")
    item_category_ids = models.JSONField(default=list, blank=True, verbose_name="Предметные категории результатов")
    results_count = models.PositiveIntegerField(null=True, blank=True, verbose_name="Найдено товаров")

    def __str__(self):
        return f"{self.event_type} #{self.id}"

    class Meta:
        verbose_name = "Событие интереса"
        verbose_name_plural = "События интереса"
        indexes = [
            models.Index(fields=["customer", "created_at"], name="idx_interest_cust_created"),
            models.Index(fields=["device_id", "created_at"], name="idx_interest_device_created"),
        ]


class FeedImpression(BaseModel):
    # One row per `products/recommended/` response: what was shown, from which source, to which test group.
    # The only way to tell later whether the personal feed sells more than the random one.
    PERSONAL, POPULAR, HOLDOUT, DISABLED, ERROR = "personal", "popular", "holdout", "disabled", "error"
    VARIANT_CHOICES = (
        (PERSONAL, "Персональная лента"),
        (POPULAR, "Нет сигналов: популярные + случайные"),
        (HOLDOUT, "Контрольная группа: случайная лента"),
        (DISABLED, "Лента выключена"),
        (ERROR, "Ошибка: случайная лента"),
    )

    # the same for all pages of one feed (viewer + seed)
    feed_request_id = models.UUIDField(db_index=True, verbose_name="ID ленты")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name="feed_impressions", verbose_name="Клиент")
    device_id = models.CharField(max_length=300, blank=True, default="", verbose_name="ID устройства")
    seed = models.PositiveIntegerField(verbose_name="Seed")
    page = models.PositiveIntegerField(verbose_name="Страница")
    page_size = models.PositiveIntegerField(verbose_name="Размер страницы")
    variant = models.CharField(max_length=16, choices=VARIANT_CHOICES, verbose_name="Вариант")
    personalized = models.BooleanField(default=False, verbose_name="Персонализирована")
    # [[product id, rec_source], ...] in the shown order
    items = models.JSONField(default=list, blank=True, verbose_name="Показанные товары")

    def __str__(self):
        return f"{self.feed_request_id} p{self.page}"

    class Meta:
        verbose_name = "Показ ленты"
        verbose_name_plural = "Показы ленты"
        indexes = [
            models.Index(fields=["customer", "created_at"], name="idx_feedimp_cust_created"),
            models.Index(fields=["device_id", "created_at"], name="idx_feedimp_device_created"),
        ]
