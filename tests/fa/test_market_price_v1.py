"""Market Price v1 unit tests — mock adapters only (no live network required)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from fa.market_price import (
    CROSSCHECK_CONFLICT,
    CROSSCHECK_MATCHED,
    CROSSCHECK_SINGLE_SOURCE,
    CROSSCHECK_UNAVAILABLE,
    MarketPriceRecord,
    ProviderPermanentError,
    ProviderQuote,
    ProviderTransientError,
    StooqAdapter,
    YahooAdapter,
    conflict_threshold,
    last_completed_us_session_date,
    resolve_market_price,
    session_close_as_of,
)
from fa.market_price.cache import load_cached, save_cached
from fa.market_price.harness import injection_kwargs_from_record
from fa.stage8.evaluate import evaluate_stage8

_ET = ZoneInfo("America/New_York")


class _MockProvider:
    def __init__(self, name: str, behavior):
        self.name = name
        self.behavior = behavior  # callable(ticker, session_date) -> quote or raises
        self.calls = 0

    def fetch_raw_close(self, ticker: str, session_date: str) -> ProviderQuote:
        self.calls += 1
        return self.behavior(ticker, session_date, self.calls)


def _quote(ticker, session_date, close, source):
    return ProviderQuote(
        ticker=ticker,
        raw_close=close,
        session_date=session_date,
        currency="USD",
        source=source,
        raw_payload={"close": close, "source": source, "session_date": session_date},
    )


def test_conflict_threshold_abs_and_rel():
    # Low price → $0.02 floor
    assert conflict_threshold(10.0) == pytest.approx(0.02)
    # High price → 0.05% dominates (e.g. 1000 * 0.0005 = 0.50)
    assert conflict_threshold(1000.0) == pytest.approx(0.50)
    # Boundary: 40 * 0.0005 = 0.02
    assert conflict_threshold(40.0) == pytest.approx(0.02)
    assert conflict_threshold(40.01) == pytest.approx(40.01 * 0.0005)


def test_session_close_as_of_et():
    assert session_close_as_of("2026-09-30") == "2026-09-30T16:00:00-04:00"


def test_last_completed_session_weekday_heuristic():
    # Wednesday 10:00 ET → prior Tuesday
    now = datetime(2026, 9, 30, 10, 0, tzinfo=_ET)
    assert last_completed_us_session_date(now=now) == "2026-09-29"
    # Wednesday 16:00 ET → today
    now2 = datetime(2026, 9, 30, 16, 0, tzinfo=_ET)
    assert last_completed_us_session_date(now=now2) == "2026-09-30"
    # Saturday → Friday
    now3 = datetime(2026, 10, 3, 12, 0, tzinfo=_ET)
    assert last_completed_us_session_date(now=now3) == "2026-10-02"


def test_matched_both_sources(tmp_path: Path):
    sess = "2026-09-30"
    primary = _MockProvider(
        "yahoo",
        lambda t, s, c: _quote(t, s, 100.0, "yahoo"),
    )
    secondary = _MockProvider(
        "stooq",
        lambda t, s, c: _quote(t, s, 100.01, "stooq"),  # within $0.02 of 100
    )
    rec = resolve_market_price(
        "TEST",
        session_date=sess,
        primary=primary,
        secondary=secondary,
        cache_root=tmp_path,
        use_cache=False,
        persist_cache=True,
    )
    assert rec.crosscheck_status == CROSSCHECK_MATCHED
    assert rec.usable is True
    assert rec.raw_close == pytest.approx(100.0)
    assert rec.price_as_of == "2026-09-30T16:00:00-04:00"
    assert rec.currency == "USD"
    assert rec.raw_response_hash
    assert primary.calls == 1 and secondary.calls == 1
    # cache written
    assert load_cached("TEST", sess, root=tmp_path) is not None


def test_price_source_conflict_suppresses_usable(tmp_path: Path):
    sess = "2026-09-30"
    primary = _MockProvider(
        "yahoo", lambda t, s, c: _quote(t, s, 100.0, "yahoo")
    )
    secondary = _MockProvider(
        "stooq", lambda t, s, c: _quote(t, s, 101.0, "stooq")  # $1 > $0.02
    )
    rec = resolve_market_price(
        "TEST",
        session_date=sess,
        primary=primary,
        secondary=secondary,
        cache_root=tmp_path,
        use_cache=False,
    )
    assert rec.crosscheck_status == CROSSCHECK_CONFLICT
    assert rec.usable is False
    assert rec.raw_close is None
    inj = injection_kwargs_from_record(rec)
    assert inj["market_price"] is None
    assert inj["price_as_of"] is None


def test_conflict_engages_existing_missing_price_path():
    """CONFLICT → no price → Stage 8 UNKNOWN freshness / suppressed / REVIEW|TOO_HARD."""
    periods = [
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "version_id": "v1",
            "period_end": "2024-12-31",
            "reporting_currency": "USD",
            "fields": {
                "operating_cash_flow": 800,
                "capex": 50,
                "cash_and_equivalents": 200.0,
                "total_debt": 1500.0,
                "shares_diluted_weighted": 100.0,
                "shares_outstanding": 99.0,
                "revenue": 5000,
                "net_income": 600,
                "sbc_expense": 40,
                "operating_income": 700,
            },
        }
    ]
    rec = MarketPriceRecord(
        ticker="SYN",
        raw_close=None,
        session_date="2026-09-30",
        price_as_of=None,
        source=None,
        currency="USD",
        fetched_at="2026-10-02T00:00:00+00:00",
        crosscheck_status=CROSSCHECK_CONFLICT,
        raw_response_hash="abc",
        usable=False,
        why="conflict",
    )
    inj = injection_kwargs_from_record(rec)
    report = evaluate_stage8(
        "synthetic_conflict",
        periods,
        market_price=inj["market_price"],
        price_currency=inj["price_currency"],
        price_as_of=inj["price_as_of"],
        price_source=inj["price_source"],
        force_primary="A3",
    )
    assert report.staleness_class == "UNKNOWN"
    assert report.price_sensitive_suppressed is True
    assert report.process_outcome in {"REVIEW_REQUIRED", "TOO_HARD"}


def test_single_source_primary_only(tmp_path: Path):
    sess = "2026-09-30"

    def sec_fail(t, s, c):
        raise ProviderPermanentError("no bar")

    primary = _MockProvider(
        "yahoo", lambda t, s, c: _quote(t, s, 55.5, "yahoo")
    )
    secondary = _MockProvider("stooq", sec_fail)
    rec = resolve_market_price(
        "ABC",
        session_date=sess,
        primary=primary,
        secondary=secondary,
        cache_root=tmp_path,
        use_cache=False,
    )
    assert rec.crosscheck_status == CROSSCHECK_SINGLE_SOURCE
    assert rec.usable is True
    assert rec.raw_close == pytest.approx(55.5)
    assert "yahoo" in (rec.source or "")


def test_single_source_secondary_fallback(tmp_path: Path):
    sess = "2026-09-30"

    def prim_fail(t, s, c):
        raise ProviderPermanentError("yahoo miss")

    primary = _MockProvider("yahoo", prim_fail)
    secondary = _MockProvider(
        "stooq", lambda t, s, c: _quote(t, s, 12.34, "stooq")
    )
    rec = resolve_market_price(
        "XYZ",
        session_date=sess,
        primary=primary,
        secondary=secondary,
        cache_root=tmp_path,
        use_cache=False,
    )
    assert rec.crosscheck_status == CROSSCHECK_SINGLE_SOURCE
    assert rec.usable is True
    assert rec.raw_close == pytest.approx(12.34)
    assert "stooq" in (rec.source or "")


def test_price_unavailable(tmp_path: Path):
    sess = "2026-09-30"

    def fail(t, s, c):
        raise ProviderPermanentError("gone")

    rec = resolve_market_price(
        "NONE",
        session_date=sess,
        primary=_MockProvider("yahoo", fail),
        secondary=_MockProvider("stooq", fail),
        cache_root=tmp_path,
        use_cache=False,
    )
    assert rec.crosscheck_status == CROSSCHECK_UNAVAILABLE
    assert rec.usable is False
    assert rec.raw_close is None


def test_transient_retry_once(tmp_path: Path):
    sess = "2026-09-30"

    def flaky(t, s, calls):
        if calls == 1:
            raise ProviderTransientError("timeout")
        return _quote(t, s, 10.0, "yahoo")

    primary = _MockProvider("yahoo", flaky)
    secondary = _MockProvider(
        "stooq", lambda t, s, c: (_ for _ in ()).throw(ProviderPermanentError("x"))
    )
    rec = resolve_market_price(
        "FLK",
        session_date=sess,
        primary=primary,
        secondary=secondary,
        cache_root=tmp_path,
        use_cache=False,
    )
    assert primary.calls == 2  # initial + 1 retry
    assert rec.primary_retries == 1
    assert rec.crosscheck_status == CROSSCHECK_SINGLE_SOURCE
    assert rec.usable is True


def test_cache_hit_skips_providers(tmp_path: Path):
    sess = "2026-09-30"
    saved = MarketPriceRecord(
        ticker="CACHED",
        raw_close=1.23,
        session_date=sess,
        price_as_of=session_close_as_of(sess),
        source="yahoo_raw_close_independent",
        currency="USD",
        fetched_at="2026-10-01T00:00:00+00:00",
        crosscheck_status=CROSSCHECK_SINGLE_SOURCE,
        raw_response_hash="deadbeef",
        usable=True,
    )
    save_cached(saved, root=tmp_path)

    def boom(t, s, c):
        raise AssertionError("provider should not be called on cache hit")

    rec = resolve_market_price(
        "CACHED",
        session_date=sess,
        primary=_MockProvider("yahoo", boom),
        secondary=_MockProvider("stooq", boom),
        cache_root=tmp_path,
        use_cache=True,
    )
    assert rec.raw_close == pytest.approx(1.23)
    assert rec.crosscheck_status == CROSSCHECK_SINGLE_SOURCE


def test_stooq_adapter_with_injected_csv():
    csv_body = (
        "Date,Open,High,Low,Close,Volume\n"
        "2026-09-29,10,11,9,10.5,1000\n"
        "2026-09-30,10.5,12,10,11.25,2000\n"
    )
    adapter = StooqAdapter(fetcher=lambda url: csv_body)
    q = adapter.fetch_raw_close("DE", "2026-09-30")
    assert q.raw_close == pytest.approx(11.25)
    assert q.session_date == "2026-09-30"
    assert q.source == "stooq"


def test_stooq_missing_session_permanent():
    csv_body = "Date,Open,High,Low,Close,Volume\n2026-09-29,10,11,9,10.5,1000\n"
    adapter = StooqAdapter(fetcher=lambda url: csv_body)
    with pytest.raises(ProviderPermanentError):
        adapter.fetch_raw_close("DE", "2026-09-30")


def test_yahoo_adapter_with_fake_yf():
    import pandas as pd

    class _Hist:
        def __init__(self, df):
            self._df = df
            self.empty = df.empty

        def iterrows(self):
            return self._df.iterrows()

        def __len__(self):
            return len(self._df)

        @property
        def iloc(self):
            return self._df.iloc

        @property
        def index(self):
            return self._df.index

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **kwargs):
            idx = pd.to_datetime(["2026-09-30"]).tz_localize("America/New_York")
            df = pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [105.0],
                    "Low": [99.0],
                    "Close": [102.5],
                    "Volume": [1e6],
                },
                index=idx,
            )
            return _Hist(df)

    class FakeYf:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker(symbol)

    adapter = YahooAdapter(yf_module=FakeYf)
    q = adapter.fetch_raw_close("COST", "2026-09-30")
    assert q.raw_close == pytest.approx(102.5)
    assert q.source == "yahoo"


def test_required_persist_fields(tmp_path: Path):
    sess = "2026-09-30"
    rec = resolve_market_price(
        "DE",
        session_date=sess,
        primary=_MockProvider(
            "yahoo", lambda t, s, c: _quote(t, s, 671.55, "yahoo")
        ),
        secondary=_MockProvider(
            "stooq", lambda t, s, c: _quote(t, s, 671.55, "stooq")
        ),
        cache_root=tmp_path,
        use_cache=False,
    )
    d = rec.to_dict()
    for key in (
        "ticker",
        "raw_close",
        "session_date",
        "price_as_of",
        "source",
        "currency",
        "fetched_at",
        "crosscheck_status",
        "raw_response_hash",
    ):
        assert key in d
        assert d[key] is not None


@pytest.mark.network
@pytest.mark.skip(reason="optional live smoke — enable with --run-network if desired")
def test_live_yahoo_stooq_smoke():
    """Optional live smoke; skipped by default."""
    rec = resolve_market_price("AAPL", use_cache=False, persist_cache=False)
    assert rec.crosscheck_status in {
        CROSSCHECK_MATCHED,
        CROSSCHECK_SINGLE_SOURCE,
        CROSSCHECK_CONFLICT,
        CROSSCHECK_UNAVAILABLE,
    }
