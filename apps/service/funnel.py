"""Product funnel events (BLD-371 / 372): product card views, cart additions and checkout starts of the site and
the app, one row per product (`ProductEvent`), written in the background. Purchases are not recorded: the funnel
report reads them from the orders. Every night the events are summed up per day, product and platform
(`ProductFunnelDaily`, kept forever) and the raw ones older than `EVENT_DAYS` are deleted."""
import io
import logging
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, CharField, Count, DecimalField, F, IntegerField, OuterRef, Q, Subquery, Sum,     Value, When
from django.db.models.functions import Cast, Coalesce, Concat
from django.utils import timezone

from openpyxl import Workbook

from utils.background import run_in_background
from .feed import Viewer
from .models import CartItem, Order, OrderItem, Product, ProductEvent, ProductFunnelDaily, ProductImage
from .models.choices import ORDER_CHANNEL, ORDER_CHANNEL_ANDROID, ORDER_CHANNEL_IOS, ORDER_CHANNEL_SITE

logger = logging.getLogger(__name__)

PLATFORMS = {value for value, _ in ORDER_CHANNEL}
# the same customer / session, product and event within this many seconds = one event (a re-render, a double tap)
REPEAT_SECONDS = 30
EVENT_DAYS = 90
# the nightly run rebuilds this many last days, so a missed night is caught up
REBUILD_DAYS = 3


def is_prefetch(request):
    purpose = f"{request.META.get('HTTP_SEC_PURPOSE', '')} {request.META.get('HTTP_PURPOSE', '')}".lower()
    return "prefetch" in purpose


def platform_of(request):
    """`platform` of the body, else of the query; "" = not sent or unknown."""
    data = request.data if hasattr(request.data, "get") else {}
    value = data.get("platform") or request.query_params.get("platform") or ""
    return value if value in PLATFORMS else ""


def record(request, event_type, product_ids, platform=None):
    """Writes the events in the background. Never breaks the request it is called from."""
    try:
        if not product_ids or is_prefetch(request):
            return
        viewer = Viewer.of(request)
        session_id = viewer.device_id or (viewer.cart_token or "")[:300]
        identity = f"c:{viewer.customer_id}" if viewer.customer_id else (f"s:{session_id}" if session_id else None)
        if identity:
            product_ids = [pid for pid in product_ids
                           if cache.add(f"funnel:{event_type}:{identity}:{pid}", 1, REPEAT_SECONDS)]
            if not product_ids:
                return
        if platform is None:
            platform = platform_of(request)

        from . import tasks
        args = (event_type, list(product_ids), platform, viewer.customer_id, session_id)
        transaction.on_commit(lambda: run_in_background(tasks.record_product_events, *args))
    except Exception as e:
        logger.error("Funnel event not recorded: %s %s: %s", event_type, product_ids, e)


def write_events(event_type, product_ids, platform, customer_id, session_id):
    existing = Product.objects.filter(id__in=product_ids).values_list("id", flat=True)
    ProductEvent.objects.bulk_create([
        ProductEvent(event_type=event_type, product_id=pid, platform=platform or "",
                     customer_id=customer_id, session_id=session_id or "")
        for pid in existing
    ])


def checked_cart_product_ids(request):
    """Products of the checked items of the cart the checkout is made from: the customer's, else the
    `cart_token` cookie's."""
    customer_id = getattr(request.user, "id", None)
    if customer_id:
        items = CartItem.objects.filter(cart__customer_id=customer_id)
    else:
        token = request.COOKIES.get("cart_token")
        if not token:
            return []
        items = CartItem.objects.filter(cart__cart_token=token)
    return list(items.filter(is_checked=True).values_list("product_id", flat=True).distinct())


# ---- daily table ----

def _viewer_identity():
    return Case(
        When(customer_id__isnull=False, then=Concat(Value("c:"), Cast("customer_id", CharField()))),
        When(~Q(session_id=""), then=Concat(Value("s:"), "session_id")),
        default=None, output_field=CharField(),
    )


def build_day(day):
    """Rebuilds the rows of one day from the raw events (safe to run again)."""
    start = datetime.combine(day, time.min)
    rows = (
        ProductEvent.objects.filter(created_at__gte=start, created_at__lt=start + timedelta(days=1))
        .values("product_id", "platform")
        .annotate(
            views=Count("id", filter=Q(event_type=ProductEvent.VIEW)),
            viewers=Count(_viewer_identity(), filter=Q(event_type=ProductEvent.VIEW), distinct=True),
            add_to_cart=Count("id", filter=Q(event_type=ProductEvent.ADD_TO_CART)),
            checkout_start=Count("id", filter=Q(event_type=ProductEvent.CHECKOUT_START)),
        )
    )
    with transaction.atomic():
        ProductFunnelDaily.objects.filter(date=day).delete()
        ProductFunnelDaily.objects.bulk_create([ProductFunnelDaily(date=day, **row) for row in rows],
                                               batch_size=1000)
    return len(rows)


