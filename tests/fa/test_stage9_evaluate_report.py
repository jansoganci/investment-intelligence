"""Stage 9 evaluate + markdown report smoke."""
from __future__ import annotations

from fa.models import Stage9SemanticFinding, Stage9SemanticReview
from fa.stage9.evaluate import evaluate_stage9
from fa.stage9.report import render_stage9_markdown
from fa.stage9.questions import STAGE9_OUTCOMES, S9_HFA_CARRIES


def _periods():
    return [
        {
            "period_key": f"FY{yr}",
            "period_type": "FY",
            "version_id": "v1",
            "fields": {"revenue": 1000 + i * 50},
        }
        for i, yr in enumerate(range(2021, 2026))
    ]


def _sem(**notes):
    findings = notes.pop("findings", None) or []
    filled = notes.pop("filled", True)
    return Stage9SemanticReview(
        filled=filled, review_source="fixture", findings=findings, **notes
    )


def test_evaluate_produces_eight_dashboard_blocks_and_outcome():
    report = evaluate_stage9(
        "synthetic_network",
        _periods(),
        semantic=_sem(
            industry_structure_notes="two-sided network; barriers to entry from scale",
            competition_notes="compete with other payment networks and fintechs",
            disruption_notes="fintechs and alternative payment rails",
            concentration_notes="cross-border geographic mix disclosed",
            regulatory_notes="government regulation; competition and antitrust law",
            geopolitical_notes="geopolitical tensions affect cross-border volumes",
            macro_cycle_notes="consumer spending and macroeconomic conditions",
            findings=[
                Stage9SemanticFinding(
                    topic="antitrust",
                    evidence_kind="FACT",
                    excerpt="violations of competition and antitrust law may adversely affect " * 3,
                    escalate_to_human=True,
                    dimension="regulatory",
                    er_lens="ER5",
                    mechanism="antitrust",
                    exposure="rules",
                ),
                Stage9SemanticFinding(
                    topic="disruption",
                    evidence_kind="CLAIM",
                    excerpt="fintechs and new technologies may disrupt our business " * 3,
                    dimension="disruption",
                    er_lens="ER3",
                ),
                Stage9SemanticFinding(
                    topic="competition",
                    evidence_kind="CLAIM",
                    excerpt="the global payments industry continues to undergo dynamic change " * 3,
                    dimension="structure",
                    er_lens="ER1",
                ),
                Stage9SemanticFinding(
                    topic="regulatory",
                    evidence_kind="FACT",
                    excerpt="government regulation of the payments industry " * 3,
                    dimension="regulatory",
                    er_lens="ER5",
                ),
                Stage9SemanticFinding(
                    topic="geopolitical",
                    evidence_kind="CLAIM",
                    excerpt="heightened geopolitical tensions may reduce cross-border " * 3,
                    dimension="geo",
                    er_lens="ER6",
                ),
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="adverse economic conditions and consumer spending declines " * 3,
                    dimension="macro",
                    er_lens="ER7",
                ),
            ],
        ),
        force_primary="A3",
        stage1_artifact={
            "thesis": {
                "advantage_type": "network effects / scale",
                "kill_shot_primary": "regulatory sword on scheme economics",
                "kill_shot_secondary": "fintech multi-homing erosion",
                "monitoring_variables": ["interchange regulation", "network share"],
            }
        },
        stage5_artifact={"process_outcome": "PROCEED"},
        stage8_artifact={
            "s8_h9_carries": ["S8_H9_EXPECTATIONS_DEMANDING"],
            "expectations_label": "demanding",
        },
    )
    assert report.process_outcome in STAGE9_OUTCOMES
    assert report.terminates_later_stages is False
    assert report.no_final_fa_synthesis is True
    assert len(report.er_lenses) == 8
    assert 3 <= len(report.thesis_breakers) <= 7
    assert report.industry_structure_bullets
    assert report.moat_durability_bullets
    assert report.disruption_bullets
    assert report.concentration_bullets
    assert report.regulatory_geo_bullets
    assert report.macro_cycle_bullets
    assert report.breaker_fp_bullets
    assert all(c in S9_HFA_CARRIES for c in report.s9_hfa_carries)
    # ER2 locked wording present
    assert any("pricing-power" in b.lower() or "thesis restatement" in b.lower() for b in report.moat_durability_bullets)
    assert report.gate2_hypothesis_consumed.get("no_thesis_restatement") is True
    md = render_stage9_markdown(report)
    assert "Dashboard 1" in md
    assert "Dashboard 8" in md
    assert "ER1" in md
    assert "NON-TERMINATING" in md or "terminates_later_stages: False" in md


