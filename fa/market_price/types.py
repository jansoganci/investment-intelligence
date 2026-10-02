"""Market Price v1 types + provider Protocol (Plan §0.T / MP-D*).

Provider adapters are replaceable. Stage 8 analytical modules must NOT import
Yahoo/Stooq SDKs — only consume injected market_price / price_as_of / price_source
(or the resolve_market_price() hand-off).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable

# Cross-check status enum (LOCKED MP-D5 / MP-D6)
CROSSCHECK_MATCHED = "MATCHED"
CROSSCHECK_SINGLE_SOURCE = "SINGLE_SOURCE"
CROSSCHECK_CONFLICT = "PRICE_SOURCE_CONFLICT"
CROSSCHECK_UNAVAILABLE = "PRICE_UNAVAILABLE"

# Conflict threshold (LOCKED): max($0.02, 0.05% of primary close)
CONFLICT_ABS_USD = 0.02
CONFLICT_REL = 0.0005  # 0.05%

PROVIDER_YAHOO = "yahoo"
PROVIDER_STOOQ = "stooq"


@dataclass(frozen=True)
class ProviderQuote:
    """Single-source RAW regular-session close quote."""

    ticker: str
    raw_close: float
    session_date: str  # YYYY-MM-DD (US completed session calendar date)
    currency: str
    source: str
    raw_payload: Any = None  # opaque; hashed for persistence
    provider_as_of: str | None = None  # optional provider timestamp hint


@dataclass
class MarketPriceRecord:
    """Persisted / hand-off record (MP-D6)."""

    ticker: str
    raw_close: float | None
    session_date: str | None
    price_as_of: str | None
    source: str | None
    currency: str
    fetched_at: str
    crosscheck_status: str
    raw_response_hash: str | None
    # Optional companion fields (allowed by MP-D6)
    primary_close: float | None = None
    secondary_close: float | None = None
    abs_delta: float | None = None
    rel_delta: float | None = None
    primary_source: str | None = None
    secondary_source: str | None = None
    primary_retries: int = 0
    secondary_retries: int = 0
    why: str = ""
    usable: bool = False  # True only when Stage 8 may inject as market_price

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def stage8_injection(self) -> dict[str, Any]:
        """Fields for run_stage8 kwargs. CONFLICT/UNAVAILABLE → no usable price."""
        if not self.usable or self.raw_close is None:
            return {
                "market_price": None,
                "price_as_of": None,
                "price_source": None,
                "price_currency": self.currency or "USD",
                "market_price_record": self.to_dict(),
            }
        return {
            "market_price": float(self.raw_close),
            "price_as_of": self.price_as_of,
            "price_source": self.source,
            "price_currency": self.currency or "USD",
            "market_price_record": self.to_dict(),
        }


@runtime_checkable
class PriceProvider(Protocol):
    """Replaceable daily-close adapter. Implementations live outside Stage 8 analytics."""

    name: str

    def fetch_raw_close(
        self, ticker: str, session_date: str
    ) -> ProviderQuote:
        """Return RAW close for the given completed US session_date.

        Raise ProviderTransientError for retryable failures.
        Raise ProviderPermanentError / ValueError for non-retryable misses.
        """
        ...


class ProviderTransientError(Exception):
    """Network / rate-limit / temporary provider failure — eligible for 1 retry."""


class ProviderPermanentError(Exception):
    """Missing symbol, bad payload, non-USD, or session not found — no retry."""


def conflict_threshold(primary_close: float) -> float:
    """LOCKED: max($0.02, 0.05% of primary close)."""
    return max(CONFLICT_ABS_USD, abs(primary_close) * CONFLICT_REL)
