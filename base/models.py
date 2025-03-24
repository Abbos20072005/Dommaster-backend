from django.db import models
from abstract_model.base_model import BaseModel

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



