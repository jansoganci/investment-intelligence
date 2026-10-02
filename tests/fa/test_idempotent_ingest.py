"""Idempotent ingest — architecture §9A cases A–E (+ restatement as 6th)."""
from __future__ import annotations

from fa.contract import blank_period_document
from fa.ingest import ingest_ir_doc, ingest_sec_filing
from fa import storage, versioning
from fa.ids import sha256_hex


def test_case_a_same_filing_twice_no_duplicate(fa_root):
    """A) Same accession twice → no new Source file / no duplicate manifest entry."""
    r1 = ingest_sec_filing(
        "SYNTH_OPCO",
        accession="0009999991-25-000001",
        form="10-K",
        filed_at="2025-02-15",
        content='{"a":1}',
        root=fa_root,
    )
    r2 = ingest_sec_filing(
        "SYNTH_OPCO",
        accession="0009999991-25-000001",
        form="10-K",
        filed_at="2025-02-15",
        content='{"a":1}',
        root=fa_root,
    )
    assert r1["created"] is True
    assert r2["created"] is False
    man = storage.load_source_manifest("SYNTH_OPCO", fa_root)
    assert len(man["sources"]) == 1


def test_case_b_amended_filing_new_source_and_version(fa_root):
    """B) Amended filing → new Source + new Normalized version with supersedes."""
    ingest_sec_filing(
        "SYNTH_OPCO", accession="ACC-ORIG", form="10-K", content="orig", root=fa_root
    )
    doc = blank_period_document("SYNTH_OPCO", "FY2025", "v001", accession="ACC-ORIG", fields={"cash_and_equivalents": 1})
    versioning.create_initial_version("SYNTH_OPCO", "FY2025", doc, accept=True, root=fa_root)

    ingest_sec_filing(
        "SYNTH_OPCO", accession="ACC-AMEND", form="10-K/A", content="amend", root=fa_root
    )
    doc2 = blank_period_document(
        "SYNTH_OPCO", "FY2025", "v002", accession="ACC-AMEND", fields={"cash_and_equivalents": 2}
    )
    v2 = versioning.create_superseding_version(
        "SYNTH_OPCO", "FY2025", doc2, change_reason="amendment", accept=True, root=fa_root
    )
    assert v2["change_reason"] == "amendment"
    assert v2["supersedes"] == "v001"
    man = storage.load_source_manifest("SYNTH_OPCO", fa_root)
    assert len(man["sources"]) == 2


def test_case_c_annual_vs_quarterly_different_period_keys(fa_root):
    """C) Same calendar year annual vs quarterly = different period_keys."""
    d_fy = blank_period_document("SYNTH_OPCO", "FY2025", "v001", period_type="FY", fields={"revenue": 100})
    d_q = blank_period_document("SYNTH_OPCO", "2025Q2", "v001", period_type="Q", fields={"revenue": 40})
    versioning.create_initial_version("SYNTH_OPCO", "FY2025", d_fy, accept=True, root=fa_root)
    versioning.create_initial_version("SYNTH_OPCO", "2025Q2", d_q, accept=True, root=fa_root)
    keys = storage.list_period_keys("SYNTH_OPCO", fa_root)
    assert "FY2025" in keys and "2025Q2" in keys
    assert "FY2025" != "2025Q2"


def test_case_d_ir_update_new_source_no_auto_gaap_mutate(fa_root):
    """D) IR update → new Source; does not auto-mutate GAAP Normalized."""
    doc = blank_period_document("SYNTH_OPCO", "FY2025", "v001", fields={"cash_and_equivalents": 99})
    versioning.create_initial_version("SYNTH_OPCO", "FY2025", doc, accept=True, root=fa_root)
    before = storage.load_current_period("SYNTH_OPCO", "FY2025", fa_root)

    r = ingest_ir_doc(
        "SYNTH_OPCO",
        logical_name="earnings",
        as_of_date="2026-02-01",
        content="IR deck content v1",
        root=fa_root,
    )
    assert r["created"] is True
    after = storage.load_current_period("SYNTH_OPCO", "FY2025", fa_root)
    assert after["fields"]["cash_and_equivalents"] == before["fields"]["cash_and_equivalents"]
    assert after["version_id"] == before["version_id"]

    # same IR again → idempotent
    r2 = ingest_ir_doc(
        "SYNTH_OPCO",
        logical_name="earnings",
        as_of_date="2026-02-01",
        content="IR deck content v1",
        root=fa_root,
    )
    assert r2["created"] is False


def test_case_e_mapping_correction_same_source_new_version(fa_root):
    """E) Corrected normalization, same accession → new version mapping_correction."""
    acc = "ACC-SAME"
    ingest_sec_filing("SYNTH_OPCO", accession=acc, form="10-K", content="x", root=fa_root)
    doc = blank_period_document("SYNTH_OPCO", "FY2025", "v001", accession=acc, fields={"revenue": 1})
    versioning.create_initial_version("SYNTH_OPCO", "FY2025", doc, accept=True, root=fa_root)
    doc2 = blank_period_document("SYNTH_OPCO", "FY2025", "v002", accession=acc, fields={"revenue": 1.5})
    v2 = versioning.create_superseding_version(
        "SYNTH_OPCO", "FY2025", doc2, change_reason="mapping_correction", accept=True, root=fa_root
    )
    assert v2["change_reason"] == "mapping_correction"
    assert v2["accession"] == acc
    assert v2["supersedes"] == "v001"
    # Source still single
    man = storage.load_source_manifest("SYNTH_OPCO", fa_root)
    assert len([s for s in man["sources"] if s["accession"] == acc]) == 1


def test_case_f_restatement_new_version(fa_root):
    """F) Restatement → new version with change_reason=restatement; prior immutable."""
    doc = blank_period_document("SYNTH_OPCO", "FY2024", "v001", fields={"revenue": 10})
    versioning.create_initial_version("SYNTH_OPCO", "FY2024", doc, accept=True, root=fa_root)
    b1 = versioning.assert_version_immutable("SYNTH_OPCO", "FY2024", "v001", fa_root)
    doc2 = blank_period_document("SYNTH_OPCO", "FY2024", "v002", fields={"revenue": 9})
    v2 = versioning.create_superseding_version(
        "SYNTH_OPCO", "FY2024", doc2, change_reason="restatement", accept=True, root=fa_root
    )
    assert v2["change_reason"] == "restatement"
    assert versioning.assert_version_immutable("SYNTH_OPCO", "FY2024", "v001", fa_root) == b1
