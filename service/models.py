from django.db import models
from abstract_model.base_model import BaseModel
from django.core.validators import MinValueValidator, MaxValueValidator
from authorization.models import Customer

ORDER_STATUS = (
    (1, "Collecting"),
    (2, "Delivering"),
    (3, "Delivered")
)


class Order(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Покупатель")
    status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name="Статус")
    total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость")

    def __str__(self):
        return str(self.id)


class ProductCategory(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")
    image = models.ImageField(upload_to='product_category', verbose_name="Изображение")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория продуктов"
        verbose_name_plural = "Категории продуктов"


class ProductSubCategory(BaseModel):
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="product_category",
                                         verbose_name="Категория продукта")
    name = models.CharField(max_length=255, verbose_name="Название")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Подкатегория продуктов"
        verbose_name_plural = "Подкатегории продуктов"


class ProductItemCategory(BaseModel):
    product_sub_category = models.ForeignKey(ProductSubCategory, on_delete=models.CASCADE,
                                             related_name="product_sub_category",
                                             verbose_name="Подкатегория продукта")
    name = models.CharField(max_length=255, verbose_name="Название")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Предметная категория продуктов"
        verbose_name_plural = "Предметные категории продуктов"


class Product(BaseModel):
    product_item_category = models.ForeignKey(ProductItemCategory, on_delete=models.CASCADE,
                                              related_name="product_item_category",
                                              verbose_name="Предметная категория продуктов")
    code = models.CharField(max_length=9, verbose_name="Код продукта")
    name = models.CharField(max_length=500, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    price = models.FloatField(default=0, verbose_name="Цена")
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
                               verbose_name="Рейтинг")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    quantity = models.IntegerField(default=0, verbose_name="Количество")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Заказ продукта"
        verbose_name_plural = "Заказы продуктов"


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    image = models.ImageField(upload_to="product_image", verbose_name="Изображение")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Изображение продукта"
        verbose_name_plural = "Изображения продуктов",


class Comment(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    commentator_name = models.CharField(max_length=150, verbose_name="Имя коментатора")
    product_rating = models.IntegerField(default=0, validators=[MinValueValidator(1), MaxValueValidator(5)],
                                         verbose_name="Рейтинг продукта")
    comment = models.TextField(verbose_name="Коментарий")

    def __str__(self):
        return self.commentator_name

    class Meta:
        verbose_name = "Коментарий"
        verbose_name_plural = "Коментарии"


class CommentReply(BaseModel):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, verbose_name="Коментарий")
    defendant_name = models.CharField(max_length=150, verbose_name="Имя ответчика")
    reply = models.TextField(verbose_name="Ответ")

    def __str__(self):
        return self.defendant_name

    class Meta:
        verbose_name = "Ответ коментарию"
        verbose_name_plural = "Ответы коментариям"


class Service(BaseModel):
    name = models.CharField(max_length=250, verbose_name="Название")
    icon = models.ImageField(upload_to="service/", verbose_name="Иконка")
    description = models.TextField(verbose_name="Описание")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"
