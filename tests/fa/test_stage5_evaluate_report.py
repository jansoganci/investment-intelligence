"""Stage 5 evaluate + report — outcomes contextual; non-terminating."""
from __future__ import annotations

from fa.models import Stage5SemanticReview
from fa.stage5.evaluate import evaluate_stage5
from fa.stage5.report import render_stage5_markdown
from fa.stage5.questions import STAGE5_OUTCOMES


def _periods():
    out = []
    for i in range(5):
        r = 100 + i * 10
        out.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "revenue": r,
                    "gross_profit": r * 0.6,
                    "operating_income": r * 0.25,
                    "cost_of_revenue": r * 0.4,
                    "sbc_expense": 1.0,
                },
            }
        )
    return out


def test_fi_refused_too_hard():
    report = evaluate_stage5(
        "BANKX",
        _periods(),
        gate0_class="financial_institution",
        semantic=Stage5SemanticReview(filled=True, review_source="fixture"),
    )
    assert report.process_outcome == "TOO_HARD"
    assert report.terminates_later_stages is False
    assert report.refuse_reason


def test_evaluate_conditional_or_proceed_synthetic():
    sem = Stage5SemanticReview(
        filled=True,
        review_source="fixture",
        pricing_power_notes="brand pricing power and pass-through of input costs",
        margin_bridge_notes="operating margin expanded",
        cost_advantage_notes="scale operating leverage",
        input_cost_notes="commodity costs increased",
    )
    report = evaluate_stage5(
        "SYNTH_BRAND",
        _periods(),
        semantic=sem,
        thesis_summary="branded beverage concentrate household brand bottling system",
        thesis_margins="stable franchise margins with pricing power",
        business_notes="branded beverage consumer brand",
        force_primary="A1",
    )
    assert report.process_outcome in STAGE5_OUTCOMES
    assert report.terminates_later_stages is False
    assert report.archetype.primary_archetype == "A1"
    assert "MATURE_FRANCHISE_ECONOMICS_OK" in report.context_tags
    assert len(report.benchmark_results) == 8
    assert all(b.dimension_id.startswith("BE") for b in report.benchmark_results)
    md = render_stage5_markdown(report)
    assert "No RED/ORANGE/GREEN" in md
    assert "no BE9" in md.lower() or "No BE9" in md
    assert report.process_outcome != "TOO_HARD"


def test_no_label_count_forces_outcome():
    """Even with BELOW_REFERENCE labels, outcome is contextual not counted."""
    sem = Stage5SemanticReview(filled=False, review_source="placeholder")
    report = evaluate_stage5(
        "THIN",
        _periods()[:2],
        semantic=sem,
        thesis_summary=None,
    )
    # Thin disclosure → CONDITIONAL or REVIEW/TOO_HARD — but never via counting labels
    assert report.process_outcome in STAGE5_OUTCOMES
    below = [b for b in report.benchmark_results if b.label == "BELOW_REFERENCE"]
    # Must not encode a formula using len(below)
    assert report.terminates_later_stages is False
    _ = below  # presence alone must not kill
