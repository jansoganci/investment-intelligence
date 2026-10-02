"""BE1–BE8 labeling — Method E; Benchmark ≠ hard gate."""
from __future__ import annotations

from fa.models import ArchetypeAdaptation, Stage5SemanticReview
from fa.stage5.benchmark import label_benchmarks, assess_pricing_power, _tag_false_positives
from fa.stage5.calc import compute_stage5_metrics


def _arch(primary="A1"):
    return ArchetypeAdaptation(
        primary_archetype=primary,
        primary_label="test",
        secondary_traits=["mature_franchise"],
        classification_path="AUTOMATED",
        confidence="HIGH",
        why="test",
    )


def _periods():
    out = []
    for i, (r, o, g) in enumerate([(100, 20, 40), (110, 24, 45), (120, 28, 50), (130, 30, 55)]):
        out.append(
            {
                "period_key": f"FY{2022+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {"revenue": r, "operating_income": o, "gross_profit": g},
            }
        )
    return out


def test_be1_through_be8_present():
    calc = compute_stage5_metrics(_periods())
    arch = _arch()
    sem = Stage5SemanticReview(
        filled=True,
        review_source="fixture",
        pricing_power_notes="pricing power and brand premium discussed",
        margin_bridge_notes="gross margin expanded on price/mix",
        cost_advantage_notes="operating leverage from scale",
    )
    pricing = assess_pricing_power(semantic=sem, archetype=arch, thesis_summary="branded beverage")
    from fa.stage5.benchmark import assess_durability

    fps = _tag_false_positives(calc_metrics=calc.metrics, semantic=sem, archetype=arch)
    dur = assess_durability(
        archetype=arch, semantic=sem, calc_metrics=calc.metrics, thesis_summary="brand", fp_tags=fps
    )
    bench, tags = label_benchmarks(
        calc_metrics=calc.metrics,
        archetype=arch,
        semantic=sem,
        pricing=pricing,
        durability=dur,
        fp_tags=fps,
        thesis_coherence="supports",
    )
    ids = [b.dimension_id for b in bench]
    assert ids == [f"BE{i}" for i in range(1, 9)]
    assert all(b.why for b in bench)
    assert "MATURE_FRANCHISE_ECONOMICS_OK" in tags
    assert pricing.posture in {"STRONG", "MODERATE", "MIXED", "WEAK", "UNKNOWN", "NOT_APPLICABLE"}
    # No BE9
    assert "BE9" not in ids


def test_ses_context_not_outcome():
    calc = compute_stage5_metrics(_periods())
    arch = _arch("A6")
    sem = Stage5SemanticReview(
        filled=True,
        review_source="fixture",
        ses_notes="scale economies shared with customers everyday low price",
    )
    pricing = assess_pricing_power(
        semantic=sem, archetype=arch, thesis_summary="retailer ses everyday low price"
    )
    from fa.stage5.benchmark import assess_durability

    fps = _tag_false_positives(calc_metrics=calc.metrics, semantic=sem, archetype=arch)
    dur = assess_durability(
        archetype=arch, semantic=sem, calc_metrics=calc.metrics, thesis_summary="ses", fp_tags=fps
    )
    bench, tags = label_benchmarks(
        calc_metrics=calc.metrics,
        archetype=arch,
        semantic=sem,
        pricing=pricing,
        durability=dur,
        fp_tags=fps,
        thesis_coherence="supports",
    )
    assert "SCALE_ECONOMIES_SHARED_OK" in tags
    assert "SCALE_ECONOMIES_SHARED_OK" not in {b.label for b in bench}
