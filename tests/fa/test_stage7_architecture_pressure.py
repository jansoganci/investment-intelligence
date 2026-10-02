"""Architecture pressure with SYNTHETIC fixtures (no production ticker hardcodes)."""
from __future__ import annotations

from fa.models import Stage7SemanticFinding, Stage7SemanticReview
from fa.stage7.evaluate import evaluate_stage7
from fa.stage7.archetype import adapt_from_prior, a7_or_acquisitive


def _sem(**notes):
    findings = notes.pop("findings", None) or []
    filled = notes.pop("filled", True)
    return Stage7SemanticReview(
        filled=filled, review_source="fixture", findings=findings, **notes
    )


def _cash_periods(
    *,
    capex=None,
    acq=None,
    div=None,
    buyback=None,
    sbc=None,
    shares=None,
    debt=None,
    n=5,
    base_year=2021,
):
    out = []
    for i in range(n):
        sh = None if shares is None else shares[i] if isinstance(shares, list) else shares
        fields = {
            "operating_cash_flow": 1000 + i * 50,
            "capex": None if capex is None else (capex if not isinstance(capex, list) else capex[i]),
            "business_acquisitions_cash": None
            if acq is None
            else (acq if not isinstance(acq, list) else acq[i]),
            "dividends_paid": None
            if div is None
            else (div if not isinstance(div, list) else div[i]),
            "share_repurchases": None
            if buyback is None
            else (buyback if not isinstance(buyback, list) else buyback[i]),
            "sbc_expense": None if sbc is None else (sbc if not isinstance(sbc, list) else sbc[i]),
            "shares_outstanding": sh,
            "total_debt": None
            if debt is None
            else (debt if not isinstance(debt, list) else debt[i]),
            "operating_income": 200 + i * 10,
            "total_assets": 5000 + i * 200,
        }
        out.append(
            {
                "period_key": f"FY{base_year+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": fields,
            }
        )
    return out


def test_synthetic_a7_consumes_s6_flags_no_guilt():
    """A7 + S6 opacity → MG3 depth; REVIEW_REQUIRED candidate; no mechanical bad-manager; NON-TERMINATING."""
    report = evaluate_stage7(
        "synthetic_acq_compounder",
        _cash_periods(acq=[500, 800, 1200, 900, 1100], div=50, buyback=100, shares=[100, 101, 102, 103, 104], debt=[2000, 2500, 3000, 3200, 3500]),
        semantic=_sem(
            stated_hierarchy_notes="Priority: bolt-on acquisitions then organic reinvestment then dividends",
            deal_criteria_notes="bolt-on acquisitions with strategic fit and integration playbook",
            incentive_metrics_notes="PSU tied to adjusted EBITDA and relative TSR",
            governance_structure_notes="independent board majority",
            guidance_delivery_notes="reaffirmed full-year guidance",
            succession_notes="board reviews CEO succession annually",
            findings=[
                Stage7SemanticFinding(
                    topic="deal_criteria",
                    evidence_kind="MANAGEMENT_CLAIM",
                    excerpt="bolt-on acquisitions integration",
                    dimension="ma",
                ),
                Stage7SemanticFinding(
                    topic="incentive_metrics",
                    evidence_kind="FACT",
                    excerpt="PSU adjusted EBITDA",
                    dimension="incentives",
                    classification="def14a",
                ),
                Stage7SemanticFinding(
                    topic="guidance_delivery",
                    evidence_kind="GUIDANCE",
                    excerpt="reaffirmed guidance",
                    dimension="comm",
                ),
            ],
        ),
        thesis_summary="acquisitive compounder niche software",
        thesis_capital="deploy capital via bolt-on M&A",
        force_primary="A7",
        prior_archetype={
            "primary_archetype": "A7",
            "primary_label": "Acquisitive compounder",
            "secondary_traits": ["acquisitive", "recurring_revenue"],
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
            "why": "synthetic",
        },
        stage6_artifact={
            "process_outcome": "REVIEW_REQUIRED",
            "runway_label": "unclear",
            "stage7_handoff_flags": [
                "S6_H7_DUAL_VIEW_CONFLICT",
                "S6_H7_ACQ_RETURN_OPACITY",
            ],
            "archetype": {"primary_archetype": "A7"},
        },
    )
    assert report.archetype.primary_archetype == "A7"
    assert report.a7_mg3_depth_required is True
    assert "S6_H7_ACQ_RETURN_OPACITY" in report.s6_handoff_flags_consumed
    assert "S6_H7_DUAL_VIEW_CONFLICT" in report.s6_handoff_flags_consumed
    assert report.terminates_later_stages is False
    assert report.process_outcome in {"REVIEW_REQUIRED", "CONDITIONAL"}
    # No mechanical guilt language as outcome formula — outcome is process enum only
    assert report.process_outcome != "TOO_HARD"
    mg3 = next(m for m in report.mg_lenses if m.lens_id == "MG3")
    assert mg3.labels.get("no_return_recalc") is True
    assert any(t.get("id") == "FP-M12" for t in report.false_positive_tags)


