"""Stores = `MarketBranch` rows of `PICKUP_BRANCH_TYPES`: weekly schedule, "open now" in Tashkent time,
coordinates check, order snapshot.

Schedule = 7 rows, Monday (0) .. Sunday (6): `{"day", "is_open", "open_time", "close_time"}`, times "HH:MM",
null on a closed day. A store open past midnight is not supported (close must be after open).
"""
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError

TASHKENT = ZoneInfo("Asia/Tashkent")
DAYS = range(7)
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)(:[0-5]\d)?$")

UZ_LATITUDE = (37.1, 45.6)
UZ_LONGITUDE = (55.9, 73.2)


def tashkent_now():
    """Naive Tashkent time, whatever the server clock zone is (the project runs with USE_TZ=False)."""
    return datetime.now(TASHKENT).replace(tzinfo=None)


def check_coordinates(latitude, longitude):
    """{field: message} of the coordinates outside Uzbekistan; empty = fine."""
    errors = {}
    if latitude is not None and not UZ_LATITUDE[0] <= latitude <= UZ_LATITUDE[1]:
        errors["latitude"] = f"The point is outside Uzbekistan: latitude must be {UZ_LATITUDE[0]}..{UZ_LATITUDE[1]}."
    if longitude is not None and not UZ_LONGITUDE[0] <= longitude <= UZ_LONGITUDE[1]:
        errors["longitude"] = (f"The point is outside Uzbekistan: longitude must be "
                               f"{UZ_LONGITUDE[0]}..{UZ_LONGITUDE[1]}.")
    return errors


def _parse_time(value):
    match = TIME_RE.match(value.strip()) if isinstance(value, str) else None
    return time(int(match.group(1)), int(match.group(2))) if match else None


def clean_schedule(value):
    """Validates the 7-day schedule and returns it normalized (sorted by day, "HH:MM", closed day -> nulls).
    Raises ValidationError with a message naming the day."""
    if not isinstance(value, list) or len(value) != 7:
        raise ValidationError("The schedule must have 7 days (day 0 = Monday .. 6 = Sunday).")
    rows = {}
    for row in value:
        if not isinstance(row, dict):
            raise ValidationError("Each schedule day must be an object.")
        day = row.get("day")
        if not isinstance(day, int) or isinstance(day, bool) or day not in DAYS:
            raise ValidationError("`day` must be 0 (Monday) .. 6 (Sunday).")
        if day in rows:
            raise ValidationError(f"Day {day} is repeated.")
        is_open = row.get("is_open")
        if not isinstance(is_open, bool):
            raise ValidationError(f"Day {day}: `is_open` must be true or false.")
        if not is_open:
            rows[day] = {"day": day, "is_open": False, "open_time": None, "close_time": None}
            continue
        open_time, close_time = _parse_time(row.get("open_time")), _parse_time(row.get("close_time"))
        if open_time is None or close_time is None:
            raise ValidationError(f"Day {day}: `open_time` and `close_time` are required in the HH:MM format.")
        if close_time <= open_time:
            raise ValidationError(f"Day {day}: the closing time must be after the opening time.")
        rows[day] = {"day": day, "is_open": True, "open_time": open_time.strftime("%H:%M"),
                     "close_time": close_time.strftime("%H:%M")}
    return [rows[day] for day in DAYS]


def open_state(schedule, now=None):
    """{"is_open_now", "closes_at", "next_open"} at `now` (default: Tashkent time now).
    `closes_at` = "HH:MM" today while open; `next_open` = {"day", "time"} while closed (null = never opens)."""
    now = now or tashkent_now()
    days = {row["day"]: row for row in schedule or [] if isinstance(row, dict)}
    current = now.strftime("%H:%M")
    today = days.get(now.weekday())
    if today and today["is_open"] and today["open_time"] <= current < today["close_time"]:
        return {"is_open_now": True, "closes_at": today["close_time"], "next_open": None}

    next_open = None
    for offset in range(8):
        day = (now.weekday() + offset) % 7
        row = days.get(day)
        if not row or not row["is_open"] or (offset == 0 and row["open_time"] <= current):
            continue
        next_open = {"day": day, "time": row["open_time"],
                     "date": (now + timedelta(days=offset)).date().isoformat()}
        break
    return {"is_open_now": False, "closes_at": None, "next_open": next_open}


def store_snapshot(branch):
    """The store (a `MarketBranch`) as it is now, kept on an order (`Order.pickup_store_snapshot`): later edits
    of the branch - by the admin panel or by 1C - or its deactivation do not change the order."""
    return {
        "id": branch.pk,
        "name_uz": branch.name_uz or "", "name_ru": branch.name_ru or branch.name or "",
        "address_uz": branch.address_uz or "", "address_ru": branch.address_ru or "",
        "landmark_uz": branch.landmark_uz or "", "landmark_ru": branch.landmark_ru or "",
        "phone": branch.phone_number or "",
        "latitude": branch.latitude, "longitude": branch.longitude,
    }


def localized_snapshot(snapshot, language):
    """The order's store snapshot in one language (an empty uz text falls back to ru)."""
    if not snapshot:
        return None

    def text(field):
        return snapshot.get(f"{field}_{language}") or snapshot.get(f"{field}_ru") or ""

    # "address" without a language = a snapshot written before the address became translated
    return {"id": snapshot.get("id"), "name": text("name"),
            "address": text("address") or snapshot.get("address") or "",
            "landmark": text("landmark"), "phone": snapshot.get("phone"),
            "latitude": snapshot.get("latitude"), "longitude": snapshot.get("longitude")}