def test_er2_does_not_restate_stage1_thesis():
    report = evaluate_stage9(
        "synthetic_no_restate",
        _periods(),
        semantic=_sem(
            filled=True,
            industry_structure_notes="structure",
            competition_notes="competition among peers",
            findings=[
                Stage9SemanticFinding(
                    topic="competition",
                    evidence_kind="CLAIM",
                    excerpt="compete with peers in the industry continuously " * 3,
                ),
                Stage9SemanticFinding(
                    topic="industry_structure",
                    evidence_kind="CLAIM",
                    excerpt="market structure and barriers to entry matter here " * 3,
                ),
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="macroeconomic conditions affect demand patterns " * 3,
                ),
            ],
        ),
        thesis_summary="WE OWN THIS BECAUSE SUPER MOAT FOREVER",
        stage1_artifact={
            "thesis": {
                "one_sentence": "WE OWN THIS BECAUSE SUPER MOAT FOREVER",
                "advantage_type": "brand",
                "kill_shot_primary": "category decline",
            }
        },
        force_primary="A1",
    )
    joined = " ".join(report.why_bullets + report.moat_durability_bullets + report.industry_structure_bullets)
    assert "WE OWN THIS BECAUSE SUPER MOAT FOREVER" not in joined
    assert report.gate2_hypothesis_consumed.get("no_thesis_restatement") is True


def test_too_hard_non_operating():
    report = evaluate_stage9(
        "synthetic_fi",
        [],
        gate0_class="financial_institution",
        semantic=_sem(filled=False),
    )
    assert report.process_outcome == "TOO_HARD"
    assert report.terminates_later_stages is False


def test_pension_new_entrants_not_moat_attack_triple():
    """Pension "closed to new entrants" must not fabricate moat-attack mechanism+exposure."""
    from fa.stage9.semantic import _findings_from_text

    text = (
        "The defined benefit pension plans for non-unionised employees are closed to "
        "new entrants in all countries. For unionised employees, some plans remain open."
    )
    findings = _findings_from_text(text, source_label="20-F:test")
    moat = [f for f in findings if f.topic == "moat_attack_surface"]
    assert moat == [] or all(f.mechanism is None and f.exposure is None for f in moat)


def test_russia_ukraine_war_is_geo_substance():
    from fa.stage9.semantic import excerpt_has_geo_substance

    ex = (
        "Geopolitical tensions and the onset of the Russia-Ukraine war resulted in "
        "extreme price volatility for fossil fuels and several commodities."
    )
    assert excerpt_has_geo_substance(ex)
    assert not excerpt_has_geo_substance(
        "In a year characterised by geopolitical volatility and rapid technological progress."
    )