def test_synthetic_buyback_sbc_gross_and_net():
    """Distributions: gross repurchase + net share + SBC honesty; no payout threshold."""
    report = evaluate_stage7(
        "synthetic_buyback_sbc",
        _cash_periods(
            buyback=[200, 300, 400, 500, 600],
            sbc=[80, 90, 100, 110, 120],
            shares=[1000, 990, 985, 980, 970],  # net decline despite SBC
            div=0,
            acq=0,
            capex=-40,
        ),
        semantic=_sem(
            stated_hierarchy_notes="Return excess capital via share repurchases to offset dilution",
            buyback_policy_notes="offset dilutive effect of share-based awards",
            incentive_metrics_notes="RSU and PSU program",
            dividend_policy_notes="",
            findings=[
                Stage7SemanticFinding(
                    topic="buyback_policy",
                    evidence_kind="MANAGEMENT_CLAIM",
                    excerpt="offset dilutive effect of SBC",
                ),
            ],
        ),
        force_primary="A2",
    )
    share = report.calc.metrics["share_trend"]
    assert share["gross_and_net_both_shown_when_available"] is True
    assert share["no_payout_threshold"] is True
    assert share["gross_repurchase_multi_year"] is not None
    assert share["net_share_change"] is not None
    assert share["net_share_change"] < 0  # net share decline
    assert share["sbc_expense_multi_year"] is not None
    assert any(t.get("id") == "FP-M2" for t in report.false_positive_tags)
    assert any(t.get("id") == "FP-M13" for t in report.false_positive_tags)
    assert report.terminates_later_stages is False
    # No ROIC fields invented
    assert "roic" not in str(report.calc.metrics).lower() or report.calc.metrics.get(
        "no_roic_recompute"
    )


def test_no_mechanical_s6_guilt_conversion():
    """S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST → REVIEW_REQUIRED candidate, not auto bad-manager score."""
    report = evaluate_stage7(
        "synthetic_destruction_flag",
        _cash_periods(acq=100, capex=-50, div=20, buyback=10, shares=50),
        semantic=_sem(
            stated_hierarchy_notes="Reinvest in the business first",
            filled=True,
        ),
        force_primary="A5",
        stage6_artifact={
            "runway_label": "ample",
            "stage7_handoff_flags": ["S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST"],
        },
    )
    assert "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST" in report.s6_handoff_flags_consumed
    assert report.process_outcome == "REVIEW_REQUIRED"
    assert report.terminates_later_stages is False
    # Must not invent a management score field
    assert not hasattr(report, "management_score")
    blob = " ".join(report.s6_handoff_bullets).lower()
    assert "no mechanical" in blob or "not mechanical" in blob


def test_mg_set_locked_names():
    report = evaluate_stage7(
        "synthetic_names",
        _cash_periods(div=30, buyback=20),
        semantic=_sem(filled=True, stated_hierarchy_notes="dividends then buybacks"),
        force_primary="A1",
    )
    names = [(m.lens_id, m.lens_name) for m in report.mg_lenses]
    assert names[0] == ("MG1", "Capital Allocation Coherence")
    assert names[3] == ("MG4", "Shareholder Distributions")
    assert names[8] == ("MG9", "Succession / Key-Person")
    assert len(names) == 9