def nightly(days=REBUILD_DAYS, keep_days=EVENT_DAYS):
    """The last `days` days up to yesterday into the daily table, then the raw events older than `keep_days`
    deleted. Returns (rows built, events deleted)."""
    today = timezone.now().date()
    built = sum(build_day(today - timedelta(days=n)) for n in range(days, 0, -1))
    deleted, _ = ProductEvent.objects.filter(
        created_at__lt=datetime.combine(today - timedelta(days=keep_days), time.min)).delete()
    return built, deleted


# ---- report (admin "Savdo" page) ----

ALL, SITE, APP = "all", "site", "app"
CHANNELS = (ALL, SITE, APP)
CHANNEL_PLATFORMS = {ALL: None, SITE: [ORDER_CHANNEL_SITE], APP: [ORDER_CHANNEL_IOS, ORDER_CHANNEL_ANDROID]}
EVENT_COLUMNS = {"views": ProductEvent.VIEW, "add_to_cart": ProductEvent.ADD_TO_CART,
                 "checkout_start": ProductEvent.CHECKOUT_START}


def _count(queryset, aggregate):
    """A correlated per-product number, 0 when there is nothing."""
    return Coalesce(Subquery(queryset.values("product_id").annotate(n=aggregate).values("n")[:1],
                             output_field=IntegerField()), 0)


def report(date_from, date_to, channel=ALL):
    """Products with any event or purchase in the range (Tashkent dates, both inclusive), annotated with the
    columns of the report. Days before yesterday are read from the daily table, yesterday and today (not built
    yet, or still going on) from the raw events. Purchase = a Completed order created in the range (the top
    sales / revenue card rule), counted once per order; `purchases` = orders of the site / the app (of the
    `channel`), `other_purchases` = orders with no channel (made in the admin panel or by an old app version)
    — only for `channel=all`, they have no checkout_start and stay out of `incomplete` / `completion_rate`."""
    platforms = CHANNEL_PLATFORMS[channel]
    raw_from = max(date_from, timezone.now().date() - timedelta(days=1))

    daily = ProductFunnelDaily.objects.filter(date__gte=date_from, date__lte=date_to, date__lt=raw_from)
    raw = ProductEvent.objects.filter(created_at__gte=datetime.combine(raw_from, time.min),
                                      created_at__lt=datetime.combine(date_to + timedelta(days=1), time.min))
    if platforms:
        daily, raw = daily.filter(platform__in=platforms), raw.filter(platform__in=platforms)
    sold = OrderItem.objects.filter(order__status=Order.COMPLETED, order__created_at__date__gte=date_from,
                                    order__created_at__date__lte=date_to)
    own_sold = sold.filter(order__channel__in=platforms or list(PLATFORMS))
    other_sold = sold.filter(order__channel__isnull=True) if channel == ALL else sold.none()

    products = Product.objects.filter(
        Q(id__in=daily.values("product_id")) | Q(id__in=raw.values("product_id"))
        | Q(id__in=own_sold.values("product_id")) | Q(id__in=other_sold.values("product_id")))

    columns = {
        name: _count(daily.filter(product_id=OuterRef("pk")), Sum(name))
        + _count(raw.filter(product_id=OuterRef("pk"), event_type=event_type), Count("id"))
        for name, event_type in EVENT_COLUMNS.items()
    }
    image = ProductImage.objects.filter(product_id=OuterRef("pk")).order_by("position", "id").values("image")[:1]
    return products.annotate(
        **columns,
        purchases=_count(own_sold.filter(product_id=OuterRef("pk")), Count("order_id", distinct=True)),
        other_purchases=_count(other_sold.filter(product_id=OuterRef("pk")), Count("order_id", distinct=True)),
        image_path=Subquery(image),
    ).annotate(
        incomplete=F("checkout_start") - F("purchases"),
        completion_rate=Case(
            When(checkout_start=0, then=None),
            default=Cast(F("purchases") * 100.0 / F("checkout_start"), DecimalField(max_digits=9, decimal_places=1)),
        ),
    )


EXPORT_COLUMNS = (
    # (field, ru header, uz header)
    ("id", "ID", "ID"),
    ("name", "Наименование", "Nomi"),
    ("articul_code", "Артикул", "Artikul"),
    ("views", "Просмотры", "Ko'rishlar"),
    ("add_to_cart", "Добавления в корзину", "Savatga qo'shish"),
    ("checkout_start", "Начали оформление", "Rasmiylashtirishni boshlash"),
    ("purchases", "Покупки", "Xaridlar"),
    ("incomplete", "Не завершили", "Yakunlanmagan"),
    ("completion_rate", "Доля завершённых, %", "Yakunlangan ulushi, %"),
    ("other_purchases", "Покупки без канала (оператор)", "Kanalsiz xaridlar (operator)"),
)


def export_workbook(products, language="ru"):
    """XLSX of the report rows as they are (filters and order applied by the caller, no pagination)."""
    header = 1 if language == "ru" else 2
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Воронка" if language == "ru" else "Voronka")
    sheet.append([column[header] for column in EXPORT_COLUMNS])
    for product in products.iterator(chunk_size=1000):
        name = (product.name_uz or product.name_ru) if language == "uz" else product.name_ru
        values = {"name": name, "completion_rate": None if product.completion_rate is None
                  else float(product.completion_rate)}
        sheet.append([values[field] if field in values else getattr(product, field)
                      for field, *_ in EXPORT_COLUMNS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
