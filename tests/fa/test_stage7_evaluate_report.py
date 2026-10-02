"""Stage 7 evaluate + markdown report smoke."""
from __future__ import annotations

from fa.models import Stage7SemanticReview
from fa.stage7.evaluate import evaluate_stage7
from fa.stage7.report import render_stage7_markdown
from fa.stage7.questions import STAGE7_OUTCOMES


def _periods():
    out = []
    for i, yr in enumerate(range(2021, 2026)):
        out.append(
            {
                "period_key": f"FY{yr}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "business_acquisitions_cash": 100 + i * 20,
                    "dividends_paid": 30,
                    "share_repurchases": 40 + i * 5,
                    "sbc_expense": 15,
                    "shares_outstanding": 200 - i,
                    "total_debt": 500 + i * 50,
                    "operating_cash_flow": 300,
                    "capex": -10,
                },
            }
        )
    return out


def test_evaluate_produces_eight_dashboard_blocks_and_outcome():
    report = evaluate_stage7(
        "synthetic_eval",
        _periods(),
        semantic=Stage7SemanticReview(
            filled=True,
            review_source="fixture",
            stated_hierarchy_notes="Reinvest organically; acquisitions; then dividends and buybacks",
            incentive_metrics_notes="Annual bonus on organic growth; PSU on ROIC and revenue",
            ownership_guidelines_notes="CEO ownership guidelines 6x salary",
            governance_structure_notes="majority independent directors",
            deal_criteria_notes="strategic fit bolt-on criteria",
            guidance_delivery_notes="reaffirmed full-year outlook",
            succession_notes="succession planning discussed annually by board",
            buyback_policy_notes="opportunistic share repurchase authorization",
            dividend_policy_notes="quarterly dividend policy with periodic increases",
            debt_motive_notes="financed the acquisition with debt under credit facility",
        ),
        thesis_summary="compounder with capital allocation optionality",
        thesis_capital="reinvest and selective M&A",
        force_primary="A7",
        prior_archetype={
            "primary_archetype": "A7",
            "primary_label": "Acquisitive compounder",
            "secondary_traits": ["acquisitive"],
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
            "why": "fixture",
        },
        stage6_artifact={
            "runway_label": "unclear",
            "stage7_handoff_flags": ["S6_H7_DUAL_VIEW_CONFLICT", "S6_H7_ACQ_RETURN_OPACITY"],
        },
    )
    assert report.process_outcome in STAGE7_OUTCOMES
    assert report.terminates_later_stages is False
    assert len(report.mg_lenses) == 9
    assert report.hierarchy_bullets
    assert report.s6_handoff_bullets
    assert report.ma_process_bullets
    assert report.distribution_bullets
    assert report.incentive_bullets
    assert report.communication_execution_bullets
    assert report.fp_gov_succession_bullets
    assert report.benchmark_results
    assert report.alignment_label in {"aligned", "tension", "opaque", "unknown"}
    md = render_stage7_markdown(report)
    assert "Dashboard 1" in md
    assert "Dashboard 8" in md
    assert "No RED/ORANGE/GREEN" in md
    assert "No ROIC/ROIIC/WACC recompute" in md
    assert report.mg_lenses[0].lens_name == "Capital Allocation Coherence"
    # Must questions answered
    must = [a for a in report.question_answers if a.must]
    assert len(must) == 10
    assert any(a.question_id == "S7-M10" for a in must)


def test_report_excludes_scores_and_stage8():
    report = evaluate_stage7(
        "synthetic_plain",
        _periods(),
        semantic=Stage7SemanticReview(filled=False, review_source="placeholder"),
        force_primary="A1",
    )
    md = render_stage7_markdown(report)
    assert "BUY" not in md or "No Stage 8 valuation / BUY-SELL" in md
    assert "averaged MG" in md.lower() or "No scores" in md
    assert "Stage 8" in md  # disclaimer only
    assert report.terminates_later_stages is False


