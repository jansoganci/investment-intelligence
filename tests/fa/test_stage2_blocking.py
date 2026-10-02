"""Stage 2 process-level blocking — NOT ratio thresholds."""
from __future__ import annotations

from fa.models import StructuredSemanticReview
from fa.stage2.evaluate import evaluate_stage2


def _healthy_period():
    return {
        "period_key": "FY2025",
        "version_id": "v001",
        "period_type": "FY",
        "fields": {
            "cash_and_equivalents": 280_000_000,
            "short_term_investments": 60_000_000,
            "short_term_debt": 35_000_000,
            "long_term_debt": 340_000_000,
            "lease_liability_current": 16_000_000,
            "lease_liability_noncurrent": 80_000_000,
            "current_portion_ltd": 35_000_000,
            "total_current_assets": 540_000_000,
            "total_current_liabilities": 300_000_000,
            "total_assets": 2_100_000_000,
            "equity_parent": 1_150_000_000,
            "goodwill": 200_000_000,
            "intangibles": 95_000_000,
            "inventory": 130_000_000,
            "receivables": 190_000_000,
            "undrawn_revolver_or_liquidity_facilities": 200_000_000,
            "restricted_cash_amount": 20_000_000,
            "restricted_cash_flag": True,
            "debt_maturity_buckets": {"Y1": 50_000_000},
            "revenue": 1_100_000_000,
        },
    }


def test_high_debt_ratio_alone_does_not_block():
    """High debt ratio alone does NOT auto-block."""
    p = _healthy_period()
    # Make leverage look "high" descriptively
    p["fields"]["long_term_debt"] = 5_000_000_000
    p["fields"]["equity_parent"] = 100_000_000
    sem = StructuredSemanticReview(
        leverage_optional_vs_required="optional",
        going_concern_language=False,
        near_term_liquidity_failure_credible=False,
        filled=True,
        review_source="fixture",
    )
    report = evaluate_stage2("SYNTH_OPCO", [p], semantic=sem)
    assert report.process_outcome not in {
        "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY",
        "TOO_HARD",
    }
    # May be PROCEED or CONDITIONAL — but not blocked solely by ratio
    assert report.block_next is False or report.process_outcome == "CONDITIONAL"


def test_going_concern_blocks():
    p = _healthy_period()
    sem = StructuredSemanticReview(
        going_concern_language=True,
        going_concern_excerpt="Substantial doubt about going concern",
        filled=True,
        review_source="fixture",
    )
    report = evaluate_stage2("SYNTH_OPCO", [p], semantic=sem)
    assert report.process_outcome == "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY"
    assert report.block_next is True


def test_wrong_gate0_too_hard():
    p = _healthy_period()
    report = evaluate_stage2(
        "BANKX",
        [p],
        gate0_class="financial_institution",
        semantic=StructuredSemanticReview(filled=True),
    )
    assert report.process_outcome == "TOO_HARD"
    assert report.block_next is True


def test_missing_periods_too_hard():
    report = evaluate_stage2(
        "SYNTH_OPCO",
        [],
        missing_critical_evidence=True,
        semantic=StructuredSemanticReview(filled=False),
    )
    assert report.process_outcome == "TOO_HARD"
    assert report.block_next is True


def test_unresolved_conflict_review_required_blocks_next():
    p = _healthy_period()
    report = evaluate_stage2(
        "SYNTH_OPCO",
        [p],
        unresolved_major_conflict=True,
        semantic=StructuredSemanticReview(filled=True, leverage_optional_vs_required="optional"),
    )
    assert report.process_outcome == "REVIEW_REQUIRED"
    assert report.block_next is True


def test_credible_liquidity_failure_blocks():
    p = _healthy_period()
    sem = StructuredSemanticReview(
        near_term_liquidity_failure_credible=True,
        near_term_liquidity_notes="Maturity wall with no refinance path",
        filled=True,
    )
    report = evaluate_stage2("SYNTH_OPCO", [p], semantic=sem)
    assert report.process_outcome == "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY"
    assert report.block_next is True


def test_no_stage3_symbol_in_evaluate_module():
    import fa.stage2.evaluate as ev
    import fa.pipeline as pipe

    assert not hasattr(ev, "stage3")
    assert not hasattr(pipe, "run_stage3")
    assert "stage3" not in dir(pipe)
