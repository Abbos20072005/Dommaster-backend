from django.db import models
from abstract_model.base_model import BaseModel

class Banner(BaseModel):
    title = models.CharField(max_length=255, verbose_name="")
    short_description = models.CharField(max_length=255, verbose_name="")
    image = models.ImageField(upload_to='banner/', verbose_name="")
    link = models.CharField(max_length=150, verbose_name="")

    def __str__(self):
        return str(self.id)

class Region(BaseModel):
    name = models.CharField(max_length=150, verbose_name="")

    def __str__(self):
        return self.name

class District(BaseModel):
    name = models.CharField(max_length=150, verbose_name="")

    def __str__(self):
        return self.name



