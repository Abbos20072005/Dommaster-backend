from django.contrib.postgres.indexes import GinIndex
from django.db import models

from abstract_model.base_model import BaseModel


class Brand(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")
    image = models.ImageField(upload_to="brand/image/", verbose_name="Изображение")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код из 1С")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"
        indexes = [
            GinIndex(fields=['name'], opclasses=['gin_trgm_ops'], name='idx_brand_name_trgm'),
            GinIndex(fields=['name_uz'], opclasses=['gin_trgm_ops'], name='idx_brand_name_uz_trgm'),
            GinIndex(fields=['name_ru'], opclasses=['gin_trgm_ops'], name='idx_brand_name_ru_trgm'),
            GinIndex(fields=['name_en'], opclasses=['gin_trgm_ops'], name='idx_brand_name_en_trgm'),
        ]


class ProductCategory(BaseModel):
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код из 1С")
    name = models.CharField(max_length=255, verbose_name="Название")
    icon = models.ImageField(upload_to="product_category/icon/")
    image = models.ImageField(upload_to="product_category", verbose_name="Изображение")
    position = models.IntegerField(default=0, verbose_name="Позиция")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self)

    class Meta:
        verbose_name = "Категория продуктов"
        verbose_name_plural = "Категории продуктов"
        ordering = ("position",)
        indexes = [
            GinIndex(fields=['name'], opclasses=['gin_trgm_ops'], name='idx_category_name_trgm'),
            GinIndex(fields=['name_uz'], opclasses=['gin_trgm_ops'], name='idx_category_name_uz_trgm'),
            GinIndex(fields=['name_ru'], opclasses=['gin_trgm_ops'], name='idx_category_name_ru_trgm'),
            GinIndex(fields=['name_en'], opclasses=['gin_trgm_ops'], name='idx_category_name_en_trgm'),
        ]


class ProductSubCategory(BaseModel):
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код из 1С")
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="product_category",
                                         verbose_name="Категория продукта")
    name = models.CharField(max_length=255, verbose_name="Название")
    image = models.ImageField(upload_to="sub_category", blank=True, null=True, verbose_name="Изображение")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self)

    class Meta:
        verbose_name = "Подкатегория продуктов"
        verbose_name_plural = "Подкатегории продуктов"


class ProductItemCategory(BaseModel):
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код из 1С")
    product_sub_category = models.ForeignKey(ProductSubCategory, on_delete=models.CASCADE,
                                             related_name="product_sub_category",
                                             verbose_name="Подкатегория продукта")
    name = models.CharField(max_length=255, verbose_name="Название")
    image = models.ImageField(upload_to="item_category", blank=True, null=True, verbose_name="Изображение")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self)

    class Meta:
        verbose_name = "Предметная категория продуктов"
        verbose_name_plural = "Предметные категории продуктов"


class ProductUnit(BaseModel):
    unit_code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код единицы измерения")
    name = models.CharField(max_length=50, verbose_name="Краткое название")
    name_full_uz = models.CharField(max_length=255, blank=True, verbose_name="Полное название (узб.)")
    name_full_ru = models.CharField(max_length=255, blank=True, verbose_name="Полное название (рус.)")
    name_full_en = models.CharField(max_length=255, blank=True, verbose_name="Полное название (англ.)")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Единица измерения"
        verbose_name_plural = "Единицы измерения"


class ProductAttribute(BaseModel):
    # Global dictionary of structured product characteristics ("Quvvat", "Rang", ...), attached to item
    # categories; not linked to products yet (they still use the free-form ProductCharacteristics from 1C)
    NUMBER, LIST, TEXT, BOOLEAN = "number", "list", "text", "boolean"
    VALUE_TYPE_CHOICES = (
        (NUMBER, "Число"),
        (LIST, "Список"),
        (TEXT, "Текст"),
        (BOOLEAN, "Да/Нет"),
    )
    item_categories = models.ManyToManyField(ProductItemCategory, through="ProductItemCategoryAttribute",
                                             related_name="attributes", blank=True,
                                             verbose_name="Предметные категории")
    name = models.CharField(max_length=150, verbose_name="Название")
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default=LIST,
                                  verbose_name="Тип значения")
    # only for `number`; the unit belongs to the attribute, products store just the value
    unit = models.CharField(max_length=50, blank=True, verbose_name="Единица измерения")
    is_filterable = models.BooleanField(default=False, verbose_name="Использовать как фильтр")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Атрибут продукта"
        verbose_name_plural = "Атрибуты продуктов"


class ProductAttributeOption(BaseModel):
    # Allowed value of a `list` attribute
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE, related_name="options",
                                  verbose_name="Атрибут")
    value = models.CharField(max_length=150, verbose_name="Значение")
    position = models.IntegerField(default=0, verbose_name="Позиция")

    def __str__(self):
        return self.value

    class Meta:
        verbose_name = "Значение атрибута"
        verbose_name_plural = "Значения атрибутов"
        ordering = ("position", "id")


class ProductItemCategoryAttribute(BaseModel):
    item_category = models.ForeignKey(ProductItemCategory, on_delete=models.CASCADE,
                                      related_name="attribute_links", verbose_name="Предметная категория")
    # PROTECT: an attribute used by a category can't be deleted
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.PROTECT, related_name="category_links",
                                  verbose_name="Атрибут")
    position = models.IntegerField(default=0, verbose_name="Позиция")

    def __str__(self):
        return f"{self.item_category} — {self.attribute}"

    class Meta:
        verbose_name = "Атрибут категории"
        verbose_name_plural = "Атрибуты категорий"
        unique_together = ("item_category", "attribute")
        ordering = ("position", "id")
