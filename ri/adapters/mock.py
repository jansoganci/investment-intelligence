"""Synthetic generator — demo only."""
from __future__ import annotations
from ..ids import new_id, utc_now

def ingest(n: int = 1) -> list[dict]:
    now = utc_now()
    return [{
        "id": new_id("src_"),
        "source_system": "mock",
        "source_url": f"https://example.test/mock/{i}",
        "title": f"Mock item {i}",
        "published_at": now,
        "received_at": now,
        "raw_content": f"Mock content {i}. Synthetic demo only.",
        "cleaned_content": f"Mock content {i}. Synthetic demo only.",
        "language": "en",
        "content_hash": None,
        "adapter_meta": {"synthetic_demo": True},
        "processing_status": "received",
        "related_event_ids": [],
        "error": None,
        "created_at": now,
        "updated_at": now,
    } for i in range(n)]
