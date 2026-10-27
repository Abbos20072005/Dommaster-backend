from django.conf import settings
from django.db import models
from django.db.models import F
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
    # prorab = PRO customer (projects, expenses); changed only by staff, history in CustomerRoleChange
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER, verbose_name="Роль")
    is_blocked = models.BooleanField(default=False, db_index=True, verbose_name="Заблокирован")
    last_login = models.DateTimeField(blank=True, null=True, db_index=True, verbose_name="Последний вход")
    avatar = models.ImageField(upload_to="customer/avatar/", blank=True, null=True, verbose_name="Фото профиля")

    def __str__(self):
        return self.full_name or self.phone_number

    @property
    def is_authenticated(self):
        """Required by DRF throttling to distinguish authenticated vs anonymous users."""
        return True

    @property
    def is_pro(self):
        return self.role == self.Role.PRORAB

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"


class CustomerVisit(BaseModel):
    """A day the customer used the app / site with their token (any client API request).
    One row per customer × day, written by `apps/authorization/visits.record_visit`; read by the dashboard
    `active_users` chart."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="visits", verbose_name="Клиент")
    day = models.DateField(verbose_name="День")

    def __str__(self):
        return f"{self.customer_id}: {self.day}"

    class Meta:
        verbose_name = "Посещение клиента"
        verbose_name_plural = "Посещения клиентов"
        constraints = [models.UniqueConstraint(fields=["customer", "day"], name="uniq_customer_visit_day")]
        indexes = [models.Index(fields=["day"], name="idx_customer_visit_day")]


class CustomerRoleChange(BaseModel):
    """One change of `Customer.role` by staff (grant / revoke PRO = prorab); revoking needs a reason."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="role_changes",
                                 verbose_name="Клиент")
    old_value = models.CharField(max_length=20, choices=Customer.Role.choices, verbose_name="Было")
    new_value = models.CharField(max_length=20, choices=Customer.Role.choices, verbose_name="Стало")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="customer_role_changes", verbose_name="Изменил")
    reason = models.TextField(blank=True, default="", verbose_name="Причина")

    def __str__(self):
        return f"{self.customer_id}: {self.old_value} -> {self.new_value}"

    class Meta:
        verbose_name = "Изменение роли клиента"
        verbose_name_plural = "Изменения ролей клиентов"
        ordering = ("-created_at", "-id")


class CustomerAddresses(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    name = models.CharField(max_length=150, verbose_name="Название")
    location_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название локации")
    latitude = models.FloatField(default=0.0, verbose_name='Широта')
    longitude = models.FloatField(default=0.0, verbose_name='Долгота')
    is_default = models.BooleanField(default=False, verbose_name="Основной")
    # delivery details; copied to the order when it is placed (DETAIL_FIELDS -> Order fields of the same names)
    apartment = models.CharField(max_length=50, blank=True, default="", verbose_name="Квартира / офис")
    intercom = models.CharField(max_length=50, blank=True, default="", verbose_name="Домофон")
    entrance = models.CharField(max_length=20, blank=True, default="", verbose_name="Подъезд")
    floor = models.CharField(max_length=20, blank=True, default="", verbose_name="Этаж")
    courier_comment = models.CharField(max_length=500, blank=True, default="", verbose_name="Комментарий для курьера")

    DETAIL_FIELDS = ("apartment", "intercom", "entrance", "floor", "courier_comment")

    def details(self):
        """Delivery details for an order snapshot."""
        return {field: getattr(self, field) for field in self.DETAIL_FIELDS}

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Адрес клиента"
        verbose_name_plural = "Адрес клиентов"


class FcmToken(BaseModel):
    IOS, ANDROID = "ios", "android"
    PLATFORM_CHOICES = (
        (IOS, "iOS"),
        (ANDROID, "Android"),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    device_id = models.CharField(max_length=300, verbose_name="ID устройства")
    fcm_token = models.CharField(max_length=300, verbose_name="Фсм Токен")
    # sent by the app together with the token; "" = unknown (a token saved by an older app version)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, blank=True, default="",
                                verbose_name="Платформа")

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


class StaffProfile(BaseModel):
    """Dashboard staff data django `User` has no fields for. One per `is_staff` user (created by a signal).
    Blocked = `user.is_active=False`; access level = `user.is_superuser`."""

    class AccessLevel(models.TextChoices):
        STAFF = 'staff', 'Сотрудник'
        SUPER_ADMIN = 'super_admin', 'Супер админ'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активен'
        BLOCKED = 'blocked', 'Заблокирован'

    class BlockReason(models.TextChoices):
        MANUAL = 'manual', 'Вручную'
        FAILED_ATTEMPTS = 'failed_attempts', 'Неверные попытки входа'

    MAX_FAILED_LOGINS = 5

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile",
                                verbose_name="Пользователь")
    full_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Ф.И.О.")
    position = models.CharField(max_length=150, blank=True, default="", verbose_name="Должность")
    must_change_password = models.BooleanField(default=False, verbose_name="Сменить пароль при первом входе")
    failed_login_attempts = models.PositiveSmallIntegerField(default=0, verbose_name="Неверные попытки входа")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="created_staff", verbose_name="Создал")

    def __str__(self):
        return self.full_name or self.user.get_username()

    @classmethod
    def of(cls, user):
        """Profile of a staff user; creates it for users that got `is_staff` past the signal (queryset.update)."""
        try:
            return user.staff_profile
        except cls.DoesNotExist:
            return cls.objects.create(user=user, full_name=user.get_full_name() or user.get_username())

    @property
    def access_level(self):
        return self.AccessLevel.SUPER_ADMIN if self.user.is_superuser else self.AccessLevel.STAFF

    @property
    def status(self):
        return self.Status.ACTIVE if self.user.is_active else self.Status.BLOCKED

    @property
    def block_reason(self):
        if self.user.is_active:
            return None
        if self.failed_login_attempts >= self.MAX_FAILED_LOGINS:
            return self.BlockReason.FAILED_ATTEMPTS
        return self.BlockReason.MANUAL

    def block(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

    def unblock(self):
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        self.reset_failed_logins()

    def reset_failed_logins(self):
        if self.failed_login_attempts:
            self.failed_login_attempts = 0
            self.save(update_fields=["failed_login_attempts", "updated_at"])

    def register_failed_login(self):
        """Counts a wrong password; returns True when this attempt blocked the account."""
        StaffProfile.objects.filter(pk=self.pk).update(failed_login_attempts=F("failed_login_attempts") + 1)
        self.refresh_from_db(fields=["failed_login_attempts"])
        if self.failed_login_attempts < self.MAX_FAILED_LOGINS:
            return False
        self.block()
        return True

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
