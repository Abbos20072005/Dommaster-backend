from django.db import models
from abstract_model.base_model import BaseModel

class Customer(BaseModel):
    full_name = models.CharField(max_length=150, verbose_name="")
    phone_number = models.CharField(max_length=14, verbose_name="", unique=True)
    email = models.EmailField(verbose_name="", unique=True)
    password = models.CharField(max_length=30, verbose_name="")
    login_time = models.DateTimeField(blank=True, null=True, verbose_name="")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = ""
        verbose_name_plural = ""

