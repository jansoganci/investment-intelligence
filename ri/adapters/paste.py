from __future__ import annotations
from ..ids import new_id, utc_now

def ingest(text: str, title: str = "", source_url: str | None = None, language: str | None = None) -> list[dict]:
    now = utc_now()
    return [{
        "id": new_id("src_"),
        "source_system": "paste",
        "source_url": source_url,
        "title": title or (text.strip().split("\n")[0][:120] if text.strip() else "untitled"),
        "published_at": None,
        "received_at": now,
        "raw_content": text,
        "cleaned_content": text,
        "language": language,
        "content_hash": None,
        "adapter_meta": {},
        "processing_status": "received",
        "related_event_ids": [],
        "error": None,
        "created_at": now,
        "updated_at": now,
    }]
