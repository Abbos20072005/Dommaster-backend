from django.db import models

from abstract_model.base_model import BaseModel
from .catalog import ProductItemCategory
from .product import Product


class ProductItemCategoryFilterSchema(BaseModel):
    item_category = models.ForeignKey(
        ProductItemCategory, on_delete=models.CASCADE,
        related_name="filter_schemas",
        verbose_name="Категория"
    )
    key = models.SlugField(max_length=100, allow_unicode=True, verbose_name="Ключ (slug)")
    source_name_ru = models.CharField(max_length=150, verbose_name="Название в 1С")
    label = models.CharField(max_length=150, verbose_name="Название")
    type = models.CharField(max_length=20, choices=[
        ("checkbox", "Multi-select"),
        ("radio", "Single select"),
        ("range", "Range slider"),
    ], default="checkbox", verbose_name="Тип фильтра")
    unit = models.CharField(max_length=50, blank=True, verbose_name="Единица измерения")
    position = models.IntegerField(default=0, verbose_name="Позиция")
    is_filterable = models.BooleanField(default=True, verbose_name="Фильтруемый")
    is_quick_filter = models.BooleanField(default=False, verbose_name="Быстрый фильтр (чип)")
    max_quick_filters = models.PositiveIntegerField(default=0, verbose_name="Макс. кол-во быстрых фильтров")
    type_locked = models.BooleanField(default=False, verbose_name="Тип зафиксирован")

    def __str__(self):
        return f"{self.item_category.name} — {self.label}"

    class Meta:
        verbose_name = "Схема фильтра категории"
        verbose_name_plural = "Схемы фильтров категорий"
        unique_together = ("item_category", "key")
        ordering = ("position",)


class ProductFilterNumericValue(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                 related_name="numeric_filter_values",
                                 verbose_name="Продукт")
    schema = models.ForeignKey(ProductItemCategoryFilterSchema,
                                on_delete=models.CASCADE,
                                verbose_name="Схема фильтра")
    value = models.FloatField(verbose_name="Значение")

    def __str__(self):
        return f"{self.product.name} — {self.schema.key}: {self.value}"

    class Meta:
        verbose_name = "Числовое значение фильтра"
        verbose_name_plural = "Числовые значения фильтров"
        unique_together = ("product", "schema")
        indexes = [
            models.Index(fields=["schema", "value"], name="idx_num_filt_schema_val"),
        ]
