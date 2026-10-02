"""Lightweight SEC client: ticker→CIK, submissions, companyfacts + cache. Network optional."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from . import config


class SecOfflineError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {"User-Agent": config.SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}


def _cache_path(*parts: str) -> Path:
    config.SEC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return config.SEC_CACHE_DIR.joinpath(*parts)


def _http_get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        # handle gzip transparently if needed
        if raw[:2] == b"\x1f\x8b":
            import gzip

            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def resolve_cik(ticker: str, *, offline: bool | None = None, fixture_map: dict | None = None) -> str | None:
    """Return zero-padded 10-digit CIK or None."""
    ticker = ticker.upper().strip()
    offline = config.FA_OFFLINE if offline is None else offline

    if fixture_map and ticker in fixture_map:
        cik = str(fixture_map[ticker]).zfill(10)
        return cik

    cache = _cache_path("company_tickers.json")
    data = None
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
    elif not offline:
        try:
            data = _http_get_json(config.SEC_TICKERS_URL)
            cache.write_text(json.dumps(data), encoding="utf-8")
            time.sleep(0.1)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise SecOfflineError(f"cannot fetch company_tickers: {e}") from e
    else:
        # fixture fallback for synthetic
        fix = config.SYNTH_COMPANY_DIR / "sec_tickers_stub.json"
        if fix.exists():
            data = json.loads(fix.read_text(encoding="utf-8"))
        else:
            return None

    if not data:
        return None

    # SEC format: {"0": {"cik_str": ..., "ticker": ..., "title": ...}, ...}
    for _, row in data.items() if isinstance(data, dict) else []:
        if isinstance(row, dict) and str(row.get("ticker", "")).upper() == ticker:
            return str(row.get("cik_str", "")).zfill(10)
    if isinstance(data, list):
        for row in data:
            if str(row.get("ticker", "")).upper() == ticker:
                return str(row.get("cik_str", "")).zfill(10)
    return None


def get_submissions(cik: str, *, offline: bool | None = None) -> dict | None:
    cik = str(cik).zfill(10)
    offline = config.FA_OFFLINE if offline is None else offline
    cache = _cache_path("submissions", f"CIK{cik}.json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    fix = config.SYNTH_COMPANY_DIR / "sec_submissions_stub.json"
    if offline:
        if fix.exists() and cik.endswith("9999991"):
            return json.loads(fix.read_text(encoding="utf-8"))
        return None

    url = config.SEC_SUBMISSIONS_URL.format(cik=cik)
    try:
        data = _http_get_json(url)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data), encoding="utf-8")
        time.sleep(0.1)
        return data
    except (urllib.error.URLError, TimeoutError, OSError):
        if fix.exists():
            return json.loads(fix.read_text(encoding="utf-8"))
        return None


def get_companyfacts(cik: str, *, offline: bool | None = None) -> dict | None:
    cik = str(cik).zfill(10)
    offline = config.FA_OFFLINE if offline is None else offline
    cache = _cache_path("companyfacts", f"CIK{cik}.json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    fix = config.SYNTH_COMPANY_DIR / "sec_companyfacts_stub.json"
    if offline:
        if fix.exists() and cik.endswith("9999991"):
            return json.loads(fix.read_text(encoding="utf-8"))
        return None

    url = config.SEC_COMPANYFACTS_URL.format(cik=cik)
    try:
        data = _http_get_json(url)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data), encoding="utf-8")
        time.sleep(0.1)
        return data
    except (urllib.error.URLError, TimeoutError, OSError):
        if fix.exists():
            return json.loads(fix.read_text(encoding="utf-8"))
        return None


def get_filing_document(
    cik: str,
    accession: str,
    primary_document: str,
    *,
    offline: bool | None = None,
) -> Path | None:
    """
    Return path to cached primary filing document (HTML), fetching from SEC archives if needed.
    Offline: only returns if already cached under SEC_CACHE_DIR/filings/.
    """
    offline = config.FA_OFFLINE if offline is None else offline
    cik_n = str(int(str(cik)))  # SEC archives drop leading zeros
    acc_nodash = accession.replace("-", "")
    cache_dir = _cache_path("filings")
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Prefer accession-scoped cache to avoid cross-ticker basename collisions
    # (shared SEC_CACHE_DIR/filings is multi-company).
    dest = cache_dir / f"{accession}_{Path(primary_document).name}"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    # Legacy basename-only cache (pre-scoped) — only if no accession collision risk
    dest_legacy = cache_dir / Path(primary_document).name
    if dest_legacy.exists() and dest_legacy.stat().st_size > 0:
        return dest_legacy

    if offline:
        return None

    url = f"https://www.sec.gov/Archives/edgar/data/{cik_n}/{acc_nodash}/{primary_document}"
    try:
        req = urllib.request.Request(url, headers=_headers())
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            if raw[:2] == b"\x1f\x8b":
                import gzip

                raw = gzip.decompress(raw)
        dest.write_bytes(raw)
        time.sleep(0.15)
        return dest
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