def test_fi_gate0_refuses_too_hard():
    report = evaluate_stage7(
        "synthetic_bank",
        _cash_periods(),
        gate0_class="financial_institution",
    )
    assert report.process_outcome == "TOO_HARD"
    assert report.terminates_later_stages is False
    assert report.refuse_reason


def test_comm_taxonomy_kinds():
    report = evaluate_stage7(
        "synthetic_comm",
        _cash_periods(div=10),
        semantic=_sem(
            filled=True,
            guidance_delivery_notes="company expects revenue to grow; reaffirmed guidance",
            findings=[
                Stage7SemanticFinding(topic="guidance_delivery", evidence_kind="GUIDANCE", excerpt="expects revenue"),
                Stage7SemanticFinding(topic="stated_hierarchy", evidence_kind="MANAGEMENT_CLAIM", excerpt="capital allocation priority"),
                Stage7SemanticFinding(topic="dividend_policy", evidence_kind="FACT", excerpt="quarterly dividend", classification="mdna"),
                Stage7SemanticFinding(topic="filing_retrieval", evidence_kind="SYSTEM_INFERENCE", excerpt="unavailable"),
            ],
        ),
        force_primary="A1",
    )
    kinds = set()
    for f in report.semantic.findings:
        kinds.add(f.evidence_kind)
    assert "FACT" in kinds
    assert "GUIDANCE" in kinds
    assert "MANAGEMENT_CLAIM" in kinds
    assert "SYSTEM_INFERENCE" in kinds
    mg8 = next(m for m in report.mg_lenses if m.lens_id == "MG8")
    assert "execution_tag" in mg8.labels


def test_adapt_a7_depth():
    adapted = adapt_from_prior(
        {
            "primary_archetype": "A7",
            "primary_label": "Acquisitive compounder",
            "secondary_traits": ["acquisitive"],
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
            "why": "from stage6",
        }
    )
    assert adapted.primary_archetype == "A7"
    assert a7_or_acquisitive(adapted.primary_archetype, adapted.secondary_traits)
    assert any(d["id"] == "mg3_mandatory_depth" for d in adapted.model_specific_drivers)


def test_mg6_toc_or_shallow_cda_is_not_pass():
    """Weak/TOC CD&A presence must not become MG6 PASS merely because a proxy exists."""
    from fa.stage7.benchmark import label_benchmarks
    from fa.stage7.semantic import incentive_evidence_depth

    toc_sem = _sem(
        filled=True,
        incentive_metrics_notes=(
            "COMPENSATION AND SECURITY OWNERSHIP Executive Compensation, Including "
            "Compensation Discussion and Analysis 39 Report of the Compensation "
            "Committee 59 Director Compensation 60 Security Ownership of Certain"
        ),
        ownership_guidelines_notes=(
            "Robust stock ownership guidelines that require our executive officers "
            "to maintain significant ownership of our common stock"
        ),
        findings=[
            Stage7SemanticFinding(
                topic="incentive_metrics",
                evidence_kind="FACT",
                excerpt=(
                    "COMPENSATION AND SECURITY OWNERSHIP Executive Compensation, "
                    "Including Compensation Discussion and Analysis 39 Report of "
                    "the Compensation Committee 59 Director Compensation 60"
                ),
                classification="def14a",
                dimension="incentives",
            ),
            Stage7SemanticFinding(
                topic="ownership_guidelines",
                evidence_kind="FACT",
                excerpt=(
                    "Robust stock ownership guidelines that require our executive "
                    "officers to maintain significant ownership of our common stock"
                ),
                classification="def14a",
                dimension="incentives",
            ),
            Stage7SemanticFinding(
                topic="clawback",
                evidence_kind="FACT",
                excerpt=(
                    "Reviewing and approving policies and procedures with respect "
                    "to the clawback or recoupment of compensation from officers"
                ),
                classification="def14a",
                dimension="incentives",
            ),
        ],
    )
    depth = incentive_evidence_depth(toc_sem)
    assert depth["depth"] == "shallow"
    assert depth["presence"] is True

    report = evaluate_stage7(
        "synthetic_shallow_cda",
        _cash_periods(div=10, buyback=20, capex=-50),
        semantic=toc_sem,
        force_primary="A2",
        prior_archetype={
            "primary_archetype": "A2",
            "primary_label": "Asset-light compounder",
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
            "why": "synthetic",
        },
    )
    mg6 = next(b for b in report.benchmark_results if b.dimension_id == "MG6")
    assert mg6.label == "MIXED", mg6.why
    assert "shallow" in mg6.why.lower() or "toc" in mg6.why.lower()

    # Substantive CD&A spine → PASS
    subst = _sem(
        filled=True,
        incentive_metrics_notes=(
            "PSUs vest over a three-year period subject to a market modifier based "
            "on total shareholder return ranking versus the S&P 500; annual bonus "
            "metrics include organic revenue growth"
        ),
        ownership_guidelines_notes="Stock ownership guidelines: CEO 6x salary",
        findings=[
            Stage7SemanticFinding(
                topic="incentive_metrics",
                evidence_kind="FACT",
                excerpt=(
                    "PSUs vest over a three-year period subject to total shareholder "
                    "return ranking; annual bonus metrics include organic growth"
                ),
                classification="def14a",
                dimension="incentives",
            ),
        ],
    )
    assert incentive_evidence_depth(subst)["depth"] == "substantive"
    report2 = evaluate_stage7(
        "synthetic_substantive_cda",
        _cash_periods(div=10, buyback=20, capex=-50),
        semantic=subst,
        force_primary="A2",
    )
    mg6b = next(b for b in report2.benchmark_results if b.dimension_id == "MG6")
    assert mg6b.label == "PASS", mg6b.why


