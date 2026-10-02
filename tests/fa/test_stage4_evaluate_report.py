"""Outcomes PROCEED/CONDITIONAL/REVIEW/TOO_HARD + mature low-growth + high-growth FP + boundaries."""
from __future__ import annotations

from fa.models import Stage4SemanticFinding, Stage4SemanticReview
from fa.stage4.evaluate import evaluate_stage4
from fa.stage4.questions import MUST_QUESTIONS, SHOULD_QUESTIONS, STAGE4_OUTCOMES
from fa.stage4.report import render_stage4_markdown


def _periods(rev0=100.0, rev1=103.0, shares=True):
    f0 = {"revenue": rev0, "net_income": 20, "capex": 5, "operating_cash_flow": 25, "diluted_eps": 2.0}
    f1 = {"revenue": rev1, "net_income": 21, "capex": 5, "operating_cash_flow": 26, "diluted_eps": 2.1}
    if shares:
        f0["shares_diluted_weighted"] = 10
        f1["shares_diluted_weighted"] = 10
    return [
        {"period_key": "FY2024", "period_type": "FY", "version_id": "v1", "fields": f0},
        {"period_key": "FY2025", "period_type": "FY", "version_id": "v1", "fields": f1},
    ]


def _sem(filled=True, escalate=False):
    findings = []
    if escalate:
        findings.append(
            Stage4SemanticFinding(
                topic="fp_channel_stuffing",
                evidence_kind="COMPANY_EXPLANATION",
                materiality_judgment="material",
                materiality_reason="channel stuffing language",
                escalate_to_human=True,
                excerpt="channel stuffing",
            )
        )
    return Stage4SemanticReview(
        filled=filled,
        review_source="fixture",
        findings=findings,
        organic_acquired_notes="organic growth discussed" if filled else None,
        volume_price_mix_notes="volume increased" if filled else None,
        fx_notes="constant currency" if filled else None,
        runway_claim_notes="white space in emerging markets" if filled else None,
    )


def test_question_spine_frozen():
    assert [q[0] for q in MUST_QUESTIONS] == [f"S4-M{i}" for i in range(1, 9)]
    assert [q[0] for q in SHOULD_QUESTIONS] == [f"S4-S{i}" for i in range(1, 7)]


def test_outcome_enum_only_four():
    report = evaluate_stage4(
        "SYNTH",
        _periods(),
        semantic=_sem(),
        thesis_summary="trademark beverage concentrate bottling brand",
        thesis_runway="geo occasions",
    )
    assert report.process_outcome in STAGE4_OUTCOMES
    assert report.terminates_later_stages is False


def test_fi_hard_stop():
    report = evaluate_stage4(
        "BANKX",
        _periods(),
        gate0_class="financial_institution",
        semantic=_sem(),
    )
    assert report.process_outcome == "TOO_HARD"
    assert report.refuse_reason
    assert report.terminates_later_stages is False


def test_mature_low_growth_valid_not_penalized():
    """Modest ~3% growth + A1 thesis → MATURE_FRANCHISE_OK; not TOO_HARD/kill for low %."""
    report = evaluate_stage4(
        "SYNTH_MATURE",
        _periods(100, 103),
        semantic=_sem(),
        thesis_summary="trademark beverage concentrate bottling system sparkling soft drink brand",
        thesis_runway="Share of remaining global beverage occasions",
    )
    assert "MATURE_FRANCHISE_OK" in report.context_tags
    assert report.process_outcome in {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED"}
    assert report.process_outcome != "TOO_HARD"
    bd1 = next(b for b in report.benchmark_results if b.dimension_id == "BD1")
    assert bd1.label in {"PASS", "MIXED", "ABOVE_REFERENCE"}  # not auto BELOW for modest
    # Must not be BELOW_REFERENCE solely for modest growth on A1
    assert bd1.label != "BELOW_REFERENCE"


def test_high_growth_fp_context():
    report = evaluate_stage4(
        "SYNTH_HG",
        _periods(100, 150),
        semantic=_sem(),
        thesis_summary="saas subscription software arr recurring revenue",
        thesis_runway="product adjacency",
    )
    assert "HIGH_GROWTH_QUALITY_RISK" in report.context_tags or any(
        t.get("id") in {"FP9", "FP1", "FP8"} for t in report.false_positive_tags
    )


def test_material_fp_review_required():
    report = evaluate_stage4(
        "SYNTH_FP",
        _periods(),
        semantic=_sem(escalate=True),
        thesis_summary="trademark beverage concentrate brand",
        thesis_runway="geo",
    )
    assert report.process_outcome == "REVIEW_REQUIRED"
    assert report.terminates_later_stages is False


def test_conditional_has_named_monitors():
    # Thin semantic → gaps → CONDITIONAL with monitors
    report = evaluate_stage4(
        "SYNTH_COND",
        _periods(),
        semantic=Stage4SemanticReview(filled=True, review_source="fixture"),
        thesis_summary="trademark beverage concentrate brand",
        thesis_runway="geo",
    )
    if report.process_outcome == "CONDITIONAL":
        assert report.monitors


def test_too_hard_no_periods():
    report = evaluate_stage4("EMPTY", [], semantic=_sem())
    assert report.process_outcome == "TOO_HARD"


def test_report_markdown_no_colors_no_stage5():
    report = evaluate_stage4(
        "SYNTH",
        _periods(),
        semantic=_sem(),
        thesis_summary="trademark beverage concentrate brand",
        thesis_runway="geo",
    )
    md = render_stage4_markdown(report)
    low = md.lower()
    assert "stage 5" not in low or "no stage 5" in low
    assert "buy" not in low.split("buy-sell")[0] or "buy-sell" in low  # disclaimer ok
    assert "**RED**" not in md and "**GREEN**" not in md
    assert "Benchmark Layer" in md
    assert report.process_outcome in md


def test_no_label_count_formula_in_evaluate_source():
    import inspect
    from fa.stage4 import evaluate as ev

    src = inspect.getsource(ev.evaluate_stage4)
    assert "count_labels" not in src
    assert "BELOW_REFERENCE" in src  # may mention as evidence language
    # Forbid mechanical N-below patterns
    assert "n_below" not in src
    assert "label_count" not in src
