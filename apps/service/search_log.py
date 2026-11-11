"""Searches that found nothing and the "Не нашли — оставьте заявку" requests (catalog search)."""
import io
import logging
from datetime import datetime, time, timedelta

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Max, Min, Q
from openpyxl import Workbook

from apps.service.feed import Viewer
from apps.service.models import NotFoundSearch, SearchRequest
from apps.service.search import normalize
from utils.background import run_in_background

logger = logging.getLogger(__name__)

# a query typed letter by letter: a longer / shorter form of the previous one within this time updates its row
MERGE_SECONDS = 30
# "leave a request" per IP: at most this many in an hour
REQUESTS_PER_HOUR = 5

EXPORT_COLUMNS = (
    ("normalized", "Запрос", "So'rov"),
    ("searches", "Поисков", "Qidiruvlar"),
    ("viewers", "Посетителей", "Tashrifchilar"),
    ("languages", "Языки", "Tillar"),
    ("first_searched_at", "Первый поиск", "Birinchi qidiruv"),
    ("last_searched_at", "Последний поиск", "Oxirgi qidiruv"),
)


def record_not_found(request, query, language, platform=""):
    """A search found nothing. Never breaks the request it is called from."""
    try:
        query = (query or "").strip()[:255]
        normalized = normalize(query)[:255]
        if not normalized:
            return
        viewer = Viewer.of(request)
        session_id = "" if viewer.customer_id else (viewer.device_id or viewer.cart_token or "")[:300]
        values = {"query": query, "normalized": normalized, "language": language, "platform": platform or ""}
        cache_key = f"search:not_found:{viewer.key}" if viewer.identity else None
        previous = cache.get(cache_key) if cache_key else None
        if previous and (normalized.startswith(previous[1]) or previous[1].startswith(normalized)):
            row_id = previous[0]
            NotFoundSearch.objects.filter(pk=row_id).update(**values)
        else:
            row_id = NotFoundSearch.objects.create(customer_id=viewer.customer_id, session_id=session_id,
                                                   **values).id
        if cache_key:
            cache.set(cache_key, (row_id, normalized), timeout=MERGE_SECONDS)
    except Exception:
        logger.exception("search: not found query was not saved")


def report(date_from, date_to, language=None, platform=None):
    """One row per query (normalized) searched in the range with no result."""
    rows = NotFoundSearch.objects.filter(
        created_at__gte=datetime.combine(date_from, time.min),
        created_at__lt=datetime.combine(date_to + timedelta(days=1), time.min),
    )
    if language:
        rows = rows.filter(language=language)
    if platform:
        rows = rows.filter(platform=platform)
    return rows.values("normalized").annotate(
        searches=Count("id"),
        # a row has either a customer or a session id, never both
        viewers=Count("customer_id", distinct=True) + Count("session_id", distinct=True, filter=~Q(session_id="")),
        languages=ArrayAgg("language", distinct=True),
        first_searched_at=Min("created_at"),
        last_searched_at=Max("created_at"),
    )


def export_workbook(rows, language="ru"):
    """XLSX of the report rows as they are (filters and order applied by the caller, no pagination)."""
    header = 1 if language == "ru" else 2
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Не найдено" if language == "ru" else "Topilmadi")
    sheet.append([column[header] for column in EXPORT_COLUMNS])
    for row in rows:
        values = {**row, "languages": ", ".join(sorted(row["languages"]))}
        sheet.append([values[field] for field, *_ in EXPORT_COLUMNS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def request_allowed(ip):
    """False when this IP has already left `REQUESTS_PER_HOUR` requests within the hour."""
    key = f"search:requests:ip:{ip}"
    cache.add(key, 0, timeout=3600)
    try:
        return cache.incr(key) <= REQUESTS_PER_HOUR
    except ValueError:
        return True


def create_request(request, data, language):
    customer = request.user if getattr(request.user, "id", None) else None
    search_request = SearchRequest.objects.create(
        query=data["query"], phone_number=data["phone_number"], company=data.get("company", ""),
        customer=customer, language=language, platform=data.get("platform", ""),
    )
    from apps.service import tasks

    transaction.on_commit(lambda: run_in_background(tasks.send_search_request, search_request.id))
    return search_request


def request_message(search_request):
    """The staff Telegram group text of a new request (ru)."""
    lines = [
        f"🔎 Заявка на товар #{search_request.id}",
        f"Искали: {search_request.query}",
        f"📞 {search_request.phone_number}",
    ]
    if search_request.company:
        lines.append(f"🏢 {search_request.company}")
    customer = search_request.customer
    if customer:
        lines.append(f"👤 {customer.full_name or 'клиент'} (id {customer.id})")
    lines.append(f"🕒 {search_request.created_at:%d.%m.%Y %H:%M}, язык {search_request.language}"
                 + (f", {search_request.platform}" if search_request.platform else ""))
    return "\n".join(lines)


def send_request(request_id):
    from apps.base.telegram import send_staff_alert

    search_request = SearchRequest.objects.select_related("customer").filter(pk=request_id).first()
    if search_request:
        send_staff_alert(request_message(search_request))
