"""Product funnel events (BLD-371 / 372): product card views, cart additions and checkout starts of the site and
the app, one row per product (`ProductEvent`), written in the background. Purchases are not recorded: the funnel
report reads them from the orders. Every night the events are summed up per day, product and platform
(`ProductFunnelDaily`, kept forever) and the raw ones older than `EVENT_DAYS` are deleted."""
import logging
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, CharField, Count, Q, Value, When
from django.db.models.functions import Cast, Concat
from django.utils import timezone

from utils.background import run_in_background
from .feed import Viewer
from .models import CartItem, Product, ProductEvent, ProductFunnelDaily
from .models.choices import ORDER_CHANNEL

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
