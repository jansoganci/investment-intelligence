"""Semantic FACT vs COMPANY_EXPLANATION vs MODEL_INFERENCE."""
from __future__ import annotations

from fa.stage4.semantic import heuristic_stage4_semantic, load_stage4_semantic_from_fixture


def test_evidence_kinds_from_heuristic_text():
    text = """
    Organic revenue growth was 5 percent excluding the impact of acquisitions.
    On a constant currency basis, net operating revenues increased.
    Unit case volume increased in emerging markets.
    Share-based compensation expense was material.
    Remaining performance obligations totaled something.
    """
    rev = heuristic_stage4_semantic(text, source_label="fixture_mdna")
    assert rev.filled
    kinds = {f.evidence_kind for f in rev.findings}
    assert "COMPANY_EXPLANATION" in kinds or "FACT" in kinds
    # dilution_sbc mapped as FACT
    sbc = [f for f in rev.findings if f.topic == "dilution_sbc"]
    assert sbc and sbc[0].evidence_kind == "FACT"
    # organic stays COMPANY_EXPLANATION (not silently promoted)
    org = [f for f in rev.findings if f.topic == "organic_vs_acquired"]
    assert org
    assert org[0].evidence_kind == "COMPANY_EXPLANATION"


def test_fixture_payload_preserves_kinds():
    payload = {
        "filled": True,
        "review_source": "fixture",
        "findings": [
            {
                "topic": "organic_vs_acquired",
                "evidence_kind": "FACT",
                "citation": "table",
                "excerpt": "organic +3%",
            },
            {
                "topic": "runway_claim",
                "evidence_kind": "COMPANY_EXPLANATION",
                "citation": "mdna",
                "excerpt": "long-term growth opportunity",
            },
            {
                "topic": "filing_retrieval",
                "evidence_kind": "MODEL_INFERENCE",
                "citation": "missing",
                "escalate_to_human": True,
            },
        ],
    }
    rev = load_stage4_semantic_from_fixture(notes_payload=payload)
    by = {f.topic: f.evidence_kind for f in rev.findings}
    assert by["organic_vs_acquired"] == "FACT"
    assert by["runway_claim"] == "COMPANY_EXPLANATION"
    assert by["filing_retrieval"] == "MODEL_INFERENCE"


def test_channel_stuffing_escalates_not_autofail():
    text = "Management denies any channel stuffing or trade loading in the quarter."
    rev = heuristic_stage4_semantic(text)
    hits = [f for f in rev.findings if f.topic == "fp_channel_stuffing"]
    assert hits
    assert hits[0].escalate_to_human is True
