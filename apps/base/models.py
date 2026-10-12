import uuid
from datetime import time, timedelta

from django.db import models
from django.utils import timezone
from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer, FcmToken
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

BRANCH_TYPE_CHOICES = (
    (0, "Showroom"),
    (1, "Market"),
    (2, "Warehouse"),
)


class MarketBranch(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Название")
    code = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="Код склада из 1С")
    location_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название локации")
    address = models.CharField(max_length=500, blank=True, null=True, verbose_name="Адрес")
    branch_type = models.IntegerField(choices=BRANCH_TYPE_CHOICES, default=1, verbose_name="Тип филиала")
    latitude = models.FloatField(blank=True, null=True, verbose_name="Широта")
    longitude = models.FloatField(blank=True, null=True, verbose_name="Долгота")
    working_hours = models.CharField(max_length=255, blank=True, null=True, verbose_name="Рабочее время")
    description = RichTextUploadingField(blank=True, null=True, verbose_name="Описание")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    image = models.ImageField(upload_to="branch/image/", blank=True, null=True, verbose_name="Изображение")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    position = models.IntegerField(default=0, verbose_name="Позиция")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"
        ordering = ("position",)


class Banner(BaseModel):
    # home_top = slider at the top of the home page, one list for the site and the app (the channels
    # `show_on_*` say where a banner is shown); a client gets it when it asks for banners without a placement
    HOME_TOP, HOME_BOTTOM, CATALOG = "home_top", "home_bottom", "catalog"
    PLACEMENT_CHOICES = (
        (HOME_TOP, "Главная · верхний слайдер"),
        (HOME_BOTTOM, "Главная · внизу страницы"),
        (CATALOG, "Внутри каталога"),
    )
    # the top slider used to be two placements: clients may still ask for it by the old names
    PLACEMENT_ALIASES = {"site_home": HOME_TOP, "app_home": HOME_TOP}
    # where a tap leads: category / product / badge / brand -> `content_object`, page -> `page`, url -> `link`
    CATEGORY, PRODUCT, BADGE, BRAND, PAGE, URL = "category", "product", "badge", "brand", "page", "url"
    LINK_TYPE_CHOICES = (
        (CATEGORY, "Категория"),
        (PRODUCT, "Товар"),
        (BADGE, "Тег"),
        (BRAND, "Бренд"),
        (PAGE, "Страница"),
        (URL, "Внешний URL"),
    )
    # not stored: derived from `is_visible` + `starts_at` / `ends_at` (see `status`, `status_q`)
    ACTIVE, SCHEDULED, EXPIRED, ARCHIVED = "active", "scheduled", "expired", "archived"
    STATUS_CHOICES = (
        (ACTIVE, "Активен"),
        (SCHEDULED, "Запланирован"),
        (EXPIRED, "Срок истёк"),
        (ARCHIVED, "Архив"),
    )

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    desktop_image = models.ImageField(upload_to="banner/desktop/", verbose_name="Компютерное изображение")
    mobile_image = models.ImageField(upload_to="banner/mobile/", blank=True, null=True,
                                     verbose_name="Телефонное изображение")
    # False = archived
    is_visible = models.BooleanField(default=True, verbose_name="Виден")
    placement = models.CharField(max_length=20, choices=PLACEMENT_CHOICES, default=HOME_TOP,
                                 verbose_name="Расположение")
    show_on_site = models.BooleanField(default=True, verbose_name="Показывать на сайте")
    show_on_ios = models.BooleanField(default=True, verbose_name="Показывать в iOS")
    show_on_android = models.BooleanField(default=True, verbose_name="Показывать в Android")
    starts_at = models.DateTimeField(default=timezone.now, verbose_name="Начало показа")
    ends_at = models.DateTimeField(blank=True, null=True, verbose_name="Конец показа")
    position = models.PositiveIntegerField(default=0, verbose_name="Позиция")

    link_type = models.CharField(max_length=10, choices=LINK_TYPE_CHOICES, default=URL, verbose_name="Тип ссылки")
    link = models.URLField(blank=True, default="", verbose_name="Линк")
    page = models.CharField(max_length=255, blank=True, default="", verbose_name="Страница",
                            help_text="Внутренний путь, например /pro")
    content_type = models.ForeignKey(ContentType, blank=True, null=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return self.title

    @property
    def code(self):
        return f"BNR-{self.pk:04d}"

    @property
    def status(self):
        now = timezone.now()
        if not self.is_visible:
            return self.ARCHIVED
        if self.starts_at > now:
            return self.SCHEDULED
        if self.ends_at and self.ends_at < now:
            return self.EXPIRED
        return self.ACTIVE

    @classmethod
    def status_q(cls, status):
        """`status` as a queryset filter."""
        now = timezone.now()
        if status == cls.ARCHIVED:
            return models.Q(is_visible=False)
        if status == cls.SCHEDULED:
            return models.Q(is_visible=True, starts_at__gt=now)
        if status == cls.EXPIRED:
            return models.Q(is_visible=True, starts_at__lte=now, ends_at__lt=now)
        return models.Q(is_visible=True, starts_at__lte=now) & (
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now))

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"
        ordering = ("position", "id")


