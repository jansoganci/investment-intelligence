from __future__ import annotations
import json
from pathlib import Path
from ..ids import new_id, utc_now

def ingest(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) and "items" in data else data
    now = utc_now()
    out = []
    for raw in items:
        it = dict(raw)
        it.setdefault("id", new_id("src_"))
        it.setdefault("source_system", "json_fixture")
        it.setdefault("received_at", now)
        it.setdefault("created_at", now)
        it.setdefault("updated_at", now)
        it.setdefault("processing_status", "received")
        it.setdefault("related_event_ids", [])
        it.setdefault("error", None)
        it.setdefault("adapter_meta", {})
        if "cleaned_content" not in it and "raw_content" in it:
            it["cleaned_content"] = it["raw_content"]
        out.append(it)
    return out
