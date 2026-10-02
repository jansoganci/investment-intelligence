"""Deterministic Stage 4 calc — YoY, CAGR, per-share, decomp arithmetic, nulls."""
from __future__ import annotations

from fa.stage4.calc import (
    assemble_decomposition_arithmetic,
    cagr,
    compute_stage4_metrics,
    per_share,
    yoy_change,
)


def _p(pk, fields, period_type="FY", **extra):
    doc = {
        "period_key": pk,
        "period_type": period_type,
        "version_id": "v001",
        "fields": fields,
        "field_uncertainty": {},
        "lineage": [],
    }
    doc.update(extra)
    return doc


def test_yoy_and_cagr_arithmetic():
    assert yoy_change(110, 100)["fraction"] == 0.1
    assert yoy_change(100, 0)["null_reason"] == "BASE_ZERO"
    assert abs(cagr(100, 121, 2)["cagr"] - 0.1) < 1e-9
    assert cagr(-1, 10, 2)["null_reason"] == "NON_POSITIVE_BASE"


def test_per_share_and_share_trend():
    periods = [
        _p("FY2023", {"revenue": 1000, "net_income": 100, "shares_diluted_weighted": 100,
                       "operating_cash_flow": 120, "capex": 20}),
        _p("FY2024", {"revenue": 1100, "net_income": 110, "shares_diluted_weighted": 95,
                       "operating_cash_flow": 130, "capex": 25}),
        _p("FY2025", {"revenue": 1210, "net_income": 121, "shares_diluted_weighted": 90,
                       "operating_cash_flow": 140, "capex": 30}),
    ]
    r = compute_stage4_metrics(periods)
    assert r.metrics["share_count_direction"] == "down"
    assert r.metrics["n_fy"] == 3
    latest_ps = r.metrics["per_share_exhibit"][-1]
    assert latest_ps["revenue_per_share"]["value"] == 1210 / 90
    assert latest_ps["fcf_per_share"]["value"] == (140 - 30) / 90


def test_multi_year_cagr_exhibits():
    periods = [
        _p(f"FY{y}", {"revenue": 100 * (1.05 ** (y - 2020)), "net_income": 10})
        for y in range(2020, 2026)
    ]
    r = compute_stage4_metrics(periods)
    assert r.metrics["revenue_cagr_5y"]["cagr"] is not None
    assert r.metrics["revenue_cagr_3y"]["cagr"] is not None
    assert r.metrics["revenue_path_consistency"] == "all_up"


def test_decomposition_uses_disclosed_only_no_invention():
    prior = _p("FY2024", {"revenue": 100})
    curr = _p(
        "FY2025",
        {
            "revenue": 110,
            "revenue_organic_growth_yoy": 0.08,
            "revenue_acquired_impact_yoy": 0.02,
            "constant_currency_revenue_growth_yoy": 0.09,
        },
    )
    d = assemble_decomposition_arithmetic(curr, prior)
    assert d.reported_revenue_change_pct == 0.1
    dims = {c["dimension"] for c in d.components}
    assert "organic" in dims and "acquisition" in dims and "FX" in dims
    assert all(c["evidence_tag"] == "FACT" for c in d.components)

    bare = assemble_decomposition_arithmetic(_p("FY2025", {"revenue": 110}), prior)
    assert "UNKNOWN" in (bare.organic_vs_acquired_summary or "")
    assert bare.unattributed_or_unknown


def test_quarterly_path_and_thin_history_flag():
    periods = [
        _p("FY2024", {"revenue": 100}),
        _p("FY2025", {"revenue": 105}),
        _p("Q2025Q1", {"revenue": 25}, period_type="Q"),
        _p("Q2025Q2", {"revenue": 26}, period_type="Q"),
    ]
    r = compute_stage4_metrics(periods)
    assert r.metrics["n_q"] == 2
    assert r.metrics["history_flags"]["history_thin"] is True
    assert "history_depth" in r.null_reasons


def test_no_quality_threshold_constants_in_metrics():
    """Guard: calc must not emit pass/fail scores or NC* bands."""
    periods = [_p("FY2024", {"revenue": 100}), _p("FY2025", {"revenue": 108})]
    r = compute_stage4_metrics(periods)
    assert "score" not in r.metrics
    assert "blended_score" not in r.metrics
    assert "nc1_band" not in r.metrics
    assert "pass_fail" not in r.metrics
    blob = str(r.null_reasons).lower() + str(list(r.metrics.keys())).lower()
    assert "nc1" not in blob
    assert "hurdle" not in blob