def test_a11_low_archetype_alone_does_not_force_review_required():
    """Archetype uncertainty must not mechanically escalate Stage 7 to REVIEW_REQUIRED."""
    report = evaluate_stage7(
        "synthetic_a11_low",
        _cash_periods(div=20, buyback=40, capex=-80),
        semantic=_sem(
            filled=True,
            stated_hierarchy_notes=(
                "investments in infrastructure and AI initiatives as well as any "
                "return of capital to stockholders"
            ),
            incentive_metrics_notes=(
                "PSU tied to adjusted EBITDA and relative TSR over a three-year period"
            ),
            ownership_guidelines_notes="CEO ownership guidelines 6x salary",
            governance_structure_notes="dual class structure of our common stock",
            succession_notes="board evaluates succession planning for key executives",
            buyback_policy_notes="board authorized a share repurchase program",
            dividend_policy_notes=(
                "declaration and payment of future dividends is at the sole "
                "discretion of our board of directors"
            ),
            findings=[
                Stage7SemanticFinding(
                    topic="incentive_metrics",
                    evidence_kind="FACT",
                    excerpt="PSU tied to adjusted EBITDA and relative TSR three-year",
                    classification="def14a",
                    dimension="incentives",
                ),
                Stage7SemanticFinding(
                    topic="related_party",
                    evidence_kind="FACT",
                    excerpt="Related Party Transactions 36 Report of the Audit Committee 37",
                    classification="proxy",
                    dimension="gov",
                    escalate_to_human=True,
                    materiality_judgment="watchable",
                ),
            ],
        ),
        force_primary="A11",
        prior_archetype={
            "primary_archetype": "A11",
            "primary_label": "Other / mixed",
            "classification_path": "REVIEW_REQUIRED",
            "confidence": "LOW",
            "ambiguity_notes": "No archetype keyword evidence — default A11",
            "why": "synthetic low-confidence A11",
            "provenance": "stage4_heuristic_via_stage6",
        },
        stage6_artifact={
            "process_outcome": "REVIEW_REQUIRED",
            "runway_label": "unclear",
            "stage7_handoff_flags": [],
            "archetype": {"primary_archetype": "A11", "confidence": "LOW"},
        },
    )
    assert report.archetype.primary_archetype == "A11"
    assert report.archetype.confidence == "LOW"
    # Must NOT be REVIEW_REQUIRED solely from A11 LOW / TOC related-party
    assert report.process_outcome != "REVIEW_REQUIRED", report.why_bullets
    assert report.process_outcome in {"PROCEED", "CONDITIONAL"}
    assert any("not mechanical REVIEW_REQUIRED" in m for m in report.monitors)
    assert not any(
        "archetype REVIEW_REQUIRED/low confidence" in b for b in report.why_bullets
    )


