from django.db import models
from abstract_model.base_model import BaseModel
from authorization.models import Customer
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class Banner(BaseModel):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    image = models.ImageField(upload_to='banner/', verbose_name="Изображение")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"


class Chat(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"


class Messages(BaseModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="chat_messages", verbose_name="Чат")
    message = models.TextField(blank=True, null=True, verbose_name="Сообщение")
    file = models.FileField(upload_to="chat/", blank=True, null=True, verbose_name="Файл")
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


