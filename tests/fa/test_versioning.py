"""Immutable versioning: v001, supersede, CURRENT pointer, no byte mutation."""
from __future__ import annotations

from fa.contract import blank_period_document
from fa import storage, versioning


def test_initial_version_v001(fa_root):
    doc = blank_period_document("SYNTH_OPCO", "FY2025", "v001", fields={"cash_and_equivalents": 1})
    out = versioning.create_initial_version("SYNTH_OPCO", "FY2025", doc, accept=True, root=fa_root)
    assert out["version_id"] == "v001"
    ptr = storage.load_current_pointer("SYNTH_OPCO", "FY2025", fa_root)
    assert ptr == {"version_id": "v001", "path": "v001.json"}
    loaded = storage.load_current_period("SYNTH_OPCO", "FY2025", fa_root)
    assert loaded["fields"]["cash_and_equivalents"] == 1
    idx = storage.load_index("SYNTH_OPCO", fa_root)
    assert idx["periods"][0]["current_version_id"] == "v001"


def test_supersede_creates_v002_preserves_v001_bytes(fa_root):
    doc = blank_period_document("SYNTH_OPCO", "FY2025", "v001", fields={"cash_and_equivalents": 100})
    versioning.create_initial_version("SYNTH_OPCO", "FY2025", doc, accept=True, root=fa_root)
    bytes_before = versioning.assert_version_immutable("SYNTH_OPCO", "FY2025", "v001", fa_root)

    doc2 = blank_period_document(
        "SYNTH_OPCO", "FY2025", "v002",
        fields={"cash_and_equivalents": 200},
        accession="000-AMEND",
    )
    out = versioning.create_superseding_version(
        "SYNTH_OPCO", "FY2025", doc2, change_reason="amendment", accept=True, root=fa_root
    )
    assert out["version_id"] == "v002"
    assert out["supersedes"] == "v001"
    bytes_after = versioning.assert_version_immutable("SYNTH_OPCO", "FY2025", "v001", fa_root)
    assert bytes_before == bytes_after  # never mutate old file bytes

    ptr = storage.load_current_pointer("SYNTH_OPCO", "FY2025", fa_root)
    assert ptr["version_id"] == "v002"
    cur = storage.load_current_period("SYNTH_OPCO", "FY2025", fa_root)
    assert cur["fields"]["cash_and_equivalents"] == 200

    idx = storage.load_index("SYNTH_OPCO", fa_root)
    hist = idx["periods"][0]["history"]
    v001 = next(h for h in hist if h["version_id"] == "v001")
    assert v001["status"] == "superseded"
    assert v001["superseded_by"] == "v002"


def test_mapping_correction_reason(fa_root):
    doc = blank_period_document("T", "FY2024", "v001", fields={"revenue": 1})
    versioning.create_initial_version("T", "FY2024", doc, accept=True, root=fa_root)
    doc2 = blank_period_document("T", "FY2024", "v002", fields={"revenue": 2})
    out = versioning.create_superseding_version(
        "T", "FY2024", doc2, change_reason="mapping_correction", accept=True, root=fa_root
    )
    assert out["change_reason"] == "mapping_correction"
    assert out["version_id"] == "v002"
