"""Unit tests for Stage 5 deterministic margin exhibits — no bands, no ROIC."""
from __future__ import annotations

from fa.stage5.calc import compute_stage5_metrics, incremental_om, margin_ratio


def test_margin_ratio_basic():
    r = margin_ratio(30.0, 100.0)
    assert r["value"] == 0.3
    assert r["null_reason"] is None


def test_margin_ratio_nulls():
    assert margin_ratio(None, 100)["null_reason"] == "UNKNOWN"
    assert margin_ratio(10, 0)["null_reason"] == "BASE_ZERO"


def test_incremental_om_reported():
    w = incremental_om(10.0, 50.0, window_id="yoy", from_period="FY1", to_period="FY2")
    assert w.incremental_om == 0.2
    assert w.posture_class == "reported"
    assert "Stage 6" in (w.stage6_handoff or "")


def test_incremental_om_zero_rev():
    w = incremental_om(5.0, 0.0, window_id="z")
    assert w.incremental_om is None
    assert w.null_reason == "BASE_ZERO"
    assert "distorted" in w.posture_class or w.posture_class == "distorted"


def _periods():
    rows = []
    revs = [100, 110, 120, 130, 140]
    ops = [20, 23, 26, 28, 32]
    gps = [40, 44, 48, 52, 56]
    for i, (r, o, g) in enumerate(zip(revs, ops, gps)):
        rows.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "revenue": r,
                    "operating_income": o,
                    "gross_profit": g,
                    "cost_of_revenue": r - g,
                    "sbc_expense": 2.0,
                },
            }
        )
    return rows


def test_compute_stage5_metrics_exhibits():
    calc = compute_stage5_metrics(_periods())
    m = calc.metrics
    assert m["n_fy"] == 5
    assert m["no_numeric_bands"] is True
    assert m["no_roic"] is True
    assert m["incremental_om_ne_roiic"] is True
    latest = m["latest_margins"]
    assert abs(latest["gross_margin"] - 0.4) < 1e-9
    assert abs(latest["operating_margin"] - (32 / 140)) < 1e-9
    assert m["incremental_om_windows"]
    yoy = m["incremental_om_windows"][0]
    assert yoy["window_id"] == "yoy_latest_fy"
    assert yoy["incremental_om"] is not None


def test_compute_derived_gp_when_missing():
    periods = [
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "version_id": "v1",
            "fields": {"revenue": 100, "cost_of_revenue": 60, "operating_income": 15},
        }
    ]
    calc = compute_stage5_metrics(periods)
    latest = calc.metrics["latest_margins"]
    assert latest["gross_profit"] == 40
    assert latest["gross_profit_source"] == "derived_rev_minus_cor"
    assert abs(latest["gross_margin"] - 0.4) < 1e-9
