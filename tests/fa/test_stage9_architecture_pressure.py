"""Architecture pressure with SYNTHETIC fixtures (no production ticker hardcodes)."""
from __future__ import annotations

from fa.models import Stage9SemanticFinding, Stage9SemanticReview
from fa.stage9.evaluate import evaluate_stage9
from fa.stage9.handoff import build_prior_handoff, extract_gate2_hypothesis


def _sem(**notes):
    findings = notes.pop("findings", None) or []
    filled = notes.pop("filled", True)
    return Stage9SemanticReview(
        filled=filled, review_source="fixture", findings=findings, **notes
    )


def _periods(n=5, base=2021):
    return [
        {
            "period_key": f"FY{base+i}",
            "period_type": "FY",
            "version_id": "v1",
            "fields": {"revenue": 500 + i * 20},
        }
        for i in range(n)
    ]


def test_synthetic_network_antitrust_pressure_non_terminating():
    """A3-like network: antitrust sword + fintech disruption → REVIEW lean; NON-TERMINATING."""
    report = evaluate_stage9(
        "synthetic_payments_network",
        _periods(),
        semantic=_sem(
            industry_structure_notes="two-sided payments network surplus capture",
            competition_notes="compete with networks and fintechs",
            disruption_notes="fintech multi-homing and alternative rails",
            regulatory_notes="antitrust and interchange regulation",
            geopolitical_notes="geopolitical tensions on cross-border",
            macro_cycle_notes="consumer spend cyclicality",
            findings=[
                Stage9SemanticFinding(
                    topic="antitrust",
                    evidence_kind="FACT",
                    excerpt="subject to antitrust and competition law enforcement worldwide " * 3,
                    escalate_to_human=True,
                    materiality_judgment="watchable",
                    dimension="regulatory",
                    er_lens="ER5",
                    mechanism="antitrust",
                    exposure="scheme_rules",
                ),
                Stage9SemanticFinding(
                    topic="disruption",
                    evidence_kind="CLAIM",
                    excerpt="fintechs may disintermediate portions of the value chain " * 3,
                    dimension="disruption",
                    er_lens="ER3",
                ),
                Stage9SemanticFinding(
                    topic="moat_attack_surface",
                    evidence_kind="CLAIM",
                    excerpt="multi-homing and switching by issuers and acquirers " * 3,
                    dimension="moat",
                    er_lens="ER2",
                ),
                Stage9SemanticFinding(
                    topic="competition",
                    evidence_kind="CLAIM",
                    excerpt="intense competition among global payment networks " * 3,
                    dimension="structure",
                    er_lens="ER1",
                ),
                Stage9SemanticFinding(
                    topic="regulatory",
                    evidence_kind="FACT",
                    excerpt="government regulation including privacy and interchange " * 3,
                    dimension="regulatory",
                    er_lens="ER5",
                ),
                Stage9SemanticFinding(
                    topic="geopolitical",
                    evidence_kind="CLAIM",
                    excerpt="geopolitical tensions and sanctions may reduce volumes " * 3,
                    dimension="geo",
                    er_lens="ER6",
                ),
            ],
        ),
        force_primary="A3",
        stage1_artifact={
            "thesis": {
                "advantage_type": "network effects",
                "kill_shot_primary": "regulatory sword",
                "kill_shot_secondary": "fintech erosion",
                "monitoring_variables": ["regulation", "share"],
            }
        },
        stage5_artifact={"process_outcome": "PROCEED"},
    )
    assert report.process_outcome in {"REVIEW_REQUIRED", "CONDITIONAL", "PROCEED"}
    assert report.terminates_later_stages is False
    assert "S9_HFA_REGULATORY_MATERIAL" in report.s9_hfa_carries or report.regulatory_posture in {
        "sword",
        "both",
    }
    assert 3 <= len(report.thesis_breakers) <= 7
    assert report.no_final_fa_synthesis is True
    # Must not invent BUY/SELL
    blob = " ".join(report.why_bullets).upper()
    assert "BUY" not in blob.split() or "NO BUY" in blob or "NEVER BUY" in blob or "no BUY" in " ".join(report.why_bullets)
    assert "SELL" not in blob or "NO BUY/SELL" in " ".join(report.why_bullets).upper() or "NEVER" in blob