class Chat(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клиент")
    chat_token = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Токен чата")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"


class Messages(BaseModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="chat_messages", verbose_name="Чат")
    message = models.TextField(blank=True, null=True, verbose_name="Сообщение")
    image = models.ImageField(upload_to="chat/", blank=True, null=True, verbose_name="Изображение")
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
    """Notification of the in-app list + its FCM push. Without an audience (`segment` / `platform` =
    all) every customer sees it; a targeted one is seen by the customers it was sent to
    (`NotificationRecipient`). The read state is per customer (`NotificationRead`)."""
    # not stored: derived from `is_active` + `publish_at` (see `status`, `status_q`)
    PUBLISHED, SCHEDULED, DRAFT = "published", "scheduled", "draft"
    STATUS_CHOICES = (
        (PUBLISHED, "Опубликовано"),
        (SCHEDULED, "Запланировано"),
        (DRAFT, "Черновик"),
    )
    # where a tap leads: category / product / badge / banner -> `content_object`, page -> `page`;
    # "" = nowhere, or the free `deeplink`
    CATEGORY, PRODUCT, BADGE, PAGE, BANNER = "category", "product", "badge", "page", "banner"
    LINK_TYPE_CHOICES = (
        (CATEGORY, "Категория"),
        (PRODUCT, "Товар"),
        (BADGE, "Тег"),
        (PAGE, "Страница"),
        (BANNER, "Баннер"),
    )
    # who gets it (see `apps/base/audience.py`)
    SEGMENT_ALL, PRO, TASHKENT, BUYERS_30D, ABANDONED_CART = "all", "pro", "tashkent", "buyers_30d", "abandoned_cart"
    SEGMENT_CHOICES = (
        (SEGMENT_ALL, "Все пользователи"),
        (PRO, "PRO клиенты"),
        (TASHKENT, "Город Ташкент"),
        (BUYERS_30D, "Покупали за последние 30 дней"),
        (ABANDONED_CART, "Бросили корзину"),
    )
    PLATFORM_ALL = "all"
    PLATFORM_CHOICES = ((PLATFORM_ALL, "iOS и Android"), *FcmToken.PLATFORM_CHOICES)
    # `quiet_hours`: nothing goes out between these, the publication moves to QUIET_TO
    QUIET_FROM, QUIET_TO = time(22, 0), time(9, 0)
    DEEPLINK_SCHEME = "buildex://"
    # the three category levels have slugs of their own, so each has its own path
    DEEPLINK_CATEGORY_PATHS = {
        "productcategory": "category",
        "productsubcategory": "sub-category",
        "productitemcategory": "item-category",
    }

    title = models.CharField(max_length=150, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    image = models.ImageField(upload_to="notification/", blank=True, null=True, verbose_name="Изображение")
    link_type = models.CharField(max_length=10, choices=LINK_TYPE_CHOICES, blank=True, default="",
                                 verbose_name="Тип ссылки")
    page = models.CharField(max_length=255, blank=True, default="", verbose_name="Страница",
                            help_text="Внутренний путь, например /pro")
    content_type = models.ForeignKey(ContentType, blank=True, null=True, on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    # built from `link_type` when it is set (see `deeplink_of`), otherwise free text
    deeplink = models.CharField(max_length=255, blank=True, default="", verbose_name="Диплинк",
                                help_text="Экран приложения, например buildex://category/sement")
    segment = models.CharField(max_length=20, choices=SEGMENT_CHOICES, default=SEGMENT_ALL,
                               verbose_name="Сегмент аудитории")
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default=PLATFORM_ALL,
                                verbose_name="Платформа")
    quiet_hours = models.BooleanField(default=False, verbose_name="Тихие часы (22:00–09:00 не отправлять)")
    # False = draft
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    publish_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name="Время публикации")
    # the FCM push goes out once, when the notification becomes published (see `notification_push`)
    push_sent_at = models.DateTimeField(null=True, blank=True, editable=False, verbose_name="Пуш отправлен")
    push_devices = models.PositiveIntegerField(default=0, editable=False,
                                               verbose_name="Устройств, получивших пуш")

    def __str__(self):
        return self.title

    @property
    def status(self):
        if not self.is_active:
            return self.DRAFT
        if self.publish_at > timezone.now():
            return self.SCHEDULED
        return self.PUBLISHED

    @classmethod
    def status_q(cls, status):
        """`status` as a queryset filter."""
        now = timezone.now()
        if status == cls.DRAFT:
            return models.Q(is_active=False)
        if status == cls.SCHEDULED:
            return models.Q(is_active=True, publish_at__gt=now)
        return models.Q(is_active=True, publish_at__lte=now)

    @property
    def is_targeted(self):
        return self.segment != self.SEGMENT_ALL or self.platform != self.PLATFORM_ALL

    @classmethod
    def visible_to(cls, customer):
        """Published notifications of the customer's list: those published before the registration are
        not shown, so a new customer does not start with a pile of old unread ones; a targeted one
        only when the customer was in its audience at the moment it was sent."""
        return cls.objects.filter(
            cls.status_q(cls.PUBLISHED), publish_at__gte=customer.created_at,
        ).filter(
            models.Q(segment=cls.SEGMENT_ALL, platform=cls.PLATFORM_ALL) | models.Q(recipients__customer=customer),
        )

    @classmethod
    def deeplink_of(cls, link_type, target=None, page=""):
        """`buildex://category/sement`, `buildex://product/15`, `buildex://page/pro`; "" without a link."""
        if link_type == cls.PAGE:
            return f"{cls.DEEPLINK_SCHEME}page/{page.lstrip('/')}"
        if not link_type or target is None:
            return ""
        if link_type == cls.CATEGORY:
            return f"{cls.DEEPLINK_SCHEME}{cls.DEEPLINK_CATEGORY_PATHS[target._meta.model_name]}/{target.slug}"
        return f"{cls.DEEPLINK_SCHEME}{link_type}/{target.pk}"

    @classmethod
    def after_quiet_hours(cls, moment):
        """A moment between 22:00 and 09:00 -> the nearest 09:00 after it."""
        if moment.time() >= cls.QUIET_FROM:
            moment += timedelta(days=1)
        elif moment.time() >= cls.QUIET_TO:
            return moment
        return moment.replace(hour=cls.QUIET_TO.hour, minute=cls.QUIET_TO.minute, second=0, microsecond=0)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ("-publish_at", "-id")


class NotificationRecipient(BaseModel):
    """The audience of a targeted notification as it was when the push went out: these customers see
    it in their list (a segment like "bought in the last 30 days" changes every day)."""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="recipients",
                                     verbose_name="Уведомление")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="notifications_received",
                                 verbose_name="Клиент")

    def __str__(self):
        return f"{self.customer_id} - {self.notification_id}"

    class Meta:
        verbose_name = "Получатель уведомления"
        verbose_name_plural = "Получатели уведомлений"
        constraints = [
            models.UniqueConstraint(fields=("notification", "customer"), name="unique_notification_recipient"),
        ]


