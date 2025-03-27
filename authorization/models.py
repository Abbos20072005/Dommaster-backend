from django.db import models
from abstract_model.base_model import BaseModel
from authorization.utils import validate_number

#TODO: need to hash password
class Customer(BaseModel):
    full_name = models.CharField(max_length=150, verbose_name="Полное имя")
    phone_number = models.CharField(max_length=14, unique=True, validators=[validate_number],
                                    verbose_name="Номер телефона")
    email = models.EmailField(verbose_name="Электронная почта", unique=True)
    password = models.CharField(max_length=30, verbose_name="Пароль")
    login_time = models.DateTimeField(blank=True, null=True, verbose_name="Время входа")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
