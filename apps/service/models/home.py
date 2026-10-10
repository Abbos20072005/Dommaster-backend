from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

from abstract_model.base_model import BaseModel
from apps.base.models import Banner


class HomeBlock(BaseModel):
    # One section of the home page ("Bosh sahifa" in the admin UI). The rows are the draft the admin edits;
    # customers get the snapshot stored by "publish" (HomePage.published_data, apps/service/home.py).
    # Admin API only, the client home page does not read it yet.
    SLIDER, BANNER, CATEGORIES, BRANDS, PAGES, CONTENT, ADDS_BRANDS = \
        "slider", "banner", "categories", "brands", "pages", "content", "adds_brands"
    BADGE_PRODUCTS, SALE_PRODUCTS, NEW_PRODUCTS, BESTSELLERS, ALL_PRODUCTS = \
        "badge_products", "sale_products", "new_products", "bestsellers", "all_products"
    TYPE_CHOICES = (
        (SLIDER, "Слайдер баннеров"),
        (CATEGORIES, "Категории"),
        (BADGE_PRODUCTS, "Подборка по тегу"),
        (SALE_PRODUCTS, "Товары распродажи"),
        (NEW_PRODUCTS, "Новые товары"),
        (BESTSELLERS, "Самые продаваемые товары"),
        (ALL_PRODUCTS, "Все товары"),
        (BANNER, "Баннер"),
        (BRANDS, "Бренды"),
        (PAGES, "Страницы"),
        (CONTENT, "Статьи и видео"),
        (ADDS_BRANDS, "Рекламные блоки"),
    )
    # blocks made of products: the display rules of HomePage apply to them
    PRODUCT_TYPES = (BADGE_PRODUCTS, SALE_PRODUCTS, NEW_PRODUCTS, BESTSELLERS, ALL_PRODUCTS)
    # not stored: derived from `is_visible` + the display rules (apps/service/home.py)
    VISIBLE, HIDDEN, RULE_HIDDEN = "visible", "hidden", "rule_hidden"
    STATUS_CHOICES = (
        (VISIBLE, "Показывается"),
        (HIDDEN, "Скрыт"),
        (RULE_HIDDEN, "Скрыт по правилу"),
    )

    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Тип")
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    position = models.PositiveIntegerField(default=0, verbose_name="Позиция")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")
    show_on_site = models.BooleanField(default=True, verbose_name="Показывать на сайте")
    show_in_app = models.BooleanField(default=True, verbose_name="Показывать в приложении")

    # the source of the block, one per type (the admin serializer empties the ones the type does not use)
    banner_placement = models.CharField(max_length=20, choices=Banner.PLACEMENT_CHOICES, blank=True, default="",
                                        verbose_name="Слайдер: расположение баннеров")
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE, null=True, blank=True, related_name="home_blocks",
                               verbose_name="Баннер")
    badge = models.ForeignKey("ProductBadge", on_delete=models.CASCADE, null=True, blank=True,
                              related_name="home_blocks", verbose_name="Тег")
    # sale_products: empty = the main sale (Sale.is_main)
    sale = models.ForeignKey("Sale", on_delete=models.CASCADE, null=True, blank=True, related_name="home_blocks",
                             verbose_name="Распродажа")
    days = models.PositiveIntegerField(null=True, blank=True, verbose_name="Новые товары: за сколько дней")
    # pages: [{"title_uz", "title_ru", "title_en", "path"}]
    pages = models.JSONField(default=list, blank=True, verbose_name="Страницы")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Блок главной страницы"
        verbose_name_plural = "Блоки главной страницы"
        ordering = ("position", "id")


class HomePage(BaseModel):
    # Singleton (pk=1, use `HomePage.load()`): display rules of the product blocks + the published layout.
    hide_out_of_stock = models.BooleanField(default=True, verbose_name="Скрывать товары без остатка")
    # stored only: there is no "price updated at" on Product yet, nothing is filtered by it
    hide_stale_price = models.BooleanField(default=True, verbose_name="Скрывать товары с устаревшей ценой")
    # a product block with fewer matching products hides itself
    min_products = models.PositiveIntegerField(default=4, verbose_name="Минимум товаров в блоке")

    # the personal feed (`products/recommended/`, apps/service/feed.py). Not a part of the published version:
    # both apply at once. Off = the endpoint returns the random feed; holdout = the share of visitors who keep
    # getting the random feed, to compare with
    personal_feed_enabled = models.BooleanField(default=True, verbose_name="Персональная лента включена")
    personal_feed_holdout_percent = models.PositiveSmallIntegerField(
        default=10, validators=[MaxValueValidator(100)], verbose_name="Персональная лента: контрольная группа, %")

    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Последняя публикация")
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="+", verbose_name="Опубликовал")
    # {"rules": {...}, "blocks": [...]} as built by apps/service/home.draft_snapshot()
    published_data = models.JSONField(null=True, blank=True, verbose_name="Опубликованная версия")

    def __str__(self):
        return "Главная страница"

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    class Meta:
        verbose_name = "Главная страница"
        verbose_name_plural = "Главная страница"