def test_synthetic_a8_cycle_windfall_not_franchise():
    report = evaluate_stage9(
        "synthetic_commodity_cycle",
        _periods(),
        semantic=_sem(
            industry_structure_notes="commodity cost curve industry",
            macro_cycle_notes="cyclical demand; peak pricing risk",
            geopolitical_notes="China demand and geopolitical exposure",
            findings=[
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="cyclical downturn and macroeconomic conditions reduce demand " * 3,
                    dimension="macro",
                    er_lens="ER7",
                ),
                Stage9SemanticFinding(
                    topic="geopolitical",
                    evidence_kind="CLAIM",
                    excerpt="China demand and geopolitical tensions affect volumes " * 3,
                    dimension="geo",
                    er_lens="ER6",
                ),
                Stage9SemanticFinding(
                    topic="industry_structure",
                    evidence_kind="CLAIM",
                    excerpt="capital cycle and supply response govern surplus " * 3,
                    dimension="structure",
                    er_lens="ER1",
                ),
            ],
        ),
        force_primary="A8",
        stage8_artifact={"s8_h9_carries": ["S8_H9_CYCLE_SENSITIVE_VALUATION"]},
        stage1_artifact={
            "thesis": {
                "advantage_type": "low-cost position",
                "kill_shot_primary": "cost curve shift",
                "kill_shot_secondary": "China demand collapse",
            }
        },
    )
    assert report.terminates_later_stages is False
    assert report.cycle_position_class in {"early", "mid", "late", "unknown"}
    assert "S8_H9_CYCLE_SENSITIVE_VALUATION" in report.s8_h9_carries_forwarded
    assert any("windfall" in b.lower() or "franchise" in b.lower() for b in report.macro_cycle_bullets)
    fps = {t["id"] for t in report.false_positive_tags}
    assert "FP-E7" in fps or "FP-E11" in fps


def test_handoff_hypotheses_only_no_rewrite():
    h = build_prior_handoff(
        stage1={
            "thesis": {
                "advantage_type": "scale",
                "one_sentence": "DO NOT RESTATE THIS AS STAGE9 OUTPUT",
                "kill_shot_primary": "entry",
            }
        },
        stage5={"process_outcome": "PROCEED"},
        stage8={"s8_h9_carries": ["S8_H9_EXPECTATIONS_DEMANDING", "IGNORED_OTHER"]},
    )
    assert h["no_stage5_pricing_power_redo"] is True
    assert h["no_stage1_thesis_restatement"] is True
    assert h["s5_durability_hypothesis"]["no_pricing_power_redo"] is True
    assert h["s8_h9_carries"] == ["S8_H9_EXPECTATIONS_DEMANDING"]
    g2 = extract_gate2_hypothesis(h and {"thesis": {"advantage_type": "scale"}})
    # extract on raw stage1:
    g2 = extract_gate2_hypothesis(
        {"thesis": {"advantage_type": "scale", "one_sentence": "SECRET THESIS"}}
    )
    assert g2["advantage_type"] == "scale"
    assert g2["one_sentence_pointer"] == "SECRET THESIS"


def test_er8_not_giant_register():
    report = evaluate_stage9(
        "synthetic_breaker_cap",
        _periods(),
        semantic=_sem(
            filled=True,
            industry_structure_notes="structure",
            competition_notes="competition",
            disruption_notes="disruption mechanism fintech",
            regulatory_notes="regulation antitrust",
            geopolitical_notes="geo",
            macro_cycle_notes="macro",
            concentration_notes="customer concentration significant portion",
            findings=[
                Stage9SemanticFinding(
                    topic=t,
                    evidence_kind="CLAIM",
                    excerpt=f"{t} evidence excerpt long enough for substantive hit " * 4,
                    escalate_to_human=(t == "antitrust"),
                )
                for t in (
                    "antitrust",
                    "disruption",
                    "competition",
                    "regulatory",
                    "geopolitical",
                    "macro_cycle",
                    "concentration_customer",
                    "moat_attack_surface",
                    "industry_structure",
                )
            ],
        ),
        force_primary="A3",
        stage1_artifact={
            "thesis": {
                "advantage_type": "network",
                "kill_shot_primary": "reg",
                "kill_shot_secondary": "fintech",
                "monitoring_variables": ["a", "b", "c"],
            }
        },
    )
    assert len(report.thesis_breakers) <= 7
    assert len(report.thesis_breakers) >= 3
