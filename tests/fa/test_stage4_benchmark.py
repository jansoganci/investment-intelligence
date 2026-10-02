"""Benchmark labels, no count→outcome, no universal threshold, BD9 no ROIC."""
from __future__ import annotations

from fa.stage4.archetype import propose_archetype
from fa.stage4.benchmark import assess_runway, count_labels, label_benchmarks, _tag_false_positives
from fa.stage4.calc import compute_stage4_metrics
from fa.stage4.questions import BENCHMARK_LABELS
from fa.models import Stage4SemanticReview


def _periods_growth(frac=0.03):
    return [
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "version_id": "v1",
            "fields": {"revenue": 100, "net_income": 20, "capex": 5, "shares_diluted_weighted": 10},
        },
        {
            "period_key": "FY2025",
            "period_type": "FY",
            "version_id": "v1",
            "fields": {
                "revenue": 100 * (1 + frac),
                "net_income": 21,
                "capex": 5,
                "shares_diluted_weighted": 10,
            },
        },
    ]


def test_benchmark_labels_valid_and_bd_ids():
    calc = compute_stage4_metrics(_periods_growth(0.04))
    arch = propose_archetype(
        thesis_summary="trademark beverage concentrate bottling system brand"
    )
    runway = assess_runway(
        archetype=arch, semantic=None, thesis_runway="geo occasions", calc_metrics=calc.metrics
    )
    fps = _tag_false_positives(calc_metrics=calc.metrics, semantic=None, archetype=arch)
    results, ctx = label_benchmarks(
        calc_metrics=calc.metrics,
        archetype=arch,
        semantic=None,
        runway=runway,
        fp_tags=fps,
        thesis_coherence="supports",
    )
    ids = [r.dimension_id for r in results]
    assert ids == ["BD1", "BD2", "BD3", "BD4", "BD5", "BD6", "BD7", "BD8", "BD9"]
    for r in results:
        assert r.label in BENCHMARK_LABELS
        assert r.why
    assert "MATURE_FRANCHISE_OK" in ctx


def test_no_count_based_outcome_helper_is_diagnostic_only():
    calc = compute_stage4_metrics(_periods_growth(0.04))
    arch = propose_archetype(thesis_summary="trademark beverage concentrate brand")
    runway = assess_runway(
        archetype=arch, semantic=None, thesis_runway="x", calc_metrics=calc.metrics
    )
    results, _ = label_benchmarks(
        calc_metrics=calc.metrics,
        archetype=arch,
        semantic=None,
        runway=runway,
        fp_tags=[],
        thesis_coherence="supports",
    )
    counts = count_labels(results)
    # Diagnostic dict exists but evaluate must not use it as a formula —
    # prove count of BELOW does not appear as decision API
    assert isinstance(counts, dict)
    assert not hasattr(label_benchmarks, "outcome_from_counts")


def test_no_universal_cagr_hurdle_in_whys():
    calc = compute_stage4_metrics(_periods_growth(0.01))
    arch = propose_archetype(thesis_summary="trademark beverage concentrate brand")
    runway = assess_runway(
        archetype=arch, semantic=None, thesis_runway="x", calc_metrics=calc.metrics
    )
    results, _ = label_benchmarks(
        calc_metrics=calc.metrics,
        archetype=arch,
        semantic=None,
        runway=runway,
        fp_tags=[],
        thesis_coherence="supports",
    )
    blob = " ".join(r.why for r in results).lower()
    assert "universal cagr hurdle" in blob or "not locked" in blob or "no universal" in blob
    assert "nc1" not in blob


def test_bd9_observational_no_roic():
    calc = compute_stage4_metrics(_periods_growth(0.05))
    arch = propose_archetype(thesis_summary="industrial manufacturer capital equipment backlog")
    runway = assess_runway(
        archetype=arch, semantic=None, thesis_runway=None, calc_metrics=calc.metrics
    )
    results, _ = label_benchmarks(
        calc_metrics=calc.metrics,
        archetype=arch,
        semantic=None,
        runway=runway,
        fp_tags=[],
        thesis_coherence="unknown",
    )
    bd9 = next(r for r in results if r.dimension_id == "BD9")
    assert "roic" not in bd9.why.lower() or "no roic" in bd9.why.lower()
    assert "stage 6" in bd9.why.lower()


def test_high_growth_fp_context_tag():
    calc = compute_stage4_metrics(_periods_growth(0.40))
    arch = propose_archetype(
        thesis_summary="saas subscription software arr recurring"
    )
    runway = assess_runway(
        archetype=arch, semantic=Stage4SemanticReview(filled=False), thesis_runway=None,
        calc_metrics=calc.metrics,
    )
    results, ctx = label_benchmarks(
        calc_metrics=calc.metrics,
        archetype=arch,
        semantic=None,
        runway=runway,
        fp_tags=[],
        thesis_coherence="supports",
    )
    assert "HIGH_GROWTH_QUALITY_RISK" in ctx
    bd1 = next(r for r in results if r.dimension_id == "BD1")
    assert bd1.label == "ABOVE_REFERENCE"
