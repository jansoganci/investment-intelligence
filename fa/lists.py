"""Fundamental Analysis List load/check — refuse analyze if not listed."""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from .models import FAList, FAListEntry


class NotOnFAListError(Exception):
    """Ticker is not on the Fundamental Analysis List."""

    def __init__(self, ticker: str, list_path: Path | None = None):
        self.ticker = ticker
        self.list_path = list_path
        msg = (
            f"{ticker} is not on the Fundamental Analysis List. "
            f"Add it to FA List first before analyze. "
            f"(list={list_path})"
        )
        super().__init__(msg)


def _entry_from_dict(d: dict) -> FAListEntry:
    return FAListEntry(
        ticker=(d.get("ticker") or "").upper(),
        name=d.get("name"),
        synthetic_demo=bool(d.get("synthetic_demo", False)),
        gate0_class=d.get("gate0_class") or "operating",
        notes=d.get("notes"),
    )


def load_fa_list(path: Path | None = None) -> FAList:
    """Load FA list. Prefer explicit path, else FA_USE_FIXTURE_LIST, else FA_ROOT/data/."""
    if path is None:
        if config.FA_USE_FIXTURE_LIST and config.DEMO_FA_LIST.exists():
            path = config.DEMO_FA_LIST
        else:
            path = config.DATA_DIR / config.FA_LIST_FILENAME
            if not path.exists() and config.DEMO_FA_LIST.exists():
                # dry-run convenience: fall back to fixture list if production empty/missing
                path = config.DEMO_FA_LIST

    if not path.exists():
        return FAList(companies=[], note="FA list file missing", updated_at=None)

    raw = json.loads(path.read_text(encoding="utf-8"))
    companies = [_entry_from_dict(c) for c in raw.get("companies", [])]
    return FAList(
        companies=companies,
        updated_at=raw.get("updated_at"),
        note=raw.get("note"),
        synthetic_demo=bool(raw.get("synthetic_demo", False)),
    )


def is_on_fa_list(ticker: str, fa_list: FAList | None = None, path: Path | None = None) -> bool:
    fa_list = fa_list or load_fa_list(path)
    t = ticker.strip().upper()
    return any(e.ticker == t for e in fa_list.companies)


def require_on_fa_list(ticker: str, path: Path | None = None) -> FAListEntry:
    """Raise NotOnFAListError if ticker not listed; return entry if listed."""
    if path is None:
        if config.FA_USE_FIXTURE_LIST and config.DEMO_FA_LIST.exists():
            path = config.DEMO_FA_LIST
        else:
            path = config.DATA_DIR / config.FA_LIST_FILENAME
            if not path.exists() and config.DEMO_FA_LIST.exists():
                path = config.DEMO_FA_LIST

    fa_list = load_fa_list(path)
    t = ticker.strip().upper()
    for e in fa_list.companies:
        if e.ticker == t:
            return e
    raise NotOnFAListError(t, path)


def ensure_empty_production_list() -> Path:
    """Ensure production FA list exists (empty companies) under FA_ROOT/data/."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DATA_DIR / config.FA_LIST_FILENAME
    if not path.exists():
        path.write_text(
            json.dumps(
                {
                    "companies": [],
                    "updated_at": None,
                    "note": "Production FA List — starts empty. Research Coverage ≠ FA List.",
                    "synthetic_demo": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    # Optional stub: research coverage lives under RI — do not merge
    stub = config.DATA_DIR / config.RESEARCH_COVERAGE_STUB
    if not stub.exists():
        stub.write_text(
            json.dumps(
                {
                    "companies": [],
                    "note": (
                        "STUB ONLY. Research Coverage / tracked_companies lives under "
                        "RI (01_Research). Do NOT merge with fundamental_analysis_list.json."
                    ),
                    "updated_at": None,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return path