def test_soft_a8_commodity_archetype_enables_windfall_honesty():
    """No prior Stage 5–8 archetype + commodity semantic → soft A8 (not a grade)."""
    report = evaluate_stage9(
        "synthetic_miner",
        _periods(),
        semantic=_sem(
            industry_structure_notes=(
                "The resilience of the Group business model is underpinned by the "
                "competitive position and diversification of our commodities portfolio "
                "and our disciplined capital allocation framework."
            ),
            macro_cycle_notes=(
                "Commodity demand and trade flows; commodity price volatility and "
                "capital allocation under cycle stress."
            ),
            concentration_notes=(
                "China is the largest market for our products and its growth pathway "
                "could affect demand; China Baowu largest customer."
            ),
            breaker_notes="Falling commodity prices or adverse China demand pathway.",
            competition_notes="Iron ore and copper peers in metals and mining.",
            geopolitical_notes=(
                "The onset of the Russia-Ukraine war resulted in extreme price volatility."
            ),
            regulatory_notes="Delays in approvals and increased government regulation.",
            findings=[
                Stage9SemanticFinding(
                    topic="concentration_customer",
                    evidence_kind="FACT",
                    excerpt="largest customer China Baowu partnership " * 4,
                    escalate_to_human=False,  # largest alone ≠ material without revenue share
                    dimension="concentration",
                    er_lens="ER4",
                    mechanism="customer_dependency",
                    exposure="earnings",
                ),
                Stage9SemanticFinding(
                    topic="geopolitical",
                    evidence_kind="CLAIM",
                    excerpt=(
                        "The onset of the Russia-Ukraine war resulted in extreme price "
                        "volatility for fossil fuels and commodities markets worldwide."
                    ),
                    dimension="geo",
                    er_lens="ER6",
                    mechanism="sanctions_export_controls_or_political_shock",
                    exposure="cross_border_volume_or_ops_footprint",
                ),
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="commodity price downturn and capital allocation cycle " * 3,
                    dimension="macro",
                    er_lens="ER7",
                    mechanism="demand_or_spend_cycle_sensitivity",
                    exposure="volume_or_mix_under_macro_stress",
                ),
            ],
        ),
    )
    assert report.archetype is not None
    assert report.archetype.primary_archetype == "A8"
    assert report.archetype.provenance == "semantic_soft_commodity"
    assert report.archetype.confidence == "LOW"
    # windfall≠franchise packaging present; commodity ≠ auto BAD / mechanical kill
    assert report.terminates_later_stages is False
    assert report.process_outcome in STAGE9_OUTCOMES
    assert report.process_outcome != "TOO_HARD"
    macro_join = " ".join(report.macro_cycle_bullets or [])
    assert "windfall" in macro_join.lower() or any(
        b.breaker_id == "TB_CYCLE" for b in report.thesis_breakers
    )


def test_china_demand_is_not_geo_substance():
    """High China revenue/demand/market/pathway ≠ geo mechanism (ER4 concentration)."""
    from fa.stage9.semantic import excerpt_has_geo_footprint, excerpt_has_geo_substance

    assert not excerpt_has_geo_substance(
        "China is the largest market for our products and its growth pathway "
        "could affect demand for our products."
    )
    assert not excerpt_has_geo_substance(
        "Steelmakers in China maintained elevated operating rates as domestic demand rose."
    )
    assert not excerpt_has_geo_substance(
        "China development pathway: China’s growth pathway could impact demand."
    )
    # True geo still works
    assert excerpt_has_geo_substance(
        "Sanctions and export controls affecting operations in China."
    )
    assert excerpt_has_geo_footprint(
        "Sanctions disrupted our operations and cross-border volumes in the region."
    )


def test_geo_material_requires_footprint_not_price_vol_alone():
    """Russia-Ukraine commodity price shock without company footprint ≠ GEO_MATERIAL HFA."""
    report = evaluate_stage9(
        "synthetic_geo_price_vol",
        _periods(),
        semantic=_sem(
            industry_structure_notes="commodity portfolio capital allocation",
            macro_cycle_notes="commodity price volatility and capital cycle",
            geopolitical_notes=(
                "The onset of the Russia-Ukraine war resulted in extreme price "
                "volatility for fossil fuels and several commodities."
            ),
            findings=[
                Stage9SemanticFinding(
                    topic="geopolitical",
                    evidence_kind="CLAIM",
                    excerpt=(
                        "Geopolitical tensions and the onset of the Russia-Ukraine war "
                        "resulted in extreme price volatility for fossil fuels and "
                        "several commodities across global markets this year."
                    ),
                    dimension="geo",
                    er_lens="ER6",
                    mechanism="sanctions_export_controls_or_political_shock",
                    exposure="cross_border_volume_or_ops_footprint",
                ),
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="commodity price downturn and capital allocation cycle " * 3,
                    dimension="macro",
                    er_lens="ER7",
                ),
            ],
        ),
        force_primary="A8",
    )
    assert "S9_HFA_GEO_MATERIAL" not in report.s9_hfa_carries
    assert report.terminates_later_stages is False


