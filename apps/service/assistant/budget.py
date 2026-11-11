"""Gemini spend: the price of every answer is stored on its row (`AssistantMessage.cost_usd`); the month's and
the day's sums switch the assistant off at the budget and warn the staff Telegram group once per level.

Google Cloud's own budget alert is set up in the billing account (devops), this is the backend's counter.
"""
import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from apps.service.models import AssistantMessage
from utils.background import run_in_background

logger = logging.getLogger(__name__)

SPENT_KEY = "assistant:budget:spent"
SPENT_TTL = 60          # the sums are re-read at most once a minute (and after every answer)
ALERT_TTL = 40 * 24 * 3600
MILLION = Decimal(1_000_000)


def cost(input_tokens, output_tokens):
    """USD of one answer at the current prices of GEMINI_MODEL."""
    price = (Decimal(str(settings.GEMINI_INPUT_PRICE_USD)) * input_tokens
             + Decimal(str(settings.GEMINI_OUTPUT_PRICE_USD)) * output_tokens) / MILLION
    return price.quantize(Decimal("0.00000001"))


def _sum(condition):
    return Coalesce(Sum("cost_usd", filter=condition), Value(Decimal(0)), output_field=DecimalField())


def compute_spent():
    today = date.today()
    month_start = today.replace(day=1)
    sums = AssistantMessage.objects.filter(created_at__date__gte=month_start).aggregate(
        month=_sum(Q()), today=_sum(Q(created_at__date=today)))
    spent = {"month": float(sums["month"]), "today": float(sums["today"]), "date": today.isoformat()}
    cache.set(SPENT_KEY, spent, SPENT_TTL)
    return spent


def spent():
    """{"month", "today"} USD of the current month / day."""
    cached = cache.get(SPENT_KEY)
    if cached and cached.get("date") == date.today().isoformat():
        return cached
    return compute_spent()


def exhausted(value=None):
    """'month' / 'day' when that budget is used up, else None."""
    value = value or spent()
    if settings.ASSISTANT_MONTHLY_BUDGET_USD and value["month"] >= settings.ASSISTANT_MONTHLY_BUDGET_USD:
        return "month"
    if settings.ASSISTANT_DAILY_BUDGET_USD and value["today"] >= settings.ASSISTANT_DAILY_BUDGET_USD:
        return "day"
    return None


def after_answer():
    """Re-read the sums after an answer was saved; warn the staff once per level and period."""
    value = compute_spent()
    today = date.today()
    levels = []
    if settings.ASSISTANT_BUDGET_WARNING_USD and value["month"] >= settings.ASSISTANT_BUDGET_WARNING_USD:
        levels.append(("warning", today.strftime("%Y-%m")))
    reached = exhausted(value)
    if reached == "month":
        levels.append(("month", today.strftime("%Y-%m")))
    elif reached == "day":
        levels.append(("day", today.isoformat()))
    for level, period in levels:
        if cache.add(f"assistant:budget:alert:{level}:{period}", 1, ALERT_TTL):
            _alert(level, value)


def alert_text(level, value):
    month, day = value["month"], value["today"]
    if level == "warning":
        return (f"AI ассистент: расход за месяц ${month:.2f} — достигнут порог предупреждения "
                f"${settings.ASSISTANT_BUDGET_WARNING_USD:.2f} (бюджет ${settings.ASSISTANT_MONTHLY_BUDGET_USD:.2f}).")
    if level == "month":
        return (f"AI ассистент отключён до следующего месяца: расход за месяц ${month:.2f} "
                f"(бюджет ${settings.ASSISTANT_MONTHLY_BUDGET_USD:.2f}).")
    return (f"AI ассистент отключён до завтра: расход за день ${day:.2f} "
            f"(дневной бюджет ${settings.ASSISTANT_DAILY_BUDGET_USD:.2f}, за месяц ${month:.2f}).")


def _alert(level, value):
    from apps.service import tasks

    logger.warning("assistant budget level %s reached: %s", level, value)
    text = alert_text(level, value)
    transaction.on_commit(lambda: run_in_background(tasks.send_assistant_budget_alert, text))
