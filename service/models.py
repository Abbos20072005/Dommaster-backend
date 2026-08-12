from django.db import models
from django.db.models import F, Sum, Case, When, FloatField as DjangoFloatField, Value
from rest_framework.reverse import reverse_lazy

from abstract_model.base_model import BaseModel
from django.core.validators import MinValueValidator, MaxValueValidator
from authorization.models import Customer
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.postgres.indexes import GinIndex
import secrets
from base.models import Promocodes, MarketBranch
from authorization.models import CustomerAddresses

ORDER_STATUS = (
    (0, "Pending"),
    (1, "Collecting"),
    (2, "Delivering"),
    (3, "Completed"),
    (4, "Canceled")
)

PAYMENT_STATUS = (
    (0, "Pending"),
    (1, "Hold"),
    (2, "Paid"),
    (3, "Cancelled"),
)

DELIVERY_TYPE = (
    (0, "Delivery"),
    (1, "Pickup"),
)

PAYMENT_TYPE = (
    (1, "Click"),
    (2, "Payme"),
    (3, "Uzum Bank"),
    (4, "При получении"),
)

CASH_PAYMENT_METHOD = (
    ("cash", "Наличные"),
    ("card", "Карта"),
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


class Order(BaseModel):
    hold_id = models.BigIntegerField(null=True, blank=True)
    promocode = models.ForeignKey(Promocodes, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Промокод")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Покупатель")
    status = models.IntegerField(choices=ORDER_STATUS, default=0, verbose_name="Статус")
    total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость")
    payment_status = models.IntegerField(choices=PAYMENT_STATUS, default=0, verbose_name="Статус оплаты")
    order_location = models.ForeignKey(CustomerAddresses, on_delete=models.SET_NULL, blank=True, null=True,
                                       verbose_name="Локация доставки")
    delivery_type = models.IntegerField(choices=DELIVERY_TYPE, default=0, verbose_name="Тип доставки")
    pickup_branch = models.ForeignKey(MarketBranch, on_delete=models.SET_NULL, blank=True, null=True,
                                      verbose_name="Филиал самовывоза")
    payment_type = models.IntegerField(choices=PAYMENT_TYPE, null=True, blank=True, verbose_name="Тип оплаты")
    payment_method = models.CharField(max_length=10, choices=CASH_PAYMENT_METHOD, blank=True, null=True, verbose_name="Способ оплаты при получении")
    receiver_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Имя получателя")
    receiver_phone = models.CharField(max_length=14, blank=True, null=True, verbose_name="Телефон получателя")
    saved_price = models.FloatField(default=0.0, verbose_name="Сэкономленная сумма")
    products_total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость продуктов")
    ofd_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Ссылка на чек")
    delivery_price = models.DecimalField(max_digits=18, decimal_places=4, default=0.0,
                                         verbose_name="Стоимость доставки")
    yandex_claim_id = models.CharField(max_length=64, blank=True, null=True, verbose_name="ID заявки Яндекс Доставки")
    yandex_claim_status = models.CharField(max_length=50, blank=True, null=True, verbose_name="Статус заявки Яндекс Доставки")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        indexes = [
            models.Index(fields=['customer', 'status'], name='idx_order_cust_status'),
        ]


class ProductCategory(BaseModel):
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Код из 1С")
    name = models.CharField(max_length=255, verbose_name="Название")
    icon = models.ImageField(upload_to="product_category/icon/")
    image = models.ImageField(upload_to="product_category", verbose_name="Изображение")
    position = models.IntegerField(default=0, verbose_name="Позиция")

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from .utils import build_breadcrumbs
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

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from .utils import build_breadcrumbs
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

    def __str__(self):
        return self.name

    def get_breadcrumbs(self):
        from .utils import build_breadcrumbs
        return build_breadcrumbs(self)

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
        from .utils import build_breadcrumbs
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
            GinIndex(fields=['name_en'], opclasses=['gin_trgm_ops'], name='idx_product_name_en_trgm'),
            models.Index(fields=['is_active'], name='idx_product_is_active'),
            models.Index(fields=['brand'], name='idx_product_brand'),
            models.Index(fields=['product_item_category'], name='idx_product_item_cat'),
        ]


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


