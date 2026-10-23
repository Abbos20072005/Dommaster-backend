from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from abstract_model.base_model import BaseModel
from utils.slug import slug_with_id, unique_slug_for


class SeoFieldsMixin(models.Model):
    """Per-language SEO fields (digital channel only; 1C never sends them).

    `slug` / `meta_title` / `meta_description` are translated (modeltranslation adds the `*_uz` / `*_ru`
    columns). Each `slug_<lang>` is unique within its own column (the base `slug` tracks the default `ru`).
    An empty `slug_<lang>` is generated from `name_<lang>` on save. Stable by default — a later name change
    does NOT move the slug; with `SLUG_FOLLOWS_NAME` (Product) a rename regenerates the slug of every language
    whose slug is still the one generated from the old name (a hand-made slug stays). A changed slug keeps the old one in `SlugHistory` for 301 redirects — categories and
    brands only (`SLUG_HISTORY`), a product's slug carries its id (`SLUG_WITH_ID`) and is not redirected.
    """
    SLUG_FALLBACK = "item"
    # the slug ends with `-<id>` (Product): unique by construction, so no collision query per row
    SLUG_WITH_ID = False
    # keep a changed slug in SlugHistory for the 301 (decision 22.10: categories and brands only)
    SLUG_HISTORY = True
    # a rename regenerates the slug generated from the old name (Product: the id keeps old URLs resolvable)
    SLUG_FOLLOWS_NAME = False

    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, verbose_name="Slug")
    meta_title = models.CharField(max_length=255, blank=True, verbose_name="Meta title")
    meta_description = models.TextField(blank=True, verbose_name="Meta description")

    class Meta:
        abstract = True

    def _slug_source(self, language):
        # the name in `language`, else ru, else the untranslated name
        return (getattr(self, f"name_{language}", None) or getattr(self, "name_ru", None)
                or getattr(self, "name", None))

    def _generated_slug(self, language, source=None):
        """The slug `slug_<lang>` would get from `source` (default: the current name)."""
        field = f"slug_{language}"
        source = self._slug_source(language) if source is None else source
        if self.SLUG_WITH_ID:
            return slug_with_id(type(self), source, self.pk, field=field, fallback=self.SLUG_FALLBACK)
        return unique_slug_for(type(self), source, field=field, exclude_pk=self.pk, fallback=self.SLUG_FALLBACK)

    def follow_name(self, stored):
        """Regenerate the slugs that were generated from the stored name when the name changed.

        `stored` = the row as it is in the db (`name`, `name_<lang>`, `slug_<lang>`); returns the fields it set.
        Only a slug equal to the one the old name gives is moved — a hand-made one is left as it is, and so is
        a slug changed in this very save."""
        moved = []
        for language in settings.MODELTRANSLATION_LANGUAGES:
            field = f"slug_{language}"
            current = getattr(self, field, None)
            if not current or current != stored.get(field):
                continue
            old_source = (stored.get(f"name_{language}") or stored.get("name_ru") or stored.get("name"))
            new_source = self._slug_source(language)
            if old_source == new_source or current != self._generated_slug(language, old_source):
                continue
            value = self._generated_slug(language, new_source)
            if value != current:
                setattr(self, field, value)
                moved.append(field)
        return moved

    def fill_slugs(self):
        """Generate the empty `slug_<lang>` columns; returns the fields it filled."""
        filled = []
        for language in settings.MODELTRANSLATION_LANGUAGES:
            field = f"slug_{language}"
            if getattr(self, field, None):
                continue
            setattr(self, field, self._generated_slug(language))
            filled.append(field)
        return filled

    def save(self, *args, **kwargs):
        languages = settings.MODELTRANSLATION_LANGUAGES
        creating = self.pk is None
        old_slugs = {}
        if not creating and self.SLUG_HISTORY:
            old_slugs = type(self)._default_manager.filter(pk=self.pk).values(
                *(f"slug_{language}" for language in languages)).first() or {}
        update_fields = kwargs.get("update_fields")
        name_fields = {"name", *(f"name_{language}" for language in languages)}
        if (not creating and self.SLUG_FOLLOWS_NAME
                and (update_fields is None or name_fields & set(update_fields))):
            slug_fields = [f"slug_{language}" for language in languages]
            rows = type(self)._default_manager.filter(pk=self.pk)
            # without the rewrite `name` would mean the active language's column
            rows = rows.rewrite(False) if hasattr(rows, "rewrite") else rows
            stored = rows.values(
                *(name_fields & {f.attname for f in self._meta.concrete_fields}), *slug_fields).first()
            moved = self.follow_name(stored) if stored else []
            if moved and update_fields is not None:
                kwargs["update_fields"] = update_fields = list(update_fields) + moved
        # a `-<id>` slug needs the id, so it is generated right after the insert
        if not (creating and self.SLUG_WITH_ID):
            filled = self.fill_slugs()
            if filled and update_fields is not None:
                kwargs["update_fields"] = list(update_fields) + filled
        super().save(*args, **kwargs)
        if creating and self.SLUG_WITH_ID:
            filled = self.fill_slugs()
            if filled:
                super().save(update_fields=filled)
        if old_slugs:
            from apps.service.seo_redirects import record_change
            for language in languages:
                previous = old_slugs.get(f"slug_{language}")
                current = getattr(self, f"slug_{language}", None)
                if previous and current and previous != current:
                    record_change(self, language, previous)


