from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
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
    # Card label ("Yangi", "Hit", ...): unlike Tag (M2M) a product has at most one (Product.badge FK)
    name = models.CharField(max_length=100, verbose_name="Название")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Бейдж продукта"
        verbose_name_plural = "Бейджи продуктов"


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
