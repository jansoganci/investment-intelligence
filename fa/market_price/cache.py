"""Disk/JSON cache keyed by ticker + session_date (Plan §0.T / MP-D5)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .. import config
from .types import MarketPriceRecord

_DEFAULT_SUBDIR = "market_price"


def default_cache_root() -> Path:
    """Prefer FA_ROOT/market_price; override with FA_MARKET_PRICE_CACHE."""
    env = os.environ.get("FA_MARKET_PRICE_CACHE")
    if env:
        return Path(env).resolve()
    return (config.FA_ROOT / _DEFAULT_SUBDIR).resolve()


def cache_key(ticker: str, session_date: str) -> str:
    t = (ticker or "").strip().upper()
    return f"{t}_{session_date}"


def cache_path(ticker: str, session_date: str, root: Path | None = None) -> Path:
    root = root or default_cache_root()
    return root / f"{cache_key(ticker, session_date)}.json"


def load_cached(
    ticker: str, session_date: str, *, root: Path | None = None
) -> MarketPriceRecord | None:
    path = cache_path(ticker, session_date, root=root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return _from_dict(data)


def save_cached(
    record: MarketPriceRecord, *, root: Path | None = None
) -> Path:
    if not record.session_date:
        raise ValueError("Cannot cache MarketPriceRecord without session_date")
    root = root or default_cache_root()
    root.mkdir(parents=True, exist_ok=True)
    path = cache_path(record.ticker, record.session_date, root=root)
    path.write_text(
        json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _from_dict(data: dict[str, Any]) -> MarketPriceRecord:
    return MarketPriceRecord(
        ticker=str(data.get("ticker") or ""),
        raw_close=data.get("raw_close"),
        session_date=data.get("session_date"),
        price_as_of=data.get("price_as_of"),
        source=data.get("source"),
        currency=str(data.get("currency") or "USD"),
        fetched_at=str(data.get("fetched_at") or ""),
        crosscheck_status=str(data.get("crosscheck_status") or ""),
        raw_response_hash=data.get("raw_response_hash"),
        primary_close=data.get("primary_close"),
        secondary_close=data.get("secondary_close"),
        abs_delta=data.get("abs_delta"),
        rel_delta=data.get("rel_delta"),
        primary_source=data.get("primary_source"),
        secondary_source=data.get("secondary_source"),
        primary_retries=int(data.get("primary_retries") or 0),
        secondary_retries=int(data.get("secondary_retries") or 0),
        why=str(data.get("why") or ""),
        usable=bool(data.get("usable")),
    )
