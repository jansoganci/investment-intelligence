"""Stage 9 deterministic helpers — concentration descriptors / cycle class."""
from __future__ import annotations

from fa.stage9.calc import (
    compute_stage9_metrics,
    descriptive_concentration_label,
    soft_cycle_position_class,
)


def test_descriptive_concentration_not_auto_fail():
    assert descriptive_concentration_label(opaque=True) == "unknown"
    assert descriptive_concentration_label(semantic_high=True) == "high"
    assert descriptive_concentration_label(semantic_extreme=True) == "extreme"
    assert descriptive_concentration_label(disclosed_pct=0.05, opaque=False) == "low"
    # thresholds packaging only — still not a gate
    assert descriptive_concentration_label(disclosed_pct=0.45) == "extreme"


def test_cycle_position_not_prediction():
    assert soft_cycle_position_class(primary_archetype="A1") == "unknown"
    assert soft_cycle_position_class(
        primary_archetype="A8", mid_cycle_honesty_flag=True
    ) == "mid"
    assert soft_cycle_position_class(
        primary_archetype="A9", peak_language=True
    ) == "late"


def test_compute_metrics_flags_and_axes():
    periods = [
        {
            "period_key": f"FY{y}",
            "period_type": "FY",
            "version_id": "v1",
            "fields": {"revenue": 100.0},
        }
        for y in range(2021, 2026)
    ]
    r = compute_stage9_metrics(
        periods,
        semantic_cues={"customer_high": True, "customer_opaque": False},
        primary_archetype="A3",
        s8_h9=["S8_H9_EXPECTATIONS_DEMANDING"],
    )
    assert r.metrics["n_fy"] == 5
    assert r.metrics["concentration_axes"]["customer"] == "high"
    assert r.metrics["concentration_no_auto_fail"] is True
    assert r.metrics["prepare_not_predict"] is True
    assert r.metrics["s8_h9_soft_linked"] == ["S8_H9_EXPECTATIONS_DEMANDING"]
    assert r.metrics["no_porter_score"] is True


def test_empty_periods_unknown():
    r = compute_stage9_metrics([])
    assert r.metrics["n_fy"] == 0
    assert "fy_spine" in r.null_reasons
