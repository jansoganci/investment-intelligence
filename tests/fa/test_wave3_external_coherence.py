"""Wave 3 regression — A7 OE period coherence, B3 post-period, B1 PPA, B2 ER5/ER8."""
from __future__ import annotations

from fa.stage5.semantic import _findings_from_text as s5_findings
from fa.stage6.semantic import _findings_from_text as s6_findings
from fa.stage8.market_data import (
    capital_structure_freshness_notes,
    detect_material_post_period_events,
)
from fa.stage8.normalization import build_normalized_base
from fa.stage9.evaluate import (
    _build_breakers,
    _er5_named_legal_facts,
    _thesis_link_supported_for_legal,
    evaluate_stage9,
)
from fa.stage9.semantic import (
    _findings_from_text as s9_findings,
    excerpt_has_primary_legal,
)
from fa.models import Stage9SemanticFinding, Stage9SemanticReview


# ---------------------------------------------------------------------------
# A7 — OE period coherence
# ---------------------------------------------------------------------------


def test_w3_a7_oe_period_aligned_not_cross_year_median():
    """OE must equal median of per-year (OCF−CapEx), not median(OCF)−median(CapEx)."""
    rows = [
        {"period_key": "FY2023", "operating_cash_flow": 5000.0, "capex": 200.0},
        {"period_key": "FY2024", "operating_cash_flow": 4800.0, "capex": 190.0},
        {"period_key": "FY2025", "operating_cash_flow": 6200.0, "capex": 80.0},
        {"period_key": "FY2026", "operating_cash_flow": 8800.0, "capex": 175.0},
    ]
    # Cross-year bug would do: med(OCF last3)=6200 − med(CapEx last3)=175 → 6025
    # Period-aligned: med(4800-190, 6200-80, 8800-175) = med(4610, 6120, 8625) = 6120
    norm = build_normalized_base(rows, primary_archetype="A1")
    assert norm["owner_earnings_period_coherent"] is True
    assert norm["owner_earnings_label"] == "ocf_minus_reported_capex_proxy_period_aligned"
    assert abs(norm["owner_earnings_base"] - 6120.0) < 1e-6
    # Must NOT equal cross-year mix
    cross_year = 6200.0 - 175.0
    assert abs(norm["owner_earnings_base"] - cross_year) > 1.0
    assert "FY2024" in (norm.get("owner_earnings_period_keys") or [])


def test_w3_a7_oe_no_compatible_pair_exposes_missing():
    rows = [
        {"period_key": "FY2024", "operating_cash_flow": 1000.0, "capex": None},
        {"period_key": "FY2025", "operating_cash_flow": 1100.0, "capex": None},
    ]
    norm = build_normalized_base(rows, primary_archetype="A1")
    assert norm["owner_earnings_base"] is None
    assert norm["owner_earnings_label"] == "NOT_APPLICABLE"
    assert norm["owner_earnings_period_coherent"] is False
    assert "oe_no_compatible_ocf_capex_pair" in (norm.get("uncertainty_drivers") or [])


def test_w3_a7_oe_matches_fcf_like_when_ocf_minus_capex():
    rows = [
        {
            "period_key": f"FY{2022+i}",
            "operating_cash_flow": 7000.0 + i * 100,
            "capex": 1200.0 + i * 50,
            "free_cash_flow": None,
        }
        for i in range(4)
    ]
    norm = build_normalized_base(rows, primary_archetype="A1")
    assert norm["owner_earnings_base"] == norm["fcf_like_base"]


# ---------------------------------------------------------------------------
# B3 — material post-period events
# ---------------------------------------------------------------------------


def _dhr_like_periods():
    """Regression shape only — no ticker hardcode in production path."""
    return [
        {
            "period_key": "FY2025",
            "period_type": "FY",
            "period_end": "2025-12-31",
            "filed_at": "2026-02-24",
            "fields": {
                "long_term_debt": 18_416_000_000,
                "short_term_debt": 2_000_000,
                "business_acquisitions_cash": 0,
                "shares_outstanding": 706_900_000,
                "cash_and_equivalents": 4_615_000_000,
            },
        },
        {
            "period_key": "2026Q2",
            "period_type": "Q",
            "period_end": "2026-06-26",
            "filed_at": "2026-07-21",
            "fields": {
                "long_term_debt": 25_147_000_000,
                "short_term_debt": 1_411_000_000,
                "business_acquisitions_cash": 9_843_000_000,
                "shares_outstanding": 702_900_000,
                "cash_and_equivalents": 4_348_000_000,
            },
        },
    ]


def test_w3_b3_detects_material_post_period_acquisition_and_debt():
    det = detect_material_post_period_events(
        _dhr_like_periods(),
        cs_period_key="FY2025",
        cs_period_end="2025-12-31",
    )
    assert det["evidence_status"] == "events_found"
    assert det["events"]
    types = {r["type"] for r in det["event_records"]}
    assert "acquisition" in types
    assert "financing_debt_change" in types
    for r in det["event_records"]:
        assert r.get("relationship") == "post_period_vs_cs_statement_date"
        assert r.get("source")
        assert r.get("event_date")


