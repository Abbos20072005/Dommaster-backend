from ckeditor.fields import RichTextField
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from abstract_model.base_model import BaseModel
from apps.base.models import MarketBranch
from .catalog import Brand, ProductItemCategory, ProductAttribute
from .choices import PUBLISH_STATUS, PUBLISH_STATUS_DRAFT


class Product(BaseModel):
    PRODUCT_UNIT_CHOICES = (
        ("kg", "KG"),
        ("l", "L"),
        ("sm", "SM"),
        ("pcs", "PCS"),
        ("m", "M"),
        ("g", "G"),
        ("pkg", "PKG"),
        ("set", "SET")
    )
    telegram_id = models.CharField(max_length=11, blank=True, null=True, verbose_name="Телеграм id")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="product_brand",
                              verbose_name="Бренд")
    badge = models.ForeignKey("ProductBadge", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="products", verbose_name="Бейдж")
    product_item_category = models.ForeignKey(ProductItemCategory, on_delete=models.CASCADE, blank=True, null=True,
                                              related_name="product_item_category",
                                              verbose_name="Предметная категория продуктов")
    name = models.CharField(max_length=500, verbose_name="Название")
    short_description = RichTextField(blank=True, null=True, verbose_name="Краткое описансе")
    description = RichTextField(verbose_name="Описание")
    price = models.FloatField(default=0.0, verbose_name="Цена")
    unit = models.CharField(choices=PRODUCT_UNIT_CHOICES, default="pcs")
    discount_price = models.FloatField(blank=True, null=True, verbose_name="Скидочная цена")
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
                               verbose_name="Рейтинг")
    discount = models.IntegerField(blank=True, null=True, verbose_name="Скидка")
    quantity = models.IntegerField(default=0, verbose_name="Количество")
    comments_quantity = models.IntegerField(default=0, verbose_name="Количество коментариев")
    questions_quantity = models.IntegerField(default=0, verbose_name="Количество вопросов")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    erp_active = models.BooleanField(default=True, verbose_name="Активен в 1С")
    publish_status = models.CharField(max_length=16, choices=PUBLISH_STATUS, default=PUBLISH_STATUS_DRAFT,
                                      verbose_name="Статус публикации")
    purchasable = models.BooleanField(default=False, verbose_name="Доступен к покупке")
    filter_data = models.JSONField(default=dict, blank=True)
    articul_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Артикул")
    barcode = models.CharField(max_length=100, blank=True, null=True, verbose_name="Штрихкод")
    product_code = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name="Код из 1С")
    weight = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, verbose_name="Вес, кг")
    length = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, verbose_name="Длина, м")
    width = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, verbose_name="Ширина, м")
    height = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, verbose_name="Высота, м")

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self)

    def update_rating(self):
        from django.db.models import Avg, Count
        agg_data = self.product_comment.aggregate(
            avg_rating=Avg("product_rating"),
            count_comments=Count("id")
        )
        self.rating = round(agg_data["avg_rating"], 1) if agg_data.get("avg_rating") else 0.0
        self.comments_quantity = agg_data["count_comments"] or 0
        self.save(update_fields=["rating", "comments_quantity"])

    def update_questions(self):
        from django.db.models import Count
        agg_data = self.product_question.aggregate(
            count_questions=Count("id")
        )
        self.questions_quantity = agg_data["count_questions"] or 0
        self.save(update_fields=["questions_quantity"])

    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"
        indexes = [
            GinIndex(fields=['name'], opclasses=['gin_trgm_ops'], name='idx_product_name_trgm'),
            GinIndex(fields=['name_uz'], opclasses=['gin_trgm_ops'], name='idx_product_name_uz_trgm'),
            GinIndex(fields=['name_ru'], opclasses=['gin_trgm_ops'], name='idx_product_name_ru_trgm'),
            models.Index(fields=['is_active'], name='idx_product_is_active'),
            models.Index(fields=['brand'], name='idx_product_brand'),
            models.Index(fields=['product_item_category'], name='idx_product_item_cat'),
        ]


class ProductRemaining(BaseModel):
    branch = models.ForeignKey(MarketBranch, on_delete=models.CASCADE, related_name="branch_remaining",
                               verbose_name="Склад")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_remaining",
                                verbose_name="Продукт")
    quantity = models.FloatField(default=0.0, verbose_name="Остаток")

    def __str__(self):
        return f"{self.branch.name} - {self.product.name}: {self.quantity}"

    class Meta:
        verbose_name = "Остаток продукта"
        verbose_name_plural = "Остатки продуктов"
        constraints = [
            models.UniqueConstraint(fields=["branch", "product"], name="unique_branch_product_remaining"),
        ]


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_image", verbose_name="Продукт")
    image = models.ImageField(upload_to="product_image", verbose_name="Изображение")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Изображение продукта"
        verbose_name_plural = "Изображения продуктов"


class ProductCharacteristics(BaseModel):
    product = models.ForeignKey(Product, blank=True, null=True, related_name="product_characteristics",
                                on_delete=models.CASCADE, verbose_name="Продукт")
    name = models.CharField(max_length=150, verbose_name="Название")
    unit = models.CharField(max_length=150, blank=True, null=True, verbose_name="Еденица измерения")
    value = models.CharField(max_length=150, verbose_name="Значение")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Харктеристика продукта"
        verbose_name_plural = "Характеристики продуктов"


class ProductAttributeValue(BaseModel):
    # Value of a category attribute for a product, kept as text per language (value_uz / value_ru):
    # number -> "2.5", boolean -> "true" / "false" (same in every language), list -> copy of the option's value
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="attribute_values",
                                verbose_name="Продукт")
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.PROTECT, related_name="product_values",
                                  verbose_name="Атрибут")
    value = models.CharField(max_length=255, verbose_name="Значение")

    def __str__(self):
        return f"{self.product_id} — {self.attribute}"

    class Meta:
        verbose_name = "Значение атрибута продукта"
        verbose_name_plural = "Значения атрибутов продуктов"
        unique_together = ("product", "attribute")


class ProductVariantGroup(BaseModel):
    DISPLAY_TYPES = (
        ("text", "Text"),
        ("image", "Image"),
    )
    name = models.CharField(max_length=255, verbose_name="Название группы")
    display_type = models.CharField(max_length=10, choices=DISPLAY_TYPES, default="text", verbose_name="Тип отображения")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Группа вариантов"
        verbose_name_plural = "Группы вариантов"


class ProductVariantItem(BaseModel):
    group = models.ForeignKey(ProductVariantGroup, on_delete=models.CASCADE, related_name="items", verbose_name="Группа")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variant_items", verbose_name="Продукт")
    display_value = models.CharField(max_length=255, verbose_name="Значение (текст)")

    def __str__(self):
        return f"{self.group.name} - {self.display_value}"

    class Meta:
        verbose_name = "Элемент варианта"
        verbose_name_plural = "Элементы вариантов"
        unique_together = ("group", "product")
        ordering = ("created_at",)