def test_mg8_unknown_execution_not_pass_on_taxonomy_alone():
    """Combined MG8 lens: taxonomy presence must not PASS when execution_tag=unknown."""
    # Communication half present (FACT + CLAIM) but no guidance/delivery evaluation → unknown
    report = evaluate_stage7(
        "synthetic_mg8_exec_unknown",
        _cash_periods(div=10, buyback=20, capex=-50),
        semantic=_sem(
            filled=True,
            stated_hierarchy_notes="investments in infrastructure then return of capital",
            buyback_policy_notes="board authorized a share repurchase program",
            governance_structure_notes="dual class structure of our common stock",
            # intentionally no guidance_delivery_notes / guidance_delivery findings
            findings=[
                Stage7SemanticFinding(
                    topic="stated_hierarchy",
                    evidence_kind="MANAGEMENT_CLAIM",
                    excerpt="investments in infrastructure and return of capital",
                    classification="mdna",
                    dimension="hierarchy",
                ),
                Stage7SemanticFinding(
                    topic="governance_structure",
                    evidence_kind="FACT",
                    excerpt="dual class structure of our common stock",
                    classification="proxy",
                    dimension="gov",
                ),
            ],
        ),
        force_primary="A2",
    )
    mg8 = next(b for b in report.benchmark_results if b.dimension_id == "MG8")
    lens = next(m for m in report.mg_lenses if m.lens_id == "MG8")
    assert lens.labels.get("execution_tag") == "unknown", lens.labels
    assert mg8.label == "MIXED", mg8.why
    assert "execution_tag=unknown" in mg8.why
    assert "combined lens" in mg8.why.lower() or "taxonomy" in mg8.why.lower()

    # Evaluated delivery with thin history → insufficient_history may still PASS
    report2 = evaluate_stage7(
        "synthetic_mg8_insufficient_history",
        _cash_periods(div=10, buyback=20, capex=-50),
        semantic=_sem(
            filled=True,
            guidance_delivery_notes="prior outlook referenced; delivery history sparse",
            findings=[
                Stage7SemanticFinding(
                    topic="guidance_delivery",
                    evidence_kind="GUIDANCE",
                    excerpt="company provided full-year outlook",
                    dimension="comm",
                ),
                Stage7SemanticFinding(
                    topic="stated_hierarchy",
                    evidence_kind="MANAGEMENT_CLAIM",
                    excerpt="capital allocation priority reinvestment then distribute",
                    dimension="hierarchy",
                ),
                Stage7SemanticFinding(
                    topic="dividend_policy",
                    evidence_kind="FACT",
                    excerpt="quarterly dividend",
                    classification="mdna",
                    dimension="dist",
                ),
            ],
        ),
        force_primary="A1",
    )
    mg8b = next(b for b in report2.benchmark_results if b.dimension_id == "MG8")
    lens2 = next(m for m in report2.mg_lenses if m.lens_id == "MG8")
    assert lens2.labels.get("execution_tag") == "insufficient_history", lens2.labels
    assert mg8b.label == "PASS", mg8b.why

    # Delivered execution + taxonomy → PASS
    report3 = evaluate_stage7(
        "synthetic_mg8_delivered",
        _cash_periods(div=10),
        semantic=_sem(
            filled=True,
            guidance_delivery_notes="reaffirmed full-year guidance; delivered on CapEx program",
            findings=[
                Stage7SemanticFinding(
                    topic="guidance_delivery",
                    evidence_kind="GUIDANCE",
                    excerpt="reaffirmed full-year guidance",
                    dimension="comm",
                ),
                Stage7SemanticFinding(
                    topic="stated_hierarchy",
                    evidence_kind="FACT",
                    excerpt="share repurchase program authorized",
                    classification="mdna",
                    dimension="hierarchy",
                ),
            ],
        ),
        force_primary="A1",
    )
    mg8c = next(b for b in report3.benchmark_results if b.dimension_id == "MG8")
    assert next(m for m in report3.mg_lenses if m.lens_id == "MG8").labels.get(
        "execution_tag"
    ) == "delivered"
    assert mg8c.label == "PASS", mg8c.why