def test_w3_b3_empty_events_not_proof_of_none_when_no_interim():
    periods = [
        {
            "period_key": "FY2025",
            "period_type": "FY",
            "period_end": "2025-12-31",
            "fields": {"long_term_debt": 1e9, "short_term_debt": 0},
        }
    ]
    det = detect_material_post_period_events(
        periods, cs_period_key="FY2025", cs_period_end="2025-12-31"
    )
    assert det["events"] == []
    assert det["evidence_status"] == "no_post_cs_interim_available"
    notes = capital_structure_freshness_notes(
        filing_period_end="2025-12-31",
        filing_as_of="2026-02-24",
        price_staleness="CURRENT",
        post_period_events=[],
        post_period_evidence_status=det["evidence_status"],
    )
    assert notes["empty_events_not_proof_of_none"] is True
    assert "does NOT establish" in notes["why"]


def test_w3_b3_historical_cs_statement_date_unchanged_in_detector():
    det = detect_material_post_period_events(
        _dhr_like_periods(), cs_period_key="FY2025", cs_period_end="2025-12-31"
    )
    assert det["cs_period_key"] == "FY2025"
    assert det["cs_period_end"] == "2025-12-31"
    # Events are separate evidence — detector does not rewrite CS key to 2026Q2
    assert "2026Q2" in (det.get("later_period_keys") or [])


# ---------------------------------------------------------------------------
# B1 — PPA semantic
# ---------------------------------------------------------------------------


DE_SEGMENT = (
    "We operate through the following operating segments: "
    "Production & Precision Agriculture (PPA), Small Agriculture & Turf (SAT), "
    "Construction & Forestry (CF), and Financial Services."
)

TRUE_PPA = (
    "The purchase price allocation (PPA) for the acquired business resulted in "
    "amortization of acquired intangibles and purchase accounting adjustments."
)


def test_w3_b1_precision_agriculture_ppa_not_hit_stage5():
    hits = s5_findings(DE_SEGMENT, "10-K")
    ppa = [h for h in hits if h.topic == "ppa_acquisition_optics"]
    assert ppa == [], [h.excerpt for h in ppa]


def test_w3_b1_precision_agriculture_ppa_not_hit_stage6():
    hits = s6_findings(DE_SEGMENT, source_label="10-Q")
    ppa = [
        h
        for h in hits
        if h.topic == "acquisition_context" and "PPA" in (h.excerpt or "")
    ]
    # Must not attribute segment acronym as purchase-price-allocation
    assert all("Precision Agriculture" not in (h.excerpt or "") or "purchase" in (h.excerpt or "").lower() for h in ppa)
    # Stronger: no finding whose matched cue is bare segment PPA
    assert not any("Precision Agriculture (PPA)" in (h.excerpt or "") for h in hits if h.topic == "acquisition_context" and "purchase price" not in (h.excerpt or "").lower())


def test_w3_b1_true_purchase_price_allocation_still_hits():
    s5 = s5_findings(TRUE_PPA, "10-K")
    assert any(h.topic == "ppa_acquisition_optics" for h in s5)
    s6 = s6_findings(TRUE_PPA, source_label="10-K")
    assert any(h.topic == "acquisition_context" for h in s6)


# ---------------------------------------------------------------------------
# B2 — ER5 multi-issue + ER8 thesis-linked promotion
# ---------------------------------------------------------------------------


FTC_SETTLEMENT = (
    "On July 8, 2026, we entered into a settlement with the FTC and plaintiff states "
    "to resolve all claims contained in the lawsuit. As part of that settlement, we have "
    "agreed, among other items, to provide certain repair resources to farmers "
    "(right-to-repair) under ongoing FTC compliance oversight."
)

RF_BOILERPLATE = (
    "We are subject to complex and evolving antitrust laws and government regulation "
    "in the countries where we operate. These laws and regulations include a range of "
    "trade, antitrust, product, and anti-bribery rules."
)


def test_w3_b2_semantic_surfaces_ftc_not_only_boilerplate():
    text = RF_BOILERPLATE + "\n\nITEM 3. LEGAL PROCEEDINGS\n" + FTC_SETTLEMENT
    hits = s9_findings(text, source_label="10-Q:test", form="10-Q")
    anti = [h for h in hits if h.topic == "antitrust"]
    assert anti, "expected antitrust findings"
    primary = [h for h in anti if excerpt_has_primary_legal(h.excerpt)]
    assert primary, [h.excerpt[:80] for h in anti]
    assert any("FTC" in (h.excerpt or "") for h in primary)
    assert any(
        "July 8, 2026" in (h.excerpt or "") or "settlement" in (h.excerpt or "").lower()
        for h in primary
    )


def test_w3_b2_boilerplate_alone_not_primary_legal():
    hits = s9_findings(RF_BOILERPLATE, source_label="10-K:rf", form="10-K")
    primary = [h for h in hits if excerpt_has_primary_legal(h.excerpt)]
    assert primary == []


