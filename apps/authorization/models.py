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

    class Platform(models.TextChoices):
        """Where a client request came from; the same values as `Order.channel` / the client `?platform=`."""
        SITE = 'site', 'Сайт'
        IOS = 'ios', 'iOS'
        ANDROID = 'android', 'Android'

    class Segment(models.TextChoices):
        """Set by staff by hand (admin panel); nothing computes it."""
        REGULAR = 'regular', 'Обычный'
        BIG = 'big', 'Крупный'
        VIP = 'vip', 'VIP'

    class Language(models.TextChoices):
        UZ = 'uz', 'Узбекский'
        RU = 'ru', 'Русский'

    MAX_TAGS = 20
    MAX_TAG_LENGTH = 50

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
    # null = unknown: customers older than the field, app versions that don't send `platform`
    registration_channel = models.CharField(max_length=10, choices=Platform.choices, blank=True, null=True,
                                            db_index=True, verbose_name="Канал регистрации")
    last_login_platform = models.CharField(max_length=10, choices=Platform.choices, blank=True, null=True,
                                           verbose_name="Платформа последнего входа")
    # language of the client API requests (Accept-Language), kept by record_visit; staff may change it too
    language = models.CharField(max_length=5, choices=Language.choices, default=Language.RU,
                                verbose_name="Язык")
    segment = models.CharField(max_length=20, choices=Segment.choices, blank=True, null=True, db_index=True,
                               verbose_name="Сегмент")
    tags = models.JSONField(default=list, blank=True, verbose_name="Теги")
    # soft delete: the row stays for the orders / admin panel, the customer can't sign in any more and the same
    # phone number gets a new account (every auth lookup filters is_deleted=False)
    is_deleted = models.BooleanField(default=False, db_index=True, verbose_name="Удален")
    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата удаления")
    # tokens issued before this moment are refused (logout from every device, delete)
    tokens_valid_after = models.DateTimeField(blank=True, null=True, verbose_name="Токены действительны после")

    def __str__(self):
        return self.full_name or self.phone_number

    def token_revoked(self, iat):
        """True when a token with this `iat` (epoch seconds) was issued before `tokens_valid_after`."""
        if not self.tokens_valid_after or iat is None:
            return False
        cutoff = self.tokens_valid_after
        if timezone.is_naive(cutoff):  # USE_TZ=False: naive Tashkent time
            cutoff = timezone.make_aware(cutoff)
        return int(iat) < int(cutoff.timestamp())

    def end_sessions(self):
        """Refuses every token issued so far and drops the push tokens of all devices."""
        self.tokens_valid_after = timezone.now()
        self.save(update_fields=["tokens_valid_after", "updated_at"])
        FcmToken.objects.filter(customer=self).delete()

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
        self.end_sessions()

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


class CustomerNote(BaseModel):
    """Internal staff note about a customer (admin API only, never shown to the customer)."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="notes", verbose_name="Клиент")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                               related_name="customer_notes", verbose_name="Автор")
    text = models.TextField(verbose_name="Текст")

    def __str__(self):
        return f"{self.customer_id}: {self.text[:50]}"

    class Meta:
        verbose_name = "Заметка о клиенте"
        verbose_name_plural = "Заметки о клиентах"
        ordering = ("-created_at", "-id")


class CustomerActivity(BaseModel):
    """Customer journal ("Jurnal" in the admin panel): account events written by the client auth views and the
    admin customer API (`apps/authorization/activity.py`). History starts at deploy."""

    class Kind(models.TextChoices):
        REGISTERED = 'registered', 'Аккаунт создан'
        LOGGED_IN = 'logged_in', 'Вход'
        UPDATED = 'updated', 'Профиль изменен'
        BLOCKED = 'blocked', 'Заблокирован'
        UNBLOCKED = 'unblocked', 'Разблокирован'
        ROLE_CHANGED = 'role_changed', 'Роль изменена'
        PHONE_REVEALED = 'phone_revealed', 'Телефон показан'
        LOGGED_OUT_ALL = 'logged_out_all', 'Выход со всех устройств'
        DELETED = 'deleted', 'Аккаунт удален'

    ADMIN = 'admin'
    CHANNEL_CHOICES = (*Customer.Platform.choices, (ADMIN, 'Админ панель'))

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="activities",
                                 verbose_name="Клиент")
    kind = models.CharField(max_length=30, choices=Kind.choices, verbose_name="Событие")
    # admin = staff action; null = client action of an unknown platform
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, blank=True, null=True,
                               verbose_name="Канал")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                              related_name="customer_activities", verbose_name="Сотрудник")
    data = models.JSONField(default=dict, blank=True, verbose_name="Данные")

    def __str__(self):
        return f"{self.customer_id}: {self.kind}"

    class Meta:
        verbose_name = "Событие клиента"
        verbose_name_plural = "Журнал клиентов"
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=["customer", "-created_at"], name="idx_customer_activity")]


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
    # who takes the order at this address; "" = the customer themself (not copied to the order)
    recipient_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Имя получателя")
    recipient_phone = models.CharField(max_length=20, blank=True, default="", verbose_name="Телефон получателя")

    RECIPIENT_FIELDS = ("recipient_name", "recipient_phone")
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