def test_dividend_policy_label_does_not_overstate_commitment_from_bare_increase():
    """Bare increase + board discretion → residual; not commitment-like policy claim."""
    from fa.stage7.evaluate import _dividend_policy_label

    discretionary = Stage7SemanticReview(
        filled=True,
        dividend_policy_notes=(
            "Board increased the quarterly dividend 10%. This is the thirty-third "
            "consecutive year of increases. Future dividends will be at the sole "
            "discretion of our Board and will depend upon capital needs and other factors."
        ),
    )
    assert _dividend_policy_label(semantic=discretionary, div_years=5) == "residual"

    explicit = Stage7SemanticReview(
        filled=True,
        dividend_policy_notes="We maintain a dividend policy committed to annual increases.",
    )
    assert _dividend_policy_label(semantic=explicit, div_years=5) == "commitment-like"

    consecutive_no_discretion = Stage7SemanticReview(
        filled=True,
        dividend_policy_notes=(
            "The company increased its quarterly dividend. This is the tenth "
            "consecutive year in which the Company has increased its dividend."
        ),
    )
    assert (
        _dividend_policy_label(semantic=consecutive_no_discretion, div_years=5)
        == "commitment-like"
    )

    bare_increase = Stage7SemanticReview(
        filled=True,
        dividend_policy_notes="Board increased the quarterly dividend to $0.91 per share.",
    )
    assert _dividend_policy_label(semantic=bare_increase, div_years=3) == "residual"


def test_alignment_opaque_notes_proxy_retrieval_gap():
    from fa.models import Stage7SemanticFinding
    from fa.stage7.evaluate import _alignment_label

    sem = Stage7SemanticReview(
        filled=True,
        stated_hierarchy_notes=None,
        findings=[
            Stage7SemanticFinding(
                topic="filing_retrieval",
                section="DEF 14A",
                evidence_kind="SYSTEM_INFERENCE",
                materiality_judgment="unclear",
                escalate_to_human=True,
            )
        ],
    )
    label, why = _alignment_label(
        semantic=sem,
        hierarchy={"revealed_rank_desc": ["acquisitions"], "dominant_use": "acquisitions"},
        thesis_capital=None,
        s6_flags=[],
        runway_label="unclear",
    )
    assert label == "opaque"
    assert "retrieval gap" in why.lower() or "DEF 14A" in why


def test_dividend_policy_heading_alone_is_not_commitment_like():
    """Bare 'Dividend Policy' section heading must not force commitment-like."""
    from fa.stage7.evaluate import _dividend_policy_label

    heading_only = Stage7SemanticReview(
        filled=True,
        dividend_policy_notes=(
            "Dividend Policy Beginning in 2024, our board of directors declared "
            "quarterly cash dividends to the holders of our Class A and Class B "
            "common stock."
        ),
    )
    assert _dividend_policy_label(semantic=heading_only, div_years=2) == "residual"

    heading_with_discretion = Stage7SemanticReview(
        filled=True,
        dividend_policy_notes=(
            "Dividend Policy Beginning in 2024, our board declared quarterly cash "
            "dividends. Subject to legally available funds and future declaration by "
            "our board of directors, we currently intend to continue to pay a quarterly "
            "cash dividend. The declaration and payment of future dividends is at the "
            "sole discretion of our board of directors after taking into account "
            "various factors, including our financial condition and capital needs."
        ),
    )
    assert (
        _dividend_policy_label(semantic=heading_with_discretion, div_years=2) == "residual"
    )


def test_alignment_accepts_infra_return_of_capital_hierarchy_language():
    """CapEx/infra + return-of-capital stated language can align with revealed uses."""
    from fa.stage7.evaluate import _alignment_label

    sem = Stage7SemanticReview(
        filled=True,
        stated_hierarchy_notes=(
            "We fund cash commitments for investing activities, including investments "
            "in infrastructure and AI initiatives, as well as any return of capital to "
            "stockholders. Capital Return Program / share repurchase program continues."
        ),
    )
    hierarchy = {
        "revealed_rank_desc": ["organic_capex", "share_repurchases", "dividends"],
        "dominant_use": "organic_capex",
    }
    label, why = _alignment_label(
        semantic=sem,
        hierarchy=hierarchy,
        thesis_capital=None,
        s6_flags=[],
        runway_label="unclear",
    )
    assert label == "aligned", (label, why)