def test_w3_b2_er5_multi_issue_no_singular_collapse():
    sem = Stage9SemanticReview(
        filled=True,
        review_source="unit",
        findings=[
            Stage9SemanticFinding(
                topic="antitrust",
                citation="t",
                classification="legal",
                evidence_kind="FACT",
                materiality_judgment="watchable",
                materiality_reason="primary-legal",
                escalate_to_human=True,
                excerpt="FTC lawsuit filed January 15, 2025 over repair resources / right-to-repair.",
                section="10-K",
                accession="acc-1",
                er_lens="ER5",
                mechanism="competition_law_enforcement_or_private_action",
                exposure="network_rules_fees_or_business_model_constraints",
            ),
            Stage9SemanticFinding(
                topic="antitrust",
                citation="t2",
                classification="legal",
                evidence_kind="FACT",
                materiality_judgment="watchable",
                materiality_reason="primary-legal",
                escalate_to_human=True,
                excerpt="On July 8, 2026, we entered into a settlement with the FTC and plaintiff states.",
                section="10-Q",
                accession="acc-2",
                er_lens="ER5",
                mechanism="competition_law_enforcement_or_private_action",
                exposure="network_rules_fees_or_business_model_constraints",
            ),
        ],
    )
    facts = _er5_named_legal_facts(sem)
    assert len(facts) >= 2
    assert all(f.get("status") for f in facts)
    assert all(f.get("excerpt") for f in facts)


def test_w3_b2_er8_promotes_when_thesis_link_supported():
    ok, why = _thesis_link_supported_for_legal(
        excerpt=FTC_SETTLEMENT,
        gate2={"kill_shot_primary": "dealer economics and technology attach"},
        regulatory_posture="sword",
    )
    assert ok is True
    assert "operating" in why or "repair" in why or "moat" in why or "Gate2" in why


def test_w3_b2_er8_no_auto_promote_when_ambiguous():
    ok, why = _thesis_link_supported_for_legal(
        excerpt="The FTC closed a routine filing review with no operational conditions disclosed.",
        gate2={"kill_shot_primary": "ag downturn share loss"},
        regulatory_posture="unknown",
    )
    assert ok is False
    assert "ambiguous" in why.lower()


def test_w3_b2_breaker_promotes_repair_linked_fact():
    sem = Stage9SemanticReview(
        filled=True,
        review_source="unit",
        findings=[
            Stage9SemanticFinding(
                topic="antitrust",
                citation="t",
                classification="legal",
                evidence_kind="FACT",
                materiality_judgment="watchable",
                materiality_reason="primary-legal",
                escalate_to_human=True,
                excerpt=FTC_SETTLEMENT,
                section="10-Q",
                accession="acc-q",
                er_lens="ER5",
                mechanism="competition_law_enforcement_or_private_action",
                exposure="repair_aftermarket_operating_constraints",
            )
        ],
    )
    breakers, monitors = _build_breakers(
        gate2={"kill_shot_primary": "dealer economics impaired"},
        semantic=sem,
        primary="A5",
        concentration={"customer": "moderate"},
        regulatory_posture="sword",
    )
    reg = [b for b in breakers if b.breaker_id == "TB_REG_SWORD"]
    assert reg, monitors
    assert reg[0].active_fact is True
    assert "ER5" in reg[0].linked_er_lenses
    assert 3 <= len(breakers) <= 7 or len(breakers) <= 7


def test_w3_b2_evaluate_surfaces_named_legal_and_carry():
    sem = Stage9SemanticReview(
        filled=True,
        review_source="unit",
        findings=[
            Stage9SemanticFinding(
                topic="antitrust",
                citation="t",
                classification="legal",
                evidence_kind="FACT",
                materiality_judgment="watchable",
                materiality_reason="primary-legal",
                escalate_to_human=True,
                excerpt=FTC_SETTLEMENT,
                section="10-Q",
                accession="acc-q",
                er_lens="ER5",
                mechanism="competition_law_enforcement_or_private_action",
                exposure="repair_aftermarket_operating_constraints",
            )
        ],
        regulatory_notes=FTC_SETTLEMENT[:200],
    )
    report = evaluate_stage9(
        "SYNTH_REG",
        periods=[
            {
                "period_key": "FY2025",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {},
            }
        ],
        semantic=sem,
        thesis_summary="Industrial OEM with dealer network and repair attach",
        stage1_artifact={
            "thesis": {
                "kill_shot_primary": "dealer economics and repair attach erosion",
                "monitoring_variables": ["dealer health", "repair attach"],
                "advantage_type": "dealer network / repair attach",
            }
        },
    )
    bullets = " ".join(report.regulatory_geo_bullets or [])
    assert "named_legal_facts_count" in bullets or "ER5_LEGAL_" in bullets
    assert "S9_HFA_REGULATORY_MATERIAL" in (report.s9_hfa_carries or [])
    # Must not claim no named primary-legal
    assert "no named primary-legal" not in " ".join(report.monitors or []).lower()