class Favourites(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Клиент")
    favourite_token = models.CharField(max_length=64, blank=True, null=True, verbose_name="Токен карзины")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")

    def __str__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        if not self.favourite_token:
            self.favourite_token = secrets.token_hex(16)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Избранный"
        verbose_name_plural = "Избранные"
        indexes = [
            models.Index(fields=['customer', 'product'], name='idx_fav_cust_prod'),
            models.Index(fields=['favourite_token'], name='idx_fav_token'),
        ]


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
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items", verbose_name="Заказ")
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
        indexes = [
            models.Index(fields=['product'], name='idx_comment_product'),
        ]


class CommentReply(BaseModel):
    comment = models.ForeignKey(Comment, related_name="comment_reply", on_delete=models.CASCADE,
                                verbose_name="Коментарий")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Клиент")
    reply_comment = models.TextField(verbose_name="Коментарий ответа")
    is_admin = models.BooleanField(default=False, verbose_name="Админ")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Ответ коментария"
        verbose_name_plural = "Ответы коментариям"
        ordering = ("-created_at",)


class CommentImages(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    comment = models.ForeignKey(Comment, related_name="comment_image", on_delete=models.CASCADE,
                                verbose_name="Коментарий")
    image = models.ImageField(upload_to="comment/images/", verbose_name="Изображение")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Изображение комментария"
        verbose_name_plural = "Изображения комментариев"
        ordering = ("-created_at",)


class Service(BaseModel):
    name = models.CharField(max_length=250, verbose_name="Название")
    icon = models.ImageField(upload_to="service/", verbose_name="Иконка")
    description = RichTextUploadingField(verbose_name="Описание")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сервис"
        verbose_name_plural = "Сервисы"


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


class Cart(BaseModel):
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.CASCADE, verbose_name="Клиент")
    cart_token = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Токен карзины")
    total_price = models.FloatField(default=0.0, verbose_name="Общая цена")
    saved_price = models.FloatField(default=0.0, verbose_name="Сэкономленная сумма")
    products_total_price = models.FloatField(default=0.0, verbose_name="Общая стоимость продуктов")

    def total_items(self):
        return self.cart_item.aggregate(total=Sum('quantity'))['total'] or 0

    def calculate_total_price(self):
        agg = self.cart_item.filter(
            is_checked=True, product__isnull=False
        ).aggregate(
            total=Sum(
                Case(
                    When(
                        product__discount_price__isnull=False,
                        then=F('product__discount_price') * F('quantity')
                    ),
                    default=F('product__price') * F('quantity'),
                    output_field=DjangoFloatField()
                )
            ),
            saved=Sum(
                Case(
                    When(
                        product__discount_price__isnull=False,
                        then=(F('product__price') - F('product__discount_price')) * F('quantity')
                    ),
                    default=Value(0.0),
                    output_field=DjangoFloatField()
                )
            ),
            products_total=Sum(
                F('product__price') * F('quantity'),
                output_field=DjangoFloatField()
            )
        )
        self.total_price = agg['total'] or 0.0
        self.saved_price = agg['saved'] or 0.0
        self.products_total_price = agg['products_total'] or 0.0
        return self.total_price, self.saved_price, self.products_total_price

    def save(self, *args, **kwargs):
        if not self.cart_token:
            self.cart_token = secrets.token_hex(16)
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Карзина"
        verbose_name_plural = "Карзины"
        ordering = ("-created_at",)


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, related_name="cart_item", on_delete=models.CASCADE, verbose_name="Карзина")
    product = models.ForeignKey(Product, related_name="cart_product", on_delete=models.SET_NULL, null=True,
                                verbose_name="Продукт")
    quantity = models.IntegerField(default=1, verbose_name="Количество")
    is_checked = models.BooleanField(default=True, verbose_name="Вабран")

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = ("cart", "product")
        verbose_name = "Вещь в корзине"
        verbose_name_plural = "Вещи в корзине"
        ordering = ("-created_at",)


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


class QuestionsReply(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Клиент")
    question = models.ForeignKey(Questions, related_name="question_reply", on_delete=models.CASCADE,
                                 verbose_name="Вопрос")
    answer = models.TextField(verbose_name="Ответ")
    is_admin = models.BooleanField(default=False, verbose_name="Админ")
    is_visible = models.BooleanField(default=False, verbose_name="Виден")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Ответ вопросу"
        verbose_name_plural = "Ответы вопросам"
        ordering = ("-created_at",)


class RecentlyViewedProducts(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recently_viewed_products",
                                verbose_name="Продукт")

    def __str__(self):
        return self.customer.full_name

    class Meta:
        verbose_name = "Недавно просмотренный продукт"
        verbose_name_plural = "Недавно просмотренные продукты"
        ordering = ("-created_at",)


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
