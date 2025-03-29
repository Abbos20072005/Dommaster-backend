from django.db import models
from abstract_model.base_model import BaseModel
from authorization.models import Customer


class Banner(BaseModel):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    short_description = models.CharField(max_length=255, verbose_name="Краткое описание")
    image = models.ImageField(upload_to='banner/', verbose_name="Изображение")
    link = models.CharField(max_length=150, verbose_name="Линк")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

class Region(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"

class District(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Название")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Область"
        verbose_name_plural = "Областя"

class Chat(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    message = models.TextField(blank=True, null=True, verbose_name="Сообщение")
    is_answer = models.BooleanField(default=False, verbose_name="Ответ")
    is_checked = models.BooleanField(default=True, verbose_name="Просмотрено")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"

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

