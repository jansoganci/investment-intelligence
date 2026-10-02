"""Immutable vNNN versions, CURRENT pointer, supersedes links."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Literal

from . import storage
from .ids import next_version_id, utc_now

ChangeReason = Literal["initial", "amendment", "restatement", "mapping_correction"]


class ImmutableVersionError(Exception):
    pass


def _existing_version_ids(ticker: str, period_key: str, root: Path | None = None) -> list[str]:
    pdir = storage.period_dir(ticker, period_key, root)
    if not pdir.exists():
        return []
    ids = []
    for f in pdir.glob("v*.json"):
        ids.append(f.stem)
    return sorted(ids)


def write_current_pointer(ticker: str, period_key: str, version_id: str, root: Path | None = None) -> None:
    """CURRENT.json is a pointer only: {version_id, path}."""
    ptr = {"version_id": version_id, "path": f"{version_id}.json"}
    storage.write_json(storage.current_pointer_path(ticker, period_key, root), ptr)


def _update_index_entry(
    ticker: str,
    period_key: str,
    version_meta: dict,
    root: Path | None = None,
) -> None:
    index = storage.load_index(ticker, root)
    periods = index.setdefault("periods", [])
    entry = None
    for p in periods:
        if p.get("period_key") == period_key:
            entry = p
            break
    if entry is None:
        entry = {"period_key": period_key, "current_version_id": None, "history": []}
        periods.append(entry)

    hist = entry.setdefault("history", [])
    # update prior history rows if superseded
    for h in hist:
        if h.get("version_id") == version_meta.get("supersedes"):
            h["status"] = "superseded"
            h["superseded_by"] = version_meta.get("version_id")

    # upsert this version in history
    existing_h = None
    for h in hist:
        if h.get("version_id") == version_meta.get("version_id"):
            existing_h = h
            break
    row = {
        "version_id": version_meta.get("version_id"),
        "accepted_at": version_meta.get("accepted_at"),
        "accession": version_meta.get("accession"),
        "status": version_meta.get("status"),
        "superseded_by": version_meta.get("superseded_by"),
        "change_reason": version_meta.get("change_reason"),
        "available_as_of": version_meta.get("available_as_of"),
        "source_id": version_meta.get("source_id"),
    }
    if existing_h:
        existing_h.update(row)
    else:
        hist.append(row)

    if version_meta.get("status") in ("accepted", "draft"):
        # draft may be current during dry-run; accepted preferred
        entry["current_version_id"] = version_meta.get("version_id")

    storage.save_index(ticker, index, root)


def create_initial_version(
    ticker: str,
    period_key: str,
    document: dict[str, Any],
    *,
    accept: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """Write first version for a period as v001. Never overwrites existing files."""
    storage.ensure_company_layout(ticker, root)
    existing = _existing_version_ids(ticker, period_key, root)
    if existing:
        raise ImmutableVersionError(
            f"{period_key} already has versions {existing}; use create_superseding_version"
        )

    doc = copy.deepcopy(document)
    doc["version_id"] = "v001"
    doc["period_key"] = period_key
    doc["ticker"] = ticker.upper()
    doc["change_reason"] = doc.get("change_reason") or "initial"
    doc["supersedes"] = None
    doc["superseded_by"] = None
    if accept:
        doc["status"] = "accepted"
        doc["accepted_at"] = doc.get("accepted_at") or utc_now()
        doc["review_status"] = "accepted"
    else:
        doc["status"] = doc.get("status") or "draft"

    path = storage.version_path(ticker, period_key, "v001", root)
    if path.exists():
        raise ImmutableVersionError(f"refusing to overwrite {path}")
    storage.write_json(path, doc)
    write_current_pointer(ticker, period_key, "v001", root)
    _update_index_entry(ticker, period_key, doc, root)
    return doc


def create_superseding_version(
    ticker: str,
    period_key: str,
    document: dict[str, Any],
    *,
    change_reason: ChangeReason,
    accept: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Amendment/restatement/mapping_correction → next vNNN.
    Prior file bytes unchanged; prior status → superseded; superseded_by set in index
    (and we write a tiny sidecar update only via new file + index — prior JSON status
    updated in-place ONLY for status/superseded_by metadata fields, OR we leave prior
    bytes and rely on index.

    Architecture: never mutate old file bytes after accepted.
    We keep prior file bytes intact; supersession is recorded in index + new version's
    supersedes field. CURRENT pointer moves to new version.
    """
    storage.ensure_company_layout(ticker, root)
    existing = _existing_version_ids(ticker, period_key, root)
    if not existing:
        # treat as initial
        document = copy.deepcopy(document)
        document["change_reason"] = change_reason if change_reason == "initial" else "initial"
        return create_initial_version(ticker, period_key, document, accept=accept, root=root)

    new_id = next_version_id(existing)
    # Determine prior current
    ptr = storage.load_current_pointer(ticker, period_key, root)
    prior_id = (ptr or {}).get("version_id") or existing[-1]

    doc = copy.deepcopy(document)
    doc["version_id"] = new_id
    doc["period_key"] = period_key
    doc["ticker"] = ticker.upper()
    doc["change_reason"] = change_reason
    doc["supersedes"] = prior_id
    doc["superseded_by"] = None
    if accept:
        doc["status"] = "accepted"
        doc["accepted_at"] = doc.get("accepted_at") or utc_now()
        doc["review_status"] = "accepted"
    else:
        doc["status"] = doc.get("status") or "draft"

    path = storage.version_path(ticker, period_key, new_id, root)
    if path.exists():
        raise ImmutableVersionError(f"refusing to overwrite {path}")
    storage.write_json(path, doc)

    # Mark prior superseded in INDEX only (do not rewrite prior version file bytes)
    index = storage.load_index(ticker, root)
    for p in index.get("periods", []):
        if p.get("period_key") != period_key:
            continue
        for h in p.get("history", []):
            if h.get("version_id") == prior_id:
                h["status"] = "superseded"
                h["superseded_by"] = new_id
        p["current_version_id"] = new_id
    storage.save_index(ticker, index, root)

    write_current_pointer(ticker, period_key, new_id, root)
    _update_index_entry(ticker, period_key, doc, root)
    return doc


def assert_version_immutable(ticker: str, period_key: str, version_id: str, root: Path | None = None) -> bytes:
    """Read raw bytes of a version file (for tests asserting no mutation)."""
    path = storage.version_path(ticker, period_key, version_id, root)
    return path.read_bytes()
