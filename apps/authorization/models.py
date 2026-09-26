from django.db import models
from abstract_model.base_model import BaseModel
from apps.authorization.utils import validate_number
import uuid
from django.utils import timezone


class Customer(BaseModel):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        PRORAB = 'prorab', 'Prorab'

    full_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Полное имя")
    phone_number = models.CharField(max_length=14, validators=[validate_number],
                                    verbose_name="Номер телефона")
    email = models.EmailField(blank=True, null=True, verbose_name="Электронная почта")
    password = models.CharField(blank=True, null=True, verbose_name="Пароль")
    verified = models.BooleanField(default=False, verbose_name="Подтвержден")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER, verbose_name="Роль")
    is_blocked = models.BooleanField(default=False, db_index=True, verbose_name="Заблокирован")
    last_login = models.DateTimeField(blank=True, null=True, db_index=True, verbose_name="Последний вход")

    def __str__(self):
        return self.full_name or self.phone_number

    @property
    def is_authenticated(self):
        """Required by DRF throttling to distinguish authenticated vs anonymous users."""
        return True

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"


class CustomerAddresses(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    name = models.CharField(max_length=150, verbose_name="Название")
    location_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название локации")
    latitude = models.FloatField(default=0.0, verbose_name='Широта')
    longitude = models.FloatField(default=0.0, verbose_name='Долгота')
    is_default = models.BooleanField(default=False, verbose_name="Основной")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Адрес клиента"
        verbose_name_plural = "Адрес клиентов"


class FcmToken(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    device_id = models.CharField(max_length=300, verbose_name="ID устройства")
    fcm_token = models.CharField(max_length=300, verbose_name="Фсм Токен")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Фсм Токен"
        verbose_name_plural = "Фсм Токены"


class OTP(BaseModel):
    class Channel(models.TextChoices):
        SMS = 'sms', 'SMS'
        TELEGRAM = 'telegram', 'Telegram'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    resend = models.BooleanField(default=False, verbose_name="Переотправить")
    otp_code = models.IntegerField(verbose_name="ОТП код")
    otp_key = models.CharField(default=uuid.uuid4, max_length=250, editable=False, unique=True, verbose_name="ОТП ключ")
    count_attempts = models.IntegerField(default=0, verbose_name="Количество попыток")
    expire_at = models.DateTimeField(blank=True, null=True, verbose_name="Истекает в")
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.SMS, verbose_name="Канал")

    def __str__(self):
        return self.customer.phone_number

    class Meta:
        verbose_name = "ОТП"
        verbose_name_plural = "ОТП"

class PasswordResetToken(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    token = models.CharField(max_length=250, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()


class TelegramLink(BaseModel):
    """Telegram account <-> phone number binding (phone ownership confirmed by shared contact)."""
    phone_number = models.CharField(max_length=14, unique=True, verbose_name="Номер телефона")
    chat_id = models.BigIntegerField(verbose_name="Chat ID")
    telegram_user_id = models.BigIntegerField(verbose_name="Telegram user ID")
    username = models.CharField(max_length=64, blank=True, default="", verbose_name="Username")
    first_name = models.CharField(max_length=128, blank=True, default="", verbose_name="Имя")

    def __str__(self):
        return f"{self.phone_number} -> {self.chat_id}"

    class Meta:
        verbose_name = "Telegram привязка"
        verbose_name_plural = "Telegram привязки"


class TelegramLinkToken(BaseModel):
    """One-time deep link token (t.me/<bot>?start=<token>); delivers `otp` once the link is confirmed."""
    token = models.CharField(max_length=64, unique=True, verbose_name="Токен")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    otp = models.ForeignKey(OTP, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ОТП")
    chat_id = models.BigIntegerField(null=True, blank=True, verbose_name="Chat ID")
    expires_at = models.DateTimeField(verbose_name="Истекает в")
    is_used = models.BooleanField(default=False, verbose_name="Использован")

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return self.customer.phone_number

    class Meta:
        verbose_name = "Telegram токен привязки"
        verbose_name_plural = "Telegram токены привязки"