class NotificationRead(BaseModel):
    """The customer has opened the notification (a row = read)."""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="reads",
                                     verbose_name="Уведомление")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="notification_reads",
                                 verbose_name="Клиент")

    def __str__(self):
        return f"{self.customer_id} - {self.notification_id}"

    class Meta:
        verbose_name = "Прочитанное уведомление"
        verbose_name_plural = "Прочитанные уведомления"
        constraints = [
            models.UniqueConstraint(fields=("notification", "customer"), name="unique_notification_read"),
        ]


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

class DeleteButton(BaseModel):
    is_deleted = models.BooleanField(default=True, verbose_name="Удалено")

    def __str__(self):
        return str(self.id)


class BaseInformation(BaseModel):
    phone_number = models.CharField(max_length=20, verbose_name="Номер телефона")
    additional_phone_number = models.CharField(max_length=20, blank=True, null=True,
                                               verbose_name="Дополнительный номер телефона")
    email = models.EmailField(verbose_name="Электронная почта")
    address = models.CharField(max_length=500, blank=True, null=True, verbose_name="Адрес")
    working_hours = models.CharField(max_length=255, blank=True, null=True, verbose_name="Рабочее время")
    telegram = models.URLField(blank=True, null=True, verbose_name="Telegram")
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram")
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook")
    youtube = models.URLField(blank=True, null=True, verbose_name="YouTube")
    telegram_support = models.URLField(blank=True, null=True, verbose_name="Telegram поддержка")
    google_play_url = models.URLField(blank=True, null=True, verbose_name="Google Play ссылка")
    app_store_url = models.URLField(blank=True, null=True, verbose_name="App Store ссылка")

    def __str__(self):
        return f"Base Information #{self.id}"

    class Meta:
        verbose_name = "Базовая информация"
        verbose_name_plural = "Базовая информация"

