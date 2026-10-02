from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from django.core.validators import RegexValidator
from django.db import models

from abstract_model.base_model import BaseModel


class AddsBrands(BaseModel):
    # "Adds" = ads: a promo campaign block (e.g. "Summer big sales"), not a brand entity.
    # Shows the chosen `products` as a section; `title`/`description` (HTML) are the campaign page
    # (client: GET adds/brands/ list, adds/brands/<id>/ detail). `brand` is nullable, one campaign per brand.
    name = models.CharField(max_length=450, verbose_name="Название")
    title = models.CharField(max_length=350, verbose_name="Заголовок")
    description = RichTextField(verbose_name="Описание")
    brand = models.OneToOneField(to="Brand", on_delete=models.SET_NULL, null=True, verbose_name="Бренд")
    products = models.ManyToManyField(to="Product", verbose_name="Продукты")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Реклама бренда"
        verbose_name_plural = "Рекламы брендов"


class PartnerBrand(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Название")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Бренд-партнёр"
        verbose_name_plural = "Бренды-партнёры"


class Tag(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")
    product = models.ManyToManyField(to="Product", blank=True, verbose_name="Продукты")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"


class ProductBadge(BaseModel):
    # Card label ("Yangi", "Hit", ...), a product may have several (Product.badges M2M).
    # Products of a `manual` badge are picked by hand in the product form; products of an `auto` badge are
    # exactly those matching its rule (apps/service/badges.py).
    MANUAL, AUTO = "manual", "auto"
    KIND_CHOICES = (
        (MANUAL, "Вручную"),
        (AUTO, "Автоматически"),
    )
    DISCOUNT, CREATED_DAYS, QUANTITY, SALES_30D = "discount", "created_days", "quantity", "sales_30d"
    RULE_FIELD_CHOICES = (
        (DISCOUNT, "Скидка, %"),
        (CREATED_DAYS, "Добавлен, дней назад"),
        (QUANTITY, "Остаток, шт"),
        (SALES_30D, "Продажи за 30 дней, шт"),
    )
    GT, GTE, LT, LTE, EQ = "gt", "gte", "lt", "lte", "eq"
    RULE_OPERATOR_CHOICES = (
        (GT, ">"),
        (GTE, "≥"),
        (LT, "<"),
        (LTE, "≤"),
        (EQ, "="),
    )
    name = models.CharField(max_length=100, verbose_name="Название")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=MANUAL, verbose_name="Тип")
    # the rule (only for `auto`): <rule_field> <rule_operator> <rule_value>, e.g. discount > 0
    rule_field = models.CharField(max_length=20, choices=RULE_FIELD_CHOICES, blank=True, null=True,
                                  verbose_name="Правило: показатель")
    rule_operator = models.CharField(max_length=3, choices=RULE_OPERATOR_CHOICES, blank=True, null=True,
                                     verbose_name="Правило: оператор")
    rule_value = models.IntegerField(blank=True, null=True, verbose_name="Правило: значение")
    color = models.CharField(max_length=7, default="#2563EB", verbose_name="Цвет",
                             validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a HEX color, e.g. #2563EB.")])
    # order of the badges on a product card
    position = models.IntegerField(default=0, verbose_name="Позиция")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Бейдж продукта"
        verbose_name_plural = "Бейджи продуктов"
        ordering = ("position", "id")


class Sale(BaseModel):
    products = models.ManyToManyField("Product", related_name="sale_products", verbose_name="Продукты")
    name = models.CharField(max_length=150, verbose_name="Название")
    image = models.ImageField(upload_to="sale/image/")
    bg_image = models.ImageField(upload_to="sale/bg_image/", verbose_name="Изображение фона")
    discount_from = models.DateField()
    discount_to = models.DateField()
    is_main = models.BooleanField(default=False, verbose_name="Основной")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Распродажа"
        verbose_name_plural = "Распродажи"


class Announcements(BaseModel):
    title = models.CharField(max_length=150, verbose_name="Заголовок")
    image = models.ImageField(upload_to="sales/", verbose_name="Изображение")
    description = models.TextField(verbose_name="Описание")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"


class Service(BaseModel):
    name = models.CharField(max_length=250, verbose_name="Название")
    icon = models.ImageField(upload_to="service/", verbose_name="Иконка")
    description = RichTextUploadingField(verbose_name="Описание")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"
