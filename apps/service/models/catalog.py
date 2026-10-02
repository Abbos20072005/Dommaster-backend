from django.contrib.postgres.indexes import GinIndex
from django.db import models

from abstract_model.base_model import BaseModel
from utils.slug import unique_slug


class Brand(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    country = models.CharField(max_length=100, blank=True, verbose_name="Страна")
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


class ProductModel(BaseModel):
    # Model line of a brand ("NXB-63" of Chint); a product picks one of its own brand (Product.product_model).
    # Admin API only, not in client serializers yet
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="product_models", verbose_name="Бренд")
    name = models.CharField(max_length=150, verbose_name="Название")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Модель"
        verbose_name_plural = "Модели"
        unique_together = ("brand", "name")


class CategoryMixin(models.Model):
    # shared by the three category levels; `show_on_site` / `show_in_app` are plain flags, no client logic uses them yet
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="Slug")
    meta_title = models.CharField(max_length=255, blank=True, verbose_name="Meta title")
    meta_description = models.TextField(blank=True, verbose_name="Meta description")
    show_on_site = models.BooleanField(default=True, verbose_name="Показывать на сайте")
    show_in_app = models.BooleanField(default=True, verbose_name="Показывать в приложении")

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # empty slug (1C sync, admin form left blank) -> generated from the name
        if not self.slug:
            self.slug = unique_slug(type(self), self.name_uz or self.name_ru or self.name, exclude_pk=self.pk,
                                    fallback="category")
        super().save(*args, **kwargs)


class ProductCategory(CategoryMixin, BaseModel):
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


class ProductSubCategory(CategoryMixin, BaseModel):
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код из 1С")
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="product_category",
                                         verbose_name="Категория продукта")
    name = models.CharField(max_length=255, verbose_name="Название")
    image = models.ImageField(upload_to="sub_category", blank=True, null=True, verbose_name="Изображение")
    position = models.IntegerField(default=0, verbose_name="Позиция")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self)

    class Meta:
        verbose_name = "Подкатегория продуктов"
        verbose_name_plural = "Подкатегории продуктов"
        ordering = ("position", "id")


class ProductItemCategory(CategoryMixin, BaseModel):
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код из 1С")
    product_sub_category = models.ForeignKey(ProductSubCategory, on_delete=models.CASCADE,
                                             related_name="product_sub_category",
                                             verbose_name="Подкатегория продукта")
    name = models.CharField(max_length=255, verbose_name="Название")
    image = models.ImageField(upload_to="item_category", blank=True, null=True, verbose_name="Изображение")
    position = models.IntegerField(default=0, verbose_name="Позиция")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self)

    class Meta:
        verbose_name = "Предметная категория продуктов"
        verbose_name_plural = "Предметные категории продуктов"
        ordering = ("position", "id")


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
