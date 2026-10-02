"""Yahoo Finance daily RAW close adapter via yfinance (primary — Plan §0.T).

Lazy-imports yfinance so Stage 8 analytical modules and CI without the package
still import fa.market_price.types / resolve with injected/mock adapters.
"""
from __future__ import annotations

from typing import Any

from .types import (
    PROVIDER_YAHOO,
    ProviderPermanentError,
    ProviderQuote,
    ProviderTransientError,
)


class YahooAdapter:
    """Primary provider: Yahoo Finance daily OHLC → RAW Close for session_date."""

    name = PROVIDER_YAHOO

    def __init__(self, *, yf_module: Any | None = None):
        self._yf = yf_module  # injectable for tests

    def _client(self) -> Any:
        if self._yf is not None:
            return self._yf
        try:
            import yfinance as yf  # noqa: WPS440 — adapter-local only
        except ImportError as e:
            raise ProviderPermanentError(
                "yfinance not installed — cannot fetch Yahoo daily close"
            ) from e
        return yf

    def fetch_raw_close(self, ticker: str, session_date: str) -> ProviderQuote:
        t = (ticker or "").strip().upper()
        if not t:
            raise ProviderPermanentError("Empty ticker")
        yf = self._client()
        try:
            # Inclusive end: yfinance end is exclusive for some paths; pad +1 day
            from datetime import date, timedelta

            d0 = date.fromisoformat(session_date)
            d1 = d0 + timedelta(days=1)
            hist = yf.Ticker(t).history(
                start=d0.isoformat(),
                end=d1.isoformat(),
                auto_adjust=False,
                actions=False,
            )
        except ProviderPermanentError:
            raise
        except Exception as e:  # noqa: BLE001 — network / Yahoo blips
            raise ProviderTransientError(f"Yahoo transient failure for {t}: {e}") from e

        if hist is None or getattr(hist, "empty", True):
            raise ProviderPermanentError(
                f"Yahoo: no daily bar for {t} on session_date={session_date}"
            )

        # Prefer exact session_date row; else single-row fallback
        row = None
        raw_payload: dict[str, Any]
        try:
            # Index may be tz-aware Timestamp
            for idx, r in hist.iterrows():
                idx_date = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
                if idx_date == session_date:
                    row = r
                    break
            if row is None and len(hist) == 1:
                row = hist.iloc[0]
            if row is None:
                # last row if within request window
                row = hist.iloc[-1]
                idx = hist.index[-1]
                idx_date = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
                if idx_date != session_date:
                    raise ProviderPermanentError(
                        f"Yahoo: bar date {idx_date} != requested session_date {session_date}"
                    )
            close = float(row["Close"])
            raw_payload = {
                "provider": PROVIDER_YAHOO,
                "ticker": t,
                "session_date": session_date,
                "close": close,
                "open": float(row["Open"]) if "Open" in row else None,
                "high": float(row["High"]) if "High" in row else None,
                "low": float(row["Low"]) if "Low" in row else None,
                "volume": float(row["Volume"]) if "Volume" in row else None,
                "auto_adjust": False,
            }
        except ProviderPermanentError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ProviderTransientError(f"Yahoo parse failure for {t}: {e}") from e

        if close != close or close <= 0:  # NaN / non-positive
            raise ProviderPermanentError(f"Yahoo: invalid Close={close} for {t}")

        return ProviderQuote(
            ticker=t,
            raw_close=close,
            session_date=session_date,
            currency="USD",
            source=PROVIDER_YAHOO,
            raw_payload=raw_payload,
        )
