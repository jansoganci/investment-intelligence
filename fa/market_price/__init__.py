"""Market Price v1 — Yahoo primary + Stooq secondary (Plan §0.T).

Provider adapters are replaceable and live **outside** Stage 8 analytical
modules (no yfinance/Stooq imports inside fa.stage8.*).

Public API:
- resolve_market_price
- resolve_and_run_stage8
- YahooAdapter / StooqAdapter
- MarketPriceRecord / conflict_threshold
"""
from .harness import injection_kwargs_from_record, resolve_and_run_stage8
from .resolve import resolve_market_price
from .session import last_completed_us_session_date, session_close_as_of
from .stooq import StooqAdapter
from .types import (
    CROSSCHECK_CONFLICT,
    CROSSCHECK_MATCHED,
    CROSSCHECK_SINGLE_SOURCE,
    CROSSCHECK_UNAVAILABLE,
    MarketPriceRecord,
    ProviderPermanentError,
    ProviderQuote,
    ProviderTransientError,
    conflict_threshold,
)
from .yahoo import YahooAdapter

__all__ = [
    "CROSSCHECK_CONFLICT",
    "CROSSCHECK_MATCHED",
    "CROSSCHECK_SINGLE_SOURCE",
    "CROSSCHECK_UNAVAILABLE",
    "MarketPriceRecord",
    "ProviderPermanentError",
    "ProviderQuote",
    "ProviderTransientError",
    "StooqAdapter",
    "YahooAdapter",
    "conflict_threshold",
    "injection_kwargs_from_record",
    "last_completed_us_session_date",
    "resolve_and_run_stage8",
    "resolve_market_price",
    "session_close_as_of",
]