class Brand(SeoFieldsMixin, BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    country = models.CharField(max_length=100, blank=True, verbose_name="Страна")
    image = models.ImageField(upload_to="brand/image/", verbose_name="Изображение")
    image_alt = models.CharField(max_length=255, blank=True, verbose_name="Alt текст изображения")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")
    # picked for the "brands" block of the home page (HomeBlock); the client brand list does not use it yet
    show_on_home = models.BooleanField(default=False, verbose_name="На главной странице")
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


class CategoryMixin(SeoFieldsMixin):
    # shared by the three category levels; `show_on_site` / `show_in_app` are plain flags, no client logic uses them yet
    # slug / meta_title / meta_description / the per-language slug generation come from SeoFieldsMixin
    SLUG_FALLBACK = "category"

    image_alt = models.CharField(max_length=255, blank=True, verbose_name="Alt текст изображения")
    # SEO text under the product list (BLD-251), stored as sent — the format is the front's job
    description = models.TextField(blank=True, verbose_name="Описание (текст под товарами)")
    show_on_site = models.BooleanField(default=True, verbose_name="Показывать на сайте")
    show_in_app = models.BooleanField(default=True, verbose_name="Показывать в приложении")

    class Meta:
        abstract = True


class ProductCategory(CategoryMixin, BaseModel):
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код из 1С")
    name = models.CharField(max_length=255, verbose_name="Название")
    icon = models.ImageField(upload_to="product_category/icon/")
    image = models.ImageField(upload_to="product_category", verbose_name="Изображение")
    position = models.IntegerField(default=0, verbose_name="Позиция")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    def get_breadcrumbs(self, language="ru"):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self, language)

    class Meta:
        verbose_name = "Категория продуктов"
        verbose_name_plural = "Категории продуктов"
        ordering = ("position",)
        indexes = [
            GinIndex(fields=['name'], opclasses=['gin_trgm_ops'], name='idx_category_name_trgm'),
            GinIndex(fields=['name_uz'], opclasses=['gin_trgm_ops'], name='idx_category_name_uz_trgm'),
            GinIndex(fields=['name_ru'], opclasses=['gin_trgm_ops'], name='idx_category_name_ru_trgm'),
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

    def get_breadcrumbs(self, language="ru"):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self, language)

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

    def get_breadcrumbs(self, language="ru"):
        from apps.service.utils import build_breadcrumbs
        return build_breadcrumbs(self, language)

    class Meta:
        verbose_name = "Предметная категория продуктов"
        verbose_name_plural = "Предметные категории продуктов"
        ordering = ("position", "id")


class ProductUnit(BaseModel):
    unit_code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код единицы измерения")
    name = models.CharField(max_length=50, verbose_name="Краткое название")
    name_full_uz = models.CharField(max_length=255, blank=True, verbose_name="Полное название (узб.)")
    name_full_ru = models.CharField(max_length=255, blank=True, verbose_name="Полное название (рус.)")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Единица измерения"
        verbose_name_plural = "Единицы измерения"


class ProductAttribute(BaseModel):
    # Global dictionary of structured product characteristics ("Quvvat", "Rang", ...), attached to item
    # categories; products keep their values in ProductAttributeValue. `is_filterable` = shown as a client filter
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
    # quick filter chips of the category: the most used values of the attribute (0 = all of them)
    is_quick_filter = models.BooleanField(default=False, verbose_name="Быстрый фильтр (чип)")
    max_quick_filters = models.PositiveIntegerField(default=0, verbose_name="Макс. кол-во быстрых фильтров")
    # a product of the category can't pass moderation without a value of it
    is_required = models.BooleanField(default=False, verbose_name="Обязательный")

    def __str__(self):
        return f"{self.item_category} — {self.attribute}"

    class Meta:
        verbose_name = "Атрибут категории"
        verbose_name_plural = "Атрибуты категорий"
        unique_together = ("item_category", "attribute")
        ordering = ("position", "id")
