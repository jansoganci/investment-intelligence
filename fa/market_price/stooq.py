"""Stooq free daily close adapter (secondary / cross-check — Plan §0.T).

Uses Stooq CSV daily download (no SDK). US symbols mapped as ``{ticker}.us``.
Injectable ``fetcher`` callable for tests (no live network required).
"""
from __future__ import annotations

import csv
import io
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .types import (
    PROVIDER_STOOQ,
    ProviderPermanentError,
    ProviderQuote,
    ProviderTransientError,
)

# Stooq US equity daily CSV (ascending by date)
_STOOQ_CSV = "https://stooq.com/q/d/l/?s={symbol}&i=d"


def _default_fetch(url: str, *, timeout: float = 30.0) -> str:
    req = Request(url, headers={"User-Agent": "InvestmentIntelligence/0.1 (research)"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — public Stooq CSV
        return resp.read().decode("utf-8", errors="replace")


class StooqAdapter:
    """Secondary provider: Stooq daily CSV → RAW Close for session_date."""

    name = PROVIDER_STOOQ

    def __init__(
        self,
        *,
        fetcher: Callable[[str], str] | None = None,
        symbol_map: Callable[[str], str] | None = None,
    ):
        self._fetcher = fetcher or _default_fetch
        self._symbol_map = symbol_map or (lambda t: f"{t.strip().lower()}.us")

    def fetch_raw_close(self, ticker: str, session_date: str) -> ProviderQuote:
        t = (ticker or "").strip().upper()
        if not t:
            raise ProviderPermanentError("Empty ticker")
        symbol = self._symbol_map(t)
        url = _STOOQ_CSV.format(symbol=symbol)
        try:
            text = self._fetcher(url)
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            raise ProviderTransientError(f"Stooq transient failure for {t}: {e}") from e
        except ProviderTransientError:
            raise
        except Exception as e:  # noqa: BLE001
            # Allow injected fetcher to raise Permanent directly
            if isinstance(e, ProviderPermanentError):
                raise
            raise ProviderTransientError(f"Stooq fetch failure for {t}: {e}") from e

        if not text or not text.strip():
            raise ProviderPermanentError(f"Stooq: empty CSV for {t}")

        # Stooq sometimes returns HTML error pages
        head = text.lstrip()[:64].lower()
        if head.startswith("<!doctype") or head.startswith("<html"):
            raise ProviderTransientError(f"Stooq: HTML error page for {t}")

        try:
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        except csv.Error as e:
            raise ProviderPermanentError(f"Stooq: CSV parse error for {t}: {e}") from e

        if not rows:
            raise ProviderPermanentError(f"Stooq: no rows for {t}")

        # Column names: Date,Open,High,Low,Close,Volume
        match = None
        for row in rows:
            d = (row.get("Date") or row.get("date") or "").strip()
            if d == session_date:
                match = row
                break
        if match is None:
            raise ProviderPermanentError(
                f"Stooq: no daily bar for {t} on session_date={session_date}"
            )

        try:
            close = float(match.get("Close") or match.get("close") or "")
        except (TypeError, ValueError) as e:
            raise ProviderPermanentError(
                f"Stooq: invalid Close for {t} on {session_date}"
            ) from e

        if close != close or close <= 0:
            raise ProviderPermanentError(f"Stooq: invalid Close={close} for {t}")

        raw_payload: dict[str, Any] = {
            "provider": PROVIDER_STOOQ,
            "ticker": t,
            "symbol": symbol,
            "session_date": session_date,
            "close": close,
            "open": _opt_float(match.get("Open") or match.get("open")),
            "high": _opt_float(match.get("High") or match.get("high")),
            "low": _opt_float(match.get("Low") or match.get("low")),
            "volume": _opt_float(match.get("Volume") or match.get("volume")),
        }
        return ProviderQuote(
            ticker=t,
            raw_close=close,
            session_date=session_date,
            currency="USD",
            source=PROVIDER_STOOQ,
            raw_payload=raw_payload,
        )


def _opt_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
