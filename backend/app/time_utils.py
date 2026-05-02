from __future__ import annotations

from datetime import datetime, timedelta, timezone


APP_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")


def app_now() -> datetime:
    return datetime.now(APP_TIMEZONE)


def as_app_time(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=APP_TIMEZONE)
    return value.astimezone(APP_TIMEZONE)


def app_time_iso(value: datetime | None) -> str | None:
    normalized = as_app_time(value)
    return normalized.isoformat() if normalized else None

