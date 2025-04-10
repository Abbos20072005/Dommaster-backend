from django.db import models
from abstract_model.base_model import BaseModel
from authorization.utils import validate_number
import uuid


class Customer(BaseModel):
    full_name = models.CharField(max_length=150, verbose_name="Полное имя")
    phone_number = models.CharField(max_length=14, validators=[validate_number],
                                    verbose_name="Номер телефона")
    email = models.EmailField(verbose_name="Электронная почта")
    password = models.CharField(verbose_name="Пароль")
    verified = models.BooleanField(default=False, verbose_name="Подтвержден")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"


class FcmToken(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    fcm_token = models.CharField(max_length=300, verbose_name="Фсм Токен")
    status = models.BooleanField(default=True, verbose_name="Статус")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Фсм Токен"
        verbose_name_plural = "Фсм Токены"


class OTP(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    resend = models.BooleanField(default=False, verbose_name="Переотправить")
    otp_code = models.IntegerField(verbose_name="ОТП код")
    otp_key = models.CharField(default=uuid.uuid4, max_length=250, editable=False, unique=True, verbose_name="ОТП ключ")
    count_attempts = models.IntegerField(default=0, verbose_name="Количество попыток")
    expire_at = models.DateTimeField(blank=True, null=True, verbose_name="Истекает в")

    def __str__(self):
        return self.customer.phone_number

    class Meta:
        verbose_name = "ОТП"
        verbose_name_plural = "ОТП"

