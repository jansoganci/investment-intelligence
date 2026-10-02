"""Canonical JSONL IO — writes to Drive data path; local cache optional."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Iterable
from . import config

def _ensure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()

def append_jsonl(path: Path, records: Iterable[dict]) -> int:
    _ensure(path)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

def rewrite_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(records)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)

def load_tracked_companies(path: Path | None = None) -> dict:
    p = path or (config.DRIVE_DATA / "tracked_companies.json")
    if not p.exists():
        return {"companies": [], "updated_at": None}
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Convenience paths
def source_items_path() -> Path:
    return config.DRIVE_DATA / "source_items.jsonl"

def events_path() -> Path:
    return config.DRIVE_DATA / "events.jsonl"

def entities_path() -> Path:
    return config.DRIVE_DATA / "entities.jsonl"

def ideas_path() -> Path:
    return config.DRIVE_DATA / "research_ideas.jsonl"
