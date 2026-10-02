"""Thin Stage 8 injection harness — adapters stay outside analytical modules.

``resolve_and_run_stage8`` fetches via resolve_market_price when no explicit
market_price is provided. Explicit injection always wins (UAT / retest callers
unchanged). On CONFLICT / UNAVAILABLE, passes no usable price so existing
missing-price / REVIEW_REQUIRED path engages — no new valuation math.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import AnalyzeResult
from ..stage8.pipeline import run_stage8
from .resolve import resolve_market_price
from .types import MarketPriceRecord, PriceProvider


def resolve_and_run_stage8(
    ticker: str,
    *,
    root: Path | None = None,
    fa_list_path: Path | None = None,
    semantic_notes_path: Path | None = None,
    require_fa_list: bool = True,
    force_primary: str | None = None,
    ensure_history: bool = True,
    prefer_fy: int = 5,
    prefer_q: int = 8,
    # Explicit injection (wins over fetch when market_price is not None)
    market_price: float | None = None,
    price_currency: str | None = "USD",
    price_as_of: str | None = None,
    price_source: str | None = None,
    price_delay_note: str | None = None,
    post_period_events: list[str] | None = None,
    selective_extend: bool = False,
    # Fetch controls
    fetch_market_price: bool = True,
    session_date: str | None = None,
    now: datetime | None = None,
    primary: PriceProvider | None = None,
    secondary: PriceProvider | None = None,
    cache_root: Path | None = None,
    use_cache: bool = True,
    persist_cache: bool = True,
) -> AnalyzeResult:
    """Run Stage 8 with optional Market Price v1 resolve when price not injected."""
    record: MarketPriceRecord | None = None

    # Explicit injection wins — do not fetch / override
    if market_price is not None:
        result = run_stage8(
            ticker,
            root=root,
            fa_list_path=fa_list_path,
            semantic_notes_path=semantic_notes_path,
            require_fa_list=require_fa_list,
            force_primary=force_primary,
            ensure_history=ensure_history,
            prefer_fy=prefer_fy,
            prefer_q=prefer_q,
            market_price=market_price,
            price_currency=price_currency,
            price_as_of=price_as_of,
            price_source=price_source,
            price_delay_note=price_delay_note,
            post_period_events=post_period_events,
            selective_extend=selective_extend,
        )
        # Attach empty marker that fetch was skipped
        if result.stage8 is not None and hasattr(result.stage8, "calc"):
            metrics = result.stage8.calc.metrics
            metrics["market_price_fetch"] = {
                "skipped": True,
                "reason": "explicit_market_price_injection",
            }
        return result

    if fetch_market_price:
        record = resolve_market_price(
            ticker,
            session_date=session_date,
            now=now,
            primary=primary,
            secondary=secondary,
            cache_root=cache_root,
            use_cache=use_cache,
            persist_cache=persist_cache,
        )
        inj = record.stage8_injection()
        result = run_stage8(
            ticker,
            root=root,
            fa_list_path=fa_list_path,
            semantic_notes_path=semantic_notes_path,
            require_fa_list=require_fa_list,
            force_primary=force_primary,
            ensure_history=ensure_history,
            prefer_fy=prefer_fy,
            prefer_q=prefer_q,
            market_price=inj["market_price"],
            price_currency=inj["price_currency"],
            price_as_of=inj["price_as_of"],
            price_source=inj["price_source"],
            price_delay_note=price_delay_note,
            post_period_events=post_period_events,
            selective_extend=selective_extend,
        )
        if result.stage8 is not None and hasattr(result.stage8, "calc"):
            result.stage8.calc.metrics["market_price_fetch"] = record.to_dict()
        return result

    # No explicit price and fetch disabled → same as legacy missing-price path
    return run_stage8(
        ticker,
        root=root,
        fa_list_path=fa_list_path,
        semantic_notes_path=semantic_notes_path,
        require_fa_list=require_fa_list,
        force_primary=force_primary,
        ensure_history=ensure_history,
        prefer_fy=prefer_fy,
        prefer_q=prefer_q,
        market_price=None,
        price_currency=price_currency,
        price_as_of=price_as_of,
        price_source=price_source,
        price_delay_note=price_delay_note,
        post_period_events=post_period_events,
        selective_extend=selective_extend,
    )


def injection_kwargs_from_record(record: MarketPriceRecord) -> dict[str, Any]:
    """Map a MarketPriceRecord to run_stage8 price kwargs (no fetch)."""
    inj = record.stage8_injection()
    return {
        "market_price": inj["market_price"],
        "price_currency": inj["price_currency"],
        "price_as_of": inj["price_as_of"],
        "price_source": inj["price_source"],
    }