def test_geo_material_with_sanctions_ops_footprint():
    """Sanctions + ops footprint → GEO_MATERIAL allowed (still NON-TERMINATING)."""
    report = evaluate_stage9(
        "synthetic_geo_footprint",
        _periods(),
        semantic=_sem(
            geopolitical_notes="sanctions ops",
            findings=[
                Stage9SemanticFinding(
                    topic="geopolitical",
                    evidence_kind="CLAIM",
                    excerpt=(
                        "Following the Russia-Ukraine war, sanctions disrupted our "
                        "operations and cross-border volumes in affected markets; "
                        "export controls further constrained shipments."
                    ),
                    dimension="geo",
                    er_lens="ER6",
                    mechanism="sanctions_export_controls_or_political_shock",
                    exposure="cross_border_volume_or_ops_footprint",
                ),
            ],
        ),
        force_primary="A3",
    )
    assert "S9_HFA_GEO_MATERIAL" in report.s9_hfa_carries
    assert report.terminates_later_stages is False


def test_tb_concentration_inference_alone_not_active_downgrades_to_monitor():
    """High concentration labels without FACT disclosure → monitor; never ACTIVE."""
    report = evaluate_stage9(
        "synthetic_conc_inference",
        _periods(),
        semantic=_sem(
            concentration_notes="geo concentration inferred from narrative only",
            findings=[
                Stage9SemanticFinding(
                    topic="concentration_geo",
                    evidence_kind="CLAIM",
                    excerpt="China is the largest market for our products and demand " * 3,
                    dimension="concentration",
                    er_lens="ER4",
                    mechanism="geo_dependency",
                    exposure="earnings",
                ),
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="cyclical downturn reduces commodity demand volumes " * 3,
                    dimension="macro",
                    er_lens="ER7",
                ),
            ],
        ),
        force_primary="A8",
        # Seed calc-like concentration via semantic cues — evaluate derives labels
        # from semantic; ensure no FACT concentration_customer
    )
    conc_breakers = [b for b in report.thesis_breakers if b.breaker_id == "TB_CONCENTRATION"]
    # Either absent (demoted) or if present must not be ACTIVE / not INFERENCE-as-active
    for b in conc_breakers:
        assert b.active_fact is False
        assert b.evidence_label != "INFERENCE" or b.active_fact is False
    assert not any(
        b.breaker_id == "TB_CONCENTRATION" and b.active_fact for b in report.thesis_breakers
    )
    # When labels high without FACT, expect monitor wording
    # (labels may be unknown if calc doesn't see disclosed pct — then no TB_CONCENTRATION at all)
    if not conc_breakers:
        assert any("TB_CONCENTRATION monitoring" in m for m in report.monitors) or all(
            v not in {"high", "extreme"} for v in (report.concentration_labels or {}).values()
        )


def test_tb_concentration_fact_inactive_not_active_breaker():
    """Quantitative customer concentration FACT backs TB_CONCENTRATION but must not be ACTIVE sword."""
    report = evaluate_stage9(
        "synthetic_conc_fact",
        _periods(),
        semantic=_sem(
            concentration_notes="largest customer accounts for 28% of our revenues",
            macro_cycle_notes="commodity price cycle",
            industry_structure_notes="commodities portfolio capital allocation",
            findings=[
                Stage9SemanticFinding(
                    topic="concentration_customer",
                    evidence_kind="FACT",
                    excerpt=(
                        "Our largest customer accounts for 28% of our revenues; "
                        "loss of that customer could materially affect results."
                    ),
                    escalate_to_human=True,
                    dimension="concentration",
                    er_lens="ER4",
                    mechanism="customer_dependency",
                    exposure="earnings",
                ),
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="commodity price downturn and capital allocation cycle " * 3,
                    dimension="macro",
                    er_lens="ER7",
                ),
            ],
        ),
        force_primary="A8",
    )
    conc = [b for b in report.thesis_breakers if b.breaker_id == "TB_CONCENTRATION"]
    assert conc, report.thesis_breakers
    assert conc[0].evidence_label == "FACT"
    assert conc[0].active_fact is False
    assert "S9_HFA_THESIS_BREAKER_ACTIVE" not in report.s9_hfa_carries


