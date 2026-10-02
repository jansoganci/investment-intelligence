from __future__ import annotations
from pathlib import Path
from .paste import ingest as paste_ingest

def ingest(path: str | Path, source_url: str | None = None) -> list[dict]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    items = paste_ingest(text, title=p.stem, source_url=source_url)
    for it in items:
        it["source_system"] = "file"
        it["adapter_meta"] = {"filename": p.name}
    return items
