"""resolve_market_price() — Yahoo primary + Stooq cross-check orchestrator (Plan §0.T).

Rules (LOCKED):
- Cache key = ticker + session_date
- Per source: 1 initial + 1 retry on transient only
- Primary fail → fallback secondary
- One valid → SINGLE_SOURCE (usable)
- Both valid → compare; conflict if |Δ| > max($0.02, 0.05% of primary)
- CONFLICT → usable=False (Stage 8 gets no price → existing REVIEW path)
- Neither → PRICE_UNAVAILABLE → usable=False
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cache import load_cached, save_cached
from .session import last_completed_us_session_date, session_close_as_of
from .stooq import StooqAdapter
from .types import (
    CROSSCHECK_CONFLICT,
    CROSSCHECK_MATCHED,
    CROSSCHECK_SINGLE_SOURCE,
    CROSSCHECK_UNAVAILABLE,
    PROVIDER_STOOQ,
    PROVIDER_YAHOO,
    MarketPriceRecord,
    PriceProvider,
    ProviderPermanentError,
    ProviderQuote,
    ProviderTransientError,
    conflict_threshold,
)
from .yahoo import YahooAdapter


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash_payloads(*payloads: Any) -> str:
    blob = json.dumps(payloads, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _fetch_with_retry(
    provider: PriceProvider, ticker: str, session_date: str
) -> tuple[ProviderQuote | None, int, str | None]:
    """Return (quote_or_None, retry_count, error_why). retry_count is 0 or 1."""
    retries = 0
    last_err: str | None = None
    for attempt in range(2):  # initial + 1 retry
        try:
            q = provider.fetch_raw_close(ticker, session_date)
            if q.currency and str(q.currency).upper() != "USD":
                return None, retries, f"{provider.name}: non-USD currency={q.currency}"
            return q, retries, None
        except ProviderPermanentError as e:
            return None, retries, f"{provider.name}: permanent: {e}"
        except ProviderTransientError as e:
            last_err = f"{provider.name}: transient: {e}"
            if attempt == 0:
                retries = 1
                continue
            return None, retries, last_err
        except Exception as e:  # noqa: BLE001 — treat unexpected as transient once
            last_err = f"{provider.name}: unexpected: {e}"
            if attempt == 0:
                retries = 1
                continue
            return None, retries, last_err
    return None, retries, last_err


def resolve_market_price(
    ticker: str,
    *,
    session_date: str | None = None,
    now: datetime | None = None,
    primary: PriceProvider | None = None,
    secondary: PriceProvider | None = None,
    cache_root: Path | None = None,
    use_cache: bool = True,
    persist_cache: bool = True,
) -> MarketPriceRecord:
    """Fetch / cross-check RAW close for latest completed US session (or override)."""
    t = (ticker or "").strip().upper()
    fetched_at = _utc_now_iso()
    sess = session_date or last_completed_us_session_date(now=now)

    if use_cache:
        cached = load_cached(t, sess, root=cache_root)
        if cached is not None:
            return cached

    primary = primary or YahooAdapter()
    secondary = secondary or StooqAdapter()

    pq, p_retries, p_err = _fetch_with_retry(primary, t, sess)
    sq, s_retries, s_err = _fetch_with_retry(secondary, t, sess)

    price_as_of = session_close_as_of(sess)

    if pq is None and sq is None:
        record = MarketPriceRecord(
            ticker=t,
            raw_close=None,
            session_date=sess,
            price_as_of=None,
            source=None,
            currency="USD",
            fetched_at=fetched_at,
            crosscheck_status=CROSSCHECK_UNAVAILABLE,
            raw_response_hash=_hash_payloads({"primary_err": p_err, "secondary_err": s_err}),
            primary_source=getattr(primary, "name", PROVIDER_YAHOO),
            secondary_source=getattr(secondary, "name", PROVIDER_STOOQ),
            primary_retries=p_retries,
            secondary_retries=s_retries,
            why=f"PRICE_UNAVAILABLE; primary={p_err}; secondary={s_err}",
            usable=False,
        )
        if persist_cache:
            save_cached(record, root=cache_root)
        return record

    if pq is not None and sq is None:
        record = MarketPriceRecord(
            ticker=t,
            raw_close=float(pq.raw_close),
            session_date=sess,
            price_as_of=price_as_of,
            source=f"{pq.source}_raw_close_independent",
            currency="USD",
            fetched_at=fetched_at,
            crosscheck_status=CROSSCHECK_SINGLE_SOURCE,
            raw_response_hash=_hash_payloads(pq.raw_payload, {"secondary_err": s_err}),
            primary_close=float(pq.raw_close),
            secondary_close=None,
            primary_source=pq.source,
            secondary_source=getattr(secondary, "name", PROVIDER_STOOQ),
            primary_retries=p_retries,
            secondary_retries=s_retries,
            why=f"SINGLE_SOURCE accepted primary={pq.source}; secondary unavailable: {s_err}",
            usable=True,
        )
        if persist_cache:
            save_cached(record, root=cache_root)
        return record

    if pq is None and sq is not None:
        record = MarketPriceRecord(
            ticker=t,
            raw_close=float(sq.raw_close),
            session_date=sess,
            price_as_of=price_as_of,
            source=f"{sq.source}_raw_close_independent",
            currency="USD",
            fetched_at=fetched_at,
            crosscheck_status=CROSSCHECK_SINGLE_SOURCE,
            raw_response_hash=_hash_payloads({"primary_err": p_err}, sq.raw_payload),
            primary_close=None,
            secondary_close=float(sq.raw_close),
            primary_source=getattr(primary, "name", PROVIDER_YAHOO),
            secondary_source=sq.source,
            primary_retries=p_retries,
            secondary_retries=s_retries,
            why=f"SINGLE_SOURCE accepted secondary={sq.source}; primary unavailable: {p_err}",
            usable=True,
        )
        if persist_cache:
            save_cached(record, root=cache_root)
        return record

    # Both valid — compare (assert same session_date)
    assert pq is not None and sq is not None
    if pq.session_date != sq.session_date:
        record = MarketPriceRecord(
            ticker=t,
            raw_close=None,
            session_date=sess,
            price_as_of=None,
            source=None,
            currency="USD",
            fetched_at=fetched_at,
            crosscheck_status=CROSSCHECK_CONFLICT,
            raw_response_hash=_hash_payloads(pq.raw_payload, sq.raw_payload),
            primary_close=float(pq.raw_close),
            secondary_close=float(sq.raw_close),
            primary_source=pq.source,
            secondary_source=sq.source,
            primary_retries=p_retries,
            secondary_retries=s_retries,
            why=(
                f"PRICE_SOURCE_CONFLICT: session_date mismatch "
                f"primary={pq.session_date} secondary={sq.session_date}"
            ),
            usable=False,
        )
        if persist_cache:
            save_cached(record, root=cache_root)
        return record

    primary_close = float(pq.raw_close)
    secondary_close = float(sq.raw_close)
    abs_delta = abs(primary_close - secondary_close)
    rel_delta = abs_delta / abs(primary_close) if primary_close else None
    thresh = conflict_threshold(primary_close)

    if abs_delta > thresh:
        record = MarketPriceRecord(
            ticker=t,
            raw_close=None,  # suppress price-sensitive valuation
            session_date=sess,
            price_as_of=None,
            source=None,
            currency="USD",
            fetched_at=fetched_at,
            crosscheck_status=CROSSCHECK_CONFLICT,
            raw_response_hash=_hash_payloads(pq.raw_payload, sq.raw_payload),
            primary_close=primary_close,
            secondary_close=secondary_close,
            abs_delta=abs_delta,
            rel_delta=rel_delta,
            primary_source=pq.source,
            secondary_source=sq.source,
            primary_retries=p_retries,
            secondary_retries=s_retries,
            why=(
                f"PRICE_SOURCE_CONFLICT: |Δ|={abs_delta:.6f} > threshold={thresh:.6f} "
                f"(primary={primary_close}, secondary={secondary_close}); "
                f"suppress price-sensitive valuation → REVIEW_REQUIRED path"
            ),
            usable=False,
        )
        if persist_cache:
            save_cached(record, root=cache_root)
        return record

    record = MarketPriceRecord(
        ticker=t,
        raw_close=primary_close,  # primary wins on MATCHED
        session_date=sess,
        price_as_of=price_as_of,
        source=f"{pq.source}+{sq.source}_crosschecked_raw_close",
        currency="USD",
        fetched_at=fetched_at,
        crosscheck_status=CROSSCHECK_MATCHED,
        raw_response_hash=_hash_payloads(pq.raw_payload, sq.raw_payload),
        primary_close=primary_close,
        secondary_close=secondary_close,
        abs_delta=abs_delta,
        rel_delta=rel_delta,
        primary_source=pq.source,
        secondary_source=sq.source,
        primary_retries=p_retries,
        secondary_retries=s_retries,
        why=f"MATCHED within threshold={thresh:.6f}; |Δ|={abs_delta:.6f}",
        usable=True,
    )
    if persist_cache:
        save_cached(record, root=cache_root)
    return record