def test_review_required_not_from_soft_a8_or_claim_count_or_inactive_geo_cycle():
    """Soft A8/LOW + CLAIM geo/cycle + inactive breakers must not mechanical RR."""
    report = evaluate_stage9(
        "synthetic_soft_a8_no_rr",
        _periods(),
        semantic=_sem(
            industry_structure_notes=(
                "commodities portfolio and disciplined capital allocation framework"
            ),
            macro_cycle_notes="commodity demand and price volatility capital cycle",
            competition_notes="iron ore and copper metals and mining peers",
            geopolitical_notes="geopolitical volatility without footprint",
            findings=[
                Stage9SemanticFinding(
                    topic="geopolitical",
                    evidence_kind="CLAIM",
                    excerpt="characterised by geopolitical volatility and rapid progress " * 3,
                    dimension="geo",
                    er_lens="ER6",
                ),
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="cyclical downturn and commodity price peak mid-cycle risk " * 3,
                    dimension="macro",
                    er_lens="ER7",
                ),
                Stage9SemanticFinding(
                    topic="industry_structure",
                    evidence_kind="CLAIM",
                    excerpt="capital cycle and supply response govern surplus capture " * 3,
                    dimension="structure",
                    er_lens="ER1",
                ),
            ],
        ),
        # no force_primary — soft A8 from semantic
    )
    assert report.archetype is not None
    assert report.archetype.primary_archetype == "A8"
    assert report.archetype.confidence == "LOW"
    # No concentration FACT escalate, no primary-legal → must NOT be RR from soft A8/CLAIM
    assert report.process_outcome != "REVIEW_REQUIRED", report.why_bullets
    assert report.terminates_later_stages is False
    joined = " ".join(report.why_bullets).lower()
    assert "soft a8" not in joined or "not soft" in joined or report.process_outcome != "REVIEW_REQUIRED"


def test_rr_from_concentration_fact_survives_without_archetype_or_inactive_geo_cycle():
    """Counterfactual: RR from quantitative concentration FACT escalate holds if soft A8 ignored / GEO-CYCLE removed."""
    report = evaluate_stage9(
        "synthetic_rr_conc_only",
        _periods(),
        semantic=_sem(
            concentration_notes="largest customer accounts for 28% of revenue",
            findings=[
                Stage9SemanticFinding(
                    topic="concentration_customer",
                    evidence_kind="FACT",
                    excerpt=(
                        "Our largest customer accounts for 28% of our revenues in the "
                        "year ended December 31, as disclosed in customer concentration notes."
                    ),
                    escalate_to_human=True,
                    dimension="concentration",
                    er_lens="ER4",
                    mechanism="customer_dependency",
                    exposure="earnings",
                ),
            ],
        ),
        force_primary="A1",  # ignore soft commodity archetype path
    )
    assert report.process_outcome == "REVIEW_REQUIRED", report.why_bullets
    why = " ".join(report.why_bullets).lower()
    assert "concentration" in why
    assert "inactive geo" not in why or "not" in why
    # Inactive GEO/CYCLE not required for RR
    assert not any(
        b.breaker_id in {"TB_GEO", "TB_CYCLE"} and b.active_fact
        for b in report.thesis_breakers
    )


