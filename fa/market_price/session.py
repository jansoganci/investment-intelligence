"""US equity completed-session helpers for Market Price v1.

Session date: latest **completed** US regular trading session (Mon–Fri regular
hours end 16:00 America/New_York).

Holiday caveat (documented): without exchange_calendars / pandas_market_calendars,
this module uses a **weekday heuristic** only — US market holidays (NYSE closed
weekdays) are NOT excluded. Prefer installing an exchange calendar for production
correctness; callers may pass an explicit ``session_date`` to override.

price_as_of representation: ET regular close, e.g. ``2026-09-30T16:00:00-04:00``
(Stage 8 freshness already accepts this form).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")
_REGULAR_CLOSE = time(16, 0, 0)


def et_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(_ET)
    if now.tzinfo is None:
        return now.replace(tzinfo=_ET)
    return now.astimezone(_ET)


def is_weekday(d: date) -> bool:
    return d.weekday() < 5


def session_close_as_of(session_date: str | date) -> str:
    """ISO timestamp for US regular-session close on session_date (ET offset)."""
    if isinstance(session_date, str):
        d = date.fromisoformat(session_date)
    else:
        d = session_date
    dt = datetime.combine(d, _REGULAR_CLOSE, tzinfo=_ET)
    return dt.isoformat()


def last_completed_us_session_date(now: datetime | None = None) -> str:
    """Return YYYY-MM-DD of the latest completed US regular session (weekday heuristic).

    Rules:
    - During Mon–Fri before 16:00 ET → prior weekday (previous completed session).
    - During/after Mon–Fri 16:00 ET → today's weekday date.
    - Weekend → Friday (walk back).
    - Does **not** skip NYSE holidays (see module docstring).
    """
    et = et_now(now)
    d = et.date()
    # If session still open or pre-open on a weekday, last completed is prior weekday
    if is_weekday(d) and (et.hour, et.minute, et.second) < (16, 0, 0):
        d = d - timedelta(days=1)
    # Walk back to weekday
    while not is_weekday(d):
        d = d - timedelta(days=1)
    return d.isoformat()
