"""Smoke tests for Emtia Defteri harvest → SourceItem mapping."""
from __future__ import annotations

from pathlib import Path

from ri.adapters import emtia_defteri

SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "ri_data"
    / "harvests"
    / "emtia_defteri_synthetic_sample.json"
)


def test_emtia_ingest_maps_harvest_to_source_items():
    items = emtia_defteri.ingest(SAMPLE)
    assert len(items) == 2

    first = items[0]
    assert first["source_system"] == "emtia_defteri"
    assert first["source_url"] == "https://emtiadefteri.com/ornek/bakir-capex"
    assert first["title"] == "Bakır arzı ve CAPEX notu"
    assert first["language"] == "tr"
    assert first["published_at"] == "2026-09-14T10:00:00Z"
    assert first["raw_content"].startswith("FREEPORT-DEMO")
    assert first["id"].startswith("src_")
    assert first["processing_status"] == "received"
    meta = first["adapter_meta"]
    assert meta["section"] == "analiz"
    assert meta["tags"] == ["bakır", "capex"]
    assert meta["author"] == "ED Editör"
    assert meta["members_only_visible"] is True
    assert meta["truncated"] is False
    assert meta["harvested_at"] == "2026-09-14T15:00:00Z"
    assert meta["site"] == "emtiadefteri.com"
    assert meta["published_display"] == "14 Eylül 2026"

    second = items[1]
    assert second["published_at"] is None  # non-ISO → null
    assert second["adapter_meta"]["published_display"] == "dün sabah"
    assert second["adapter_meta"]["truncated"] is True
    assert second["language"] == "tr"


def test_emtia_default_language_tr_when_missing(tmp_path: Path):
    p = tmp_path / "harvest.json"
    p.write_text(
        '{"harvested_at":"2026-09-14T00:00:00Z","site":"emtiadefteri.com","items":['
        '{"title":"X","url":"https://example/x","raw_content":"y","published_at":null}'
        "]}",
        encoding="utf-8",
    )
    items = emtia_defteri.ingest(p)
    assert len(items) == 1
    assert items[0]["language"] == "tr"
