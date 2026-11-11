from django.core.cache import cache
from django.db import models

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer
from .choices import ORDER_CHANNEL


class SearchSynonym(BaseModel):
    # One group of equivalent search terms ("6203 2RS", "6203-2RS", "180203"): a query with one of them also
    # looks for the others. Logic: apps/service/search.py
    terms = models.JSONField(default=list, verbose_name="Синонимы")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return " = ".join(self.terms or [])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from apps.service.search import SYNONYMS_CACHE_KEY
        cache.delete(SYNONYMS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        from apps.service.search import SYNONYMS_CACHE_KEY
        cache.delete(SYNONYMS_CACHE_KEY)
        return result

    class Meta:
        verbose_name = "Синоним поиска"
        verbose_name_plural = "Синонимы поиска"
        ordering = ("-id",)


class NotFoundSearch(BaseModel):
    # A catalog search that found nothing (`product/filter/` with `q` and no other filter, first page)
    query = models.CharField(max_length=255, verbose_name="Запрос")
    # lower case, words joined by one space: the rows of one query are grouped by it
    normalized = models.CharField(max_length=255, db_index=True, verbose_name="Нормализованный запрос")
    language = models.CharField(max_length=5, verbose_name="Язык")
    platform = models.CharField(max_length=10, choices=ORDER_CHANNEL, blank=True, default="",
                                verbose_name="Платформа")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="not_found_searches", verbose_name="Клиент")
    # a visitor who is not logged in: the `X-Device-Id` header, else the `cart_token` cookie
    session_id = models.CharField(max_length=300, blank=True, default="", verbose_name="ID сессии")

    def __str__(self):
        return self.query

    class Meta:
        verbose_name = "Поиск без результата"
        verbose_name_plural = "Поиски без результата"
        indexes = [models.Index(fields=["created_at"], name="idx_notfound_search_created")]


class SearchRequest(BaseModel):
    # "Не нашли — оставьте заявку": a request for a product the search did not find, for a manager to call back
    NEW, IN_PROGRESS, DONE, REJECTED = "new", "in_progress", "done", "rejected"
    STATUS_CHOICES = (
        (NEW, "Новая"),
        (IN_PROGRESS, "В работе"),
        (DONE, "Обработана"),
        (REJECTED, "Отклонена"),
    )

    query = models.CharField(max_length=500, verbose_name="Что искали")
    phone_number = models.CharField(max_length=20, verbose_name="Телефон")
    company = models.CharField(max_length=255, blank=True, default="", verbose_name="Компания")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="search_requests", verbose_name="Клиент")
    language = models.CharField(max_length=5, verbose_name="Язык")
    platform = models.CharField(max_length=10, choices=ORDER_CHANNEL, blank=True, default="",
                                verbose_name="Платформа")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=NEW, verbose_name="Статус")
    manager_comment = models.TextField(blank=True, default="", verbose_name="Комментарий менеджера")

    def __str__(self):
        return f"#{self.id} {self.query}"

    class Meta:
        verbose_name = "Заявка на товар"
        verbose_name_plural = "Заявки на товар"
        ordering = ("-id",)
