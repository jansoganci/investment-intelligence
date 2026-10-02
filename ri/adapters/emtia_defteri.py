"""Emtia Defteri harvest adapter — reads offline harvest JSON → SourceItem[].

No browser automation, cookies, or live network. Harvest files are produced
elsewhere and landed under ri_data/harvests/ (or a path passed to ingest).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..ids import new_id, utc_now


def _iso_or_none(value) -> str | None:
    """Return value if it parses as ISO-8601 (date or datetime); else None."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return s
    except ValueError:
        return None


def ingest(path: str | Path) -> list[dict]:
    """Map an Emtia Defteri harvest JSON file to SourceItem dicts."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("emtia_defteri harvest must be an object with 'items'")
    items = data.get("items") or []
    harvested_at = data.get("harvested_at")
    site = data.get("site")
    now = utc_now()
    out: list[dict] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        published_at = _iso_or_none(raw.get("published_at"))
        language = raw.get("language") or "tr"
        title = raw.get("title") or ""
        content = raw.get("raw_content") or ""
        adapter_meta = {
            "section": raw.get("section"),
            "tags": raw.get("tags") or [],
            "author": raw.get("author"),
            "members_only_visible": raw.get("members_only_visible"),
            "truncated": raw.get("truncated"),
            "harvested_at": harvested_at,
            "site": site,
            "published_display": raw.get("published_display"),
        }
        out.append({
            "id": new_id("src_"),
            "source_system": "emtia_defteri",
            "source_url": raw.get("url"),
            "title": title,
            "published_at": published_at,
            "received_at": now,
            "raw_content": content,
            "cleaned_content": content,
            "language": language,
            "content_hash": None,
            "adapter_meta": adapter_meta,
            "processing_status": "received",
            "related_event_ids": [],
            "error": None,
            "created_at": now,
            "updated_at": now,
        })
    return out
