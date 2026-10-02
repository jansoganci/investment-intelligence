"""Company folder layout, Source store, Normalized index/versions/CURRENT."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config
from .ids import normalize_ticker, utc_now


def company_dir(ticker: str, root: Path | None = None) -> Path:
    root = root or config.FA_ROOT
    return root / "companies" / normalize_ticker(ticker)


def ensure_company_layout(ticker: str, root: Path | None = None, entity_name: str | None = None) -> Path:
    """Create standard company folder tree; write meta.json if missing."""
    cdir = company_dir(ticker, root)
    for sub in (
        "Source/filings",
        "Source/ir",
        "Source/notes",
        "Normalized/periods",
        "Generated",
        "Thesis",
    ):
        (cdir / sub).mkdir(parents=True, exist_ok=True)

    meta_path = cdir / "meta.json"
    if not meta_path.exists():
        meta = {
            "ticker": normalize_ticker(ticker),
            "entity_name": entity_name,
            "gate0_class": "operating",
            "created_at": utc_now(),
            "stale": False,
            "notes": [],
        }
        write_json(meta_path, meta)

    index_path = cdir / "Normalized" / "index.json"
    if not index_path.exists():
        write_json(index_path, {"periods": []})

    return cdir


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_meta(ticker: str, root: Path | None = None) -> dict:
    p = company_dir(ticker, root) / "meta.json"
    if not p.exists():
        ensure_company_layout(ticker, root)
    return read_json(company_dir(ticker, root) / "meta.json")


def save_meta(ticker: str, meta: dict, root: Path | None = None) -> None:
    write_json(company_dir(ticker, root) / "meta.json", meta)


def source_manifest_path(ticker: str, root: Path | None = None) -> Path:
    return company_dir(ticker, root) / "Source" / "manifest.json"


def load_source_manifest(ticker: str, root: Path | None = None) -> dict:
    p = source_manifest_path(ticker, root)
    if not p.exists():
        return {"sources": []}
    return read_json(p)


def save_source_manifest(ticker: str, manifest: dict, root: Path | None = None) -> None:
    write_json(source_manifest_path(ticker, root), manifest)


def find_source_by_id(ticker: str, source_id: str, root: Path | None = None) -> dict | None:
    man = load_source_manifest(ticker, root)
    for s in man.get("sources", []):
        if s.get("source_id") == source_id:
            return s
    return None


def load_index(ticker: str, root: Path | None = None) -> dict:
    p = company_dir(ticker, root) / "Normalized" / "index.json"
    if not p.exists():
        return {"periods": []}
    return read_json(p)


def save_index(ticker: str, index: dict, root: Path | None = None) -> None:
    write_json(company_dir(ticker, root) / "Normalized" / "index.json", index)


def period_dir(ticker: str, period_key: str, root: Path | None = None) -> Path:
    return company_dir(ticker, root) / "Normalized" / "periods" / period_key


def version_path(ticker: str, period_key: str, version_id: str, root: Path | None = None) -> Path:
    return period_dir(ticker, period_key, root) / f"{version_id}.json"


def current_pointer_path(ticker: str, period_key: str, root: Path | None = None) -> Path:
    return period_dir(ticker, period_key, root) / "CURRENT.json"


def load_current_pointer(ticker: str, period_key: str, root: Path | None = None) -> dict | None:
    p = current_pointer_path(ticker, period_key, root)
    if not p.exists():
        return None
    return read_json(p)


def load_current_period(ticker: str, period_key: str, root: Path | None = None) -> dict | None:
    """Load the version document pointed to by CURRENT.json (pointer semantics)."""
    ptr = load_current_pointer(ticker, period_key, root)
    if not ptr:
        return None
    vid = ptr.get("version_id")
    rel = ptr.get("path") or (f"{vid}.json" if vid else None)
    if not rel:
        return None
    path = period_dir(ticker, period_key, root) / rel
    if not path.exists():
        # fallback absolute-ish
        path = version_path(ticker, period_key, vid, root)
    if not path.exists():
        return None
    return read_json(path)


def list_period_keys(ticker: str, root: Path | None = None) -> list[str]:
    idx = load_index(ticker, root)
    return [p["period_key"] for p in idx.get("periods", [])]


def load_all_current_periods(ticker: str, root: Path | None = None) -> list[dict]:
    out = []
    for pk in list_period_keys(ticker, root):
        doc = load_current_period(ticker, pk, root)
        if doc:
            out.append(doc)
    return out
