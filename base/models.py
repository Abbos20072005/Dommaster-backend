import uuid

from django.db import models
from abstract_model.base_model import BaseModel
from authorization.models import Customer
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

BRANCH_TYPE_CHOICES = (
    (0, "Showroom"),
    (1, "Market"),
)


class MarketBranch(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Название")
    location_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название локации")
    address = models.CharField(max_length=500, blank=True, null=True, verbose_name="Адрес")
    branch_type = models.IntegerField(choices=BRANCH_TYPE_CHOICES, default=1, verbose_name="Тип филиала")
    latitude = models.FloatField(verbose_name="Широта")
    longitude = models.FloatField(verbose_name="Долгота")
    working_hours = models.CharField(max_length=255, blank=True, null=True, verbose_name="Рабочее время")
    description = RichTextUploadingField(verbose_name="Описание")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    image = models.ImageField(upload_to="branch/image/", blank=True, null=True, verbose_name="Изображение")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    position = models.IntegerField(default=0, verbose_name="Позиция")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"
        ordering = ("position",)


class Banner(BaseModel):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    desktop_image = models.ImageField(upload_to="banner/desktop/", verbose_name="Компютерное изображение")
    mobile_image = models.ImageField(upload_to="banner/mobile/", blank=True, null=True,
                                     verbose_name="Телефонное изображение")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")
    link = models.URLField(verbose_name="Линк")

    content_type = models.ForeignKey(ContentType, blank=True, null=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"


class Chat(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клиент")
    chat_token = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Токен чата")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"


class Messages(BaseModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="chat_messages", verbose_name="Чат")
    message = models.TextField(blank=True, null=True, verbose_name="Сообщение")
    image = models.ImageField(upload_to="chat/", blank=True, null=True, verbose_name="Изображение")
    is_answer = models.BooleanField(default=False, verbose_name="Ответ")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"


class LoyaltyCard(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    full_name = models.CharField(max_length=250, verbose_name="Полное имя")
    card_number = models.IntegerField(default=0, verbose_name="Номер карты")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Карта лояльности"
        verbose_name_plural = "Карты лояльности"


class Notification(BaseModel):
    title = models.CharField(max_length=150, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"


class AboutUs(BaseModel):
    description = RichTextUploadingField(verbose_name="Описание")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "О нас"
        verbose_name_plural = "О нас"


class News(BaseModel):
    title = models.CharField(max_length=450, verbose_name="Заголовок")
    description = RichTextUploadingField(verbose_name="Описание")
    image = models.ImageField(upload_to="news/", verbose_name="Изображение")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"


class Articles(BaseModel):
    title = models.CharField(max_length=450, verbose_name="Заголовок")
    short_description = models.TextField(verbose_name="Краткое описание")
    description = RichTextUploadingField(verbose_name="Описание")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"


class Reviews(BaseModel):
    title = models.CharField(max_length=450, verbose_name="Заголовок")
    short_description = models.TextField(verbose_name="Краткое описание")
    description = RichTextUploadingField(verbose_name="Описание")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Обзор"
        verbose_name_plural = "Обзоры"


class Video(BaseModel):
    url = models.URLField(verbose_name="Cсылка")
    name = models.CharField(max_length=150, verbose_name="Название")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Видео"
        verbose_name_plural = "Видео"


class Promocodes(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    name = models.CharField(max_length=150, verbose_name="Название")
    code = models.CharField(max_length=15, unique=True, verbose_name="Код")
    discount_precent = models.IntegerField(blank=True, null=True, verbose_name="Процент скидки")
    discount_price = models.FloatField(blank=True, null=True, verbose_name="Сумма скидки")
    expires_at = models.DateField(verbose_name="Истекает в")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"

class DeleteButton(BaseModel):
    is_deleted = models.BooleanField(default=True, verbose_name="Удалено")

    def __str__(self):
        return str(self.id)


class BaseInformation(BaseModel):
    phone_number = models.CharField(max_length=20, verbose_name="Номер телефона")
    additional_phone_number = models.CharField(max_length=20, blank=True, null=True,
                                               verbose_name="Дополнительный номер телефона")
    email = models.EmailField(verbose_name="Электронная почта")
    address = models.CharField(max_length=500, blank=True, null=True, verbose_name="Адрес")
    working_hours = models.CharField(max_length=255, blank=True, null=True, verbose_name="Рабочее время")
    telegram = models.URLField(blank=True, null=True, verbose_name="Telegram")
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram")
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook")
    youtube = models.URLField(blank=True, null=True, verbose_name="YouTube")
    telegram_support = models.URLField(blank=True, null=True, verbose_name="Telegram поддержка")
    google_play_url = models.URLField(blank=True, null=True, verbose_name="Google Play ссылка")
    app_store_url = models.URLField(blank=True, null=True, verbose_name="App Store ссылка")

    def __str__(self):
        return f"Base Information #{self.id}"

    class Meta:
        verbose_name = "Базовая информация"
        verbose_name_plural = "Базовая информация"