def test_largest_customer_alone_without_quant_not_material_escalate():
    """Largest-customer identity alone ≠ automatic material concentration / RR."""
    from fa.stage9.semantic import (
        excerpt_has_concentration_quant,
        _findings_from_text,
    )

    assert not excerpt_has_concentration_quant(
        "In 2023, we extended a key climate partnership with our largest customer, "
        "China Baowu, to accelerate efforts to decarbonise the steel value chain."
    )
    assert excerpt_has_concentration_quant(
        "Our largest customer accounts for 28% of our revenues in FY2023."
    )
    assert excerpt_has_concentration_quant(
        "A significant portion of our net sales is derived from a small number of customers."
    )

    findings = _findings_from_text(
        "From customer to strategic partner In 2023, we extended a key climate "
        "partnership with our largest customer, China Baowu, to accelerate efforts "
        "to decarbonise the steel value chain and reduce our Scope 3 emissions. "
        "This is the result of decades of deep relationship building.",
        source_label="20-F:test",
        accession="0001628280-24-006512",
        form="20-F",
    )
    cust = [f for f in findings if f.topic == "concentration_customer"]
    assert cust, findings
    assert cust[0].evidence_kind == "FACT"
    assert cust[0].escalate_to_human is False
    assert cust[0].materiality_judgment == "unclear"

    report = evaluate_stage9(
        "synthetic_baowu_no_quant",
        _periods(),
        semantic=_sem(
            industry_structure_notes=(
                "commodities portfolio and disciplined capital allocation framework"
            ),
            macro_cycle_notes="commodity price volatility and capital cycle",
            concentration_notes=(
                "largest customer China Baowu climate partnership; China largest market"
            ),
            findings=[
                Stage9SemanticFinding(
                    topic="concentration_customer",
                    evidence_kind="FACT",
                    excerpt=(
                        "In 2023, we extended a key climate partnership with our "
                        "largest customer, China Baowu, to accelerate decarbonisation."
                    ),
                    escalate_to_human=False,
                    materiality_judgment="unclear",
                    materiality_reason=(
                        "Largest-customer alone without disclosed revenue share — "
                        "monitoring/uncertainty"
                    ),
                    dimension="concentration",
                    er_lens="ER4",
                    mechanism="customer_dependency",
                    exposure="earnings",
                ),
                Stage9SemanticFinding(
                    topic="concentration_geo",
                    evidence_kind="CLAIM",
                    excerpt=(
                        "China is the largest market for our products and its growth "
                        "pathway could affect demand for our products."
                    ),
                    dimension="concentration",
                    er_lens="ER4",
                ),
                Stage9SemanticFinding(
                    topic="macro_cycle",
                    evidence_kind="CLAIM",
                    excerpt="commodity price downturn and capital allocation cycle " * 3,
                    dimension="macro",
                    er_lens="ER7",
                ),
            ],
        ),
    )
    # Counterfactual: Baowu not material → must NOT be RR solely on unsupported materiality
    assert report.process_outcome != "REVIEW_REQUIRED", report.why_bullets
    assert report.concentration_labels.get("customer") in {"unknown", "moderate", "low"}
    assert report.terminates_later_stages is False
    mon = " ".join(report.monitors or []).lower()
    assert "revenue share" in mon or "largest-customer" in mon or "uncertainty" in mon


def test_environmental_permitting_captured_under_er5():
    """Env regulation / permitting / closure / remediation is ER5 research-depth, not skipped."""
    from fa.stage9.semantic import _findings_from_text

    blob = (
        "We are subject to environmental regulations and permitting requirements for "
        "our mining operations. Delays in approvals and mine licence renewals may "
        "affect development. Closure and rehabilitation provisions are reviewed "
        "annually. Remediation of legacy sites and tailings facility management "
        "remain material operational obligations. Environmental litigation and "
        "enforcement actions can arise from alleged non-compliance."
    )
    findings = _findings_from_text(
        blob,
        source_label="20-F:test-env",
        accession="0001628280-24-006512",
        form="20-F",
    )
    env = [f for f in findings if f.topic == "environmental_permitting"]
    assert env, [f.topic for f in findings]
    assert env[0].er_lens == "ER5"

    report = evaluate_stage9(
        "synthetic_miner_env",
        _periods(),
        semantic=_sem(
            industry_structure_notes="commodities portfolio capital allocation",
            regulatory_notes=blob[:220],
            findings=env
            + [
                Stage9SemanticFinding(
                    topic="regulatory",
                    evidence_kind="CLAIM",
                    excerpt="increased government regulation and delays in approvals " * 3,
                    dimension="regulatory",
                    er_lens="ER5",
                ),
            ],
        ),
        force_primary="A8",
    )
    er5 = next(e for e in report.er_lenses if e.lens_id == "ER5")
    joined = " ".join(report.regulatory_geo_bullets or []).lower()
    assert "environmental" in joined or "permitting" in joined
    # Coverage is filing CLAIM under ER5 — explicitly not an ESG vendor score gate
    assert "not esg vendor grade" in joined or "environmental/permitting coverage" in joined
    assert report.terminates_later_stages is False
    assert er5.evidence_label in {"CLAIM", "FACT", "INFERENCE", "UNKNOWN"}
