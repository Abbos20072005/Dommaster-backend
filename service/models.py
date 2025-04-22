from django.db import models
from abstract_model.base_model import BaseModel
from django.core.validators import MinValueValidator, MaxValueValidator
from authorization.models import Customer
from ckeditor.fields import RichTextField
from django.contrib.postgres.indexes import GinIndex
import secrets

ORDER_STATUS = (
    (0, "Pending"),
    (1, "Collecting"),
    (2, "Delivering"),
    (3, "Delivered"),
    (4, "Canceled")
)


class AddsBrands(BaseModel):
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


class Brand(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")
    image = models.ImageField(upload_to="brand/image/", verbose_name="Изображение")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"


class Order(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Покупатель")
    status = models.IntegerField(choices=ORDER_STATUS, default=0, verbose_name="Статус")
    total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"


class ProductCategory(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")
    icon = models.ImageField(upload_to="product_category/icon/")
    image = models.ImageField(upload_to="product_category", verbose_name="Изображение")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория продуктов"
        verbose_name_plural = "Категории продуктов"


class ProductSubCategory(BaseModel):
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="product_category",
                                         verbose_name="Категория продукта")
    name = models.CharField(max_length=255, verbose_name="Название")
    image = models.ImageField(upload_to="sub_category", blank=True, null=True, verbose_name="Изображение")

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
    image = models.ImageField(upload_to="item_category", blank=True, null=True, verbose_name="Изображение")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Предметная категория продуктов"
        verbose_name_plural = "Предметные категории продуктов"


class Tag(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")
    product = models.ManyToManyField(to="Product", blank=True, verbose_name="Продукты")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"


class Sale(BaseModel):
    products = models.ManyToManyField("Product", verbose_name="Продукты")
    name = models.CharField(max_length=150, verbose_name="Название")
    bg_image = models.ImageField(upload_to="sale/", verbose_name="Изображение фона")
    discount_from = models.DateField()
    discount_to = models.DateField()
    is_main = models.BooleanField(default=False, verbose_name="Основной")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Распродажа"
        verbose_name_plural = "Распродажи"


class Product(BaseModel):
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="product_brand",
                              verbose_name="Бренд")
    product_item_category = models.ForeignKey(ProductItemCategory, on_delete=models.CASCADE, blank=True, null=True,
                                              related_name="product_item_category",
                                              verbose_name="Предметная категория продуктов")
    name = models.CharField(max_length=500, verbose_name="Название")
    description = RichTextField(verbose_name="Описание")
    price = models.FloatField(default=0.0, verbose_name="Цена")
    discount_price = models.FloatField(blank=True, null=True, verbose_name="Скидочная цена")
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
                               verbose_name="Рейтинг")
    discount = models.IntegerField(blank=True, null=True, verbose_name="Скидка")
    quantity = models.IntegerField(default=0, verbose_name="Количество")
    comments_quantity = models.IntegerField(default=0, verbose_name="Количество коментариев")

    def __str__(self):
        return self.name

    def update_rating(self):
        from django.db.models import Avg, Count
        agg_data = self.product_comment.aggregate(
            avg_rating=Avg("product_rating"),
            count_comments=Count("id")
        )
        self.rating = round(agg_data["avg_rating"], 1) if agg_data.get("avg_rating") else 0.0
        self.comments_quantity = agg_data["count_comments"] or 0
        self.save()

    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"
        indexes = [
            GinIndex(fields=['name'], opclasses=['gin_trgm_ops'], name='idx_product_name_trgm'),
            GinIndex(fields=['name_uz'], opclasses=['gin_trgm_ops'], name='idx_product_name_uz_trgm'),
            GinIndex(fields=['name_ru'], opclasses=['gin_trgm_ops'], name='idx_product_name_ru_trgm'),
            GinIndex(fields=['name_en'], opclasses=['gin_trgm_ops'], name='idx_product_name_en_trgm'),
        ]


class Favourites(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Клиент")
    favourite_token = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Токен карзины")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")

    def __str__(self):
        return str(self.id)

    def save(self, *args, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.favourite_token:
            self.favourite_token = secrets.token_hex(16)
        return super().save(*args, force_insert=False, force_update=False, using=None, update_fields=None)

    class Meta:
        verbose_name = "Избранный"
        verbose_name_plural = "Избранные"


class Announcements(BaseModel):
    title = models.CharField(max_length=150, verbose_name="Заголовок")
    image = models.ImageField(upload_to="sales/", verbose_name="Изображение")
    description = models.TextField(verbose_name="Описание")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_order_item",
                                verbose_name="Продукт")
    quantity = models.IntegerField(default=0, verbose_name="Количество")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Заказ продукта"
        verbose_name_plural = "Заказы продуктов"


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_image", verbose_name="Продукт")
    image = models.ImageField(upload_to="product_image", verbose_name="Изображение")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Изображение продукта"
        verbose_name_plural = "Изображения продуктов"


class Comment(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_comment",
                                verbose_name="Продукт")
    product_rating = models.IntegerField(default=0, validators=[MinValueValidator(1), MaxValueValidator(5)],
                                         verbose_name="Рейтинг продукта")
    comment = models.TextField(verbose_name="Коментарий")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Коментарий"
        verbose_name_plural = "Коментарии"


class Service(BaseModel):
    name = models.CharField(max_length=250, verbose_name="Название")
    icon = models.ImageField(upload_to="service/", verbose_name="Иконка")
    description = RichTextField(verbose_name="Описание")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"


class ProductCharacteristics(BaseModel):
    product = models.ForeignKey(Product, blank=True, null=True, related_name="product_characteristics",
                                on_delete=models.CASCADE, verbose_name="Продукт")
    name = models.CharField(max_length=150, verbose_name="Название")
    unit = models.CharField(max_length=150, verbose_name="Еденица измерения")
    value = models.CharField(max_length=150, verbose_name="Значение")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Харктеристика продукта"
        verbose_name_plural = "Характеристики продуктов"


class Cart(BaseModel):
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.CASCADE, verbose_name="Клиент")
    cart_token = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Токен карзины")
    total_price = models.FloatField(default=0.0, verbose_name="Общая цена")
    saved_price = models.FloatField(default=0.0, verbose_name="Сэкономленная сумма")
    products_total_price =  models.FloatField(default=0.0, verbose_name="Общая стоимость продуктов")

    def total_items(self):
        return sum(item.quantity for item in self.cart_item.all())

    def calculate_total_price(self):
        total = 0.0
        saved_price_total = 0.0
        products_total_price = 0.0
        for item in self.cart_item.all():
            if item.is_checked is True and item.product and item.product.discount_price:
                total += item.product.discount_price * item.quantity
                saved_price_total += (item.product.price - item.product.discount_price) * item.quantity
                products_total_price += item.product.price * item.quantity
            elif item.is_checked is True and item.product:
                total += item.product.price * item.quantity
                products_total_price += item.product.price * item.quantity


        self.total_price = total
        self.saved_price = saved_price_total
        self.products_total_price = products_total_price
        return self.total_price, self.saved_price, self.products_total_price

    def save(self, *args, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.cart_token:
            self.cart_token = secrets.token_hex(16)
        return super().save(*args, force_insert=False, force_update=False, using=None, update_fields=None)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Карзина"
        verbose_name_plural = "Карзины"


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, related_name="cart_item", on_delete=models.CASCADE, verbose_name="Карзина")
    product = models.ForeignKey(Product, related_name="cart_product", on_delete=models.SET_NULL, null=True,
                                verbose_name="Продукт")
    quantity = models.IntegerField(default=1, verbose_name="Количество")
    is_checked = models.BooleanField(default=True, verbose_name="Вабран")

    def __str__(self):
        return self.product.name

    class Meta:
        unique_together = ("cart", "product")
        verbose_name = "Вещь в корзине"
        verbose_name_plural = "Вещи в корзине"


class Questions(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_question",
                                 verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_question",
                                verbose_name="Продукт")
    question = models.TextField(verbose_name="Вопрос")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return self.product.name

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
