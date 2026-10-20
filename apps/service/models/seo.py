from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from abstract_model.base_model import BaseModel
from utils.slug import unique_slug
from .catalog import Brand, ProductItemCategory


class FilterPage(BaseModel):
    # Landing page of one filter combination ("Bosch" + "perforator", "kabel VVG 3x2.5"), from the agreed keyword
    # list: an item category + optional brand + attribute filters in the shape of `product/filter` `filters`.
    # Open to clients (and the sitemap) only while active with at least MIN_PRODUCTS products
    # (apps/service/filter_pages.py); filter combinations without a page stay closed to search engines.
    MIN_PRODUCTS = 3
    MIN_SEARCH_VOLUME = 10

    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="Slug")
    item_category = models.ForeignKey(ProductItemCategory, on_delete=models.CASCADE, related_name="filter_pages",
                                      verbose_name="Предметная категория")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True, related_name="filter_pages",
                              verbose_name="Бренд")
    filters = models.JSONField(default=dict, blank=True, verbose_name="Фильтры")
    # md5 of the normalized item category + brand + filters: one page per combination
    combination_hash = models.CharField(max_length=32, unique=True, editable=False)

    keyword = models.CharField(max_length=255, blank=True, verbose_name="Ключевой запрос")
    search_volume = models.PositiveIntegerField(default=0, verbose_name="Запросов в месяц")
    title = models.CharField(max_length=255, verbose_name="Заголовок (H1)")
    meta_title = models.CharField(max_length=255, blank=True, verbose_name="Meta title")
    meta_description = models.TextField(blank=True, verbose_name="Meta description")
    text = models.TextField(blank=True, verbose_name="Текст")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    # active products of the combination, kept by filter_pages.refresh_counts (hourly + on admin save)
    products_count = models.PositiveIntegerField(default=0, editable=False, verbose_name="Товаров")
    counted_at = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        # same rule as filter_pages.open_pages()
        return (self.is_active and self.products_count >= self.MIN_PRODUCTS and self.item_category.is_active
                and (self.brand is None or self.brand.is_visible))

    def save(self, *args, **kwargs):
        from apps.service.filter_pages import combination_hash
        self.combination_hash = combination_hash(self.item_category_id, self.brand_id, self.filters)
        if not self.slug:
            self.slug = unique_slug(type(self), self.keyword_ru or self.title_ru or self.title, exclude_pk=self.pk,
                                    fallback="page")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Страница фильтра"
        verbose_name_plural = "Страницы фильтров"
        ordering = ("-search_volume", "id")


class SlugHistory(BaseModel):
    # An old slug of a product / brand / category, kept so the site can 301 it to the current slug.
    # One row per (object, language, old slug); written by SeoFieldsMixin.save() when a slug changes.
    # Logic (writing / resolving) lives in apps/service/seo_redirects.py.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="Тип объекта")
    object_id = models.PositiveIntegerField(verbose_name="ID объекта")
    content_object = GenericForeignKey("content_type", "object_id")
    language = models.CharField(max_length=5, verbose_name="Язык")
    old_slug = models.SlugField(max_length=255, db_index=True, verbose_name="Старый slug")

    def __str__(self):
        return f"{self.old_slug} ({self.language})"

    class Meta:
        verbose_name = "История slug"
        verbose_name_plural = "История slug"
        ordering = ("-id",)
        constraints = [
            models.UniqueConstraint(fields=("content_type", "language", "old_slug"),
                                    name="uniq_slug_history_ct_lang_slug"),
        ]
        indexes = [
            models.Index(fields=("content_type", "language", "old_slug"), name="idx_slug_history_lookup"),
        ]
