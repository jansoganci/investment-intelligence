"""Unit tests for Stage 6 deterministic ROIC / IC / incremental exhibits."""
from __future__ import annotations

from fa.stage6.calc import (
    compute_ic_inclusive,
    compute_nopat,
    compute_stage6_metrics,
    resolve_tax_rate,
    sane_etr,
    _classify_incremental,
)


def test_sane_etr_band():
    assert sane_etr(100.0, 21.0) == 0.21
    assert sane_etr(100.0, 70.0) is None  # > 60%
    assert sane_etr(-10.0, 5.0) is None  # loss year
    assert sane_etr(None, 5.0) is None


def test_resolve_tax_rate_median_then_statutory():
    fields = [
        {"pretax_income": 100, "income_tax": 20},
        {"pretax_income": 100, "income_tax": 22},
        {"pretax_income": 100, "income_tax": 24},
    ]
    r = resolve_tax_rate(fields)
    assert r["tax_rate_source"] == "median_sane_etr"
    assert abs(r["tax_rate"] - 0.22) < 1e-9

    r2 = resolve_tax_rate([{"pretax_income": -5, "income_tax": 1}])
    assert r2["tax_rate_source"] == "statutory_fallback"
    assert r2["tax_rate"] == 0.21


def test_nopat_basic():
    n = compute_nopat(100.0, 0.21, tax_rate_source="statutory_fallback")
    assert abs(n["nopat"] - 79.0) < 1e-9
    assert n["null_reason"] is None
    missing = compute_nopat(None, 0.21)
    assert missing["nopat"] is None
    assert missing["null_reason"] == "UNKNOWN"


def test_ic_excludes_cash_and_includes_gw():
    fields = {
        "total_assets": 1000,
        "cash_and_equivalents": 50,
        "short_term_investments": 10,
        "accounts_payable": 40,
        "deferred_revenue_current": 30,
        "goodwill": 200,
        "intangibles": 100,
        "lease_liability_current": 5,
        "lease_liability_noncurrent": 15,
    }
    ic = compute_ic_inclusive(fields)
    # 1000 - 50 - 10 - 0 - (40+30) = 870; lease liab NOT in NIBOL
    assert abs(ic["ic_inclusive"] - 870.0) < 1e-9
    assert ic["nibol_info"]["nibol"] == 70
    assert ic["components"]["goodwill_included"] == 200


def test_delta_ic_near_zero_not_meaningful():
    w = _classify_incremental(10.0, 0.0, window_id="t")
    assert w.meaning_class == "not_meaningful"
    assert w.incremental_roic is None


def test_compute_stage6_metrics_dual_and_incremental():
    rows = []
    for i in range(5):
        rows.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "operating_income": 100 + i * 10,
                    "pretax_income": 90 + i * 10,
                    "income_tax": 20 + i,
                    "total_assets": 1000 + i * 100,
                    "cash_and_equivalents": 50,
                    "accounts_payable": 40,
                    "deferred_revenue_current": 20,
                    "goodwill": 200,
                    "intangibles": 100,
                    "capex": -30,
                    "depreciation_amortization": 25,
                    "equity_parent": 500,
                    "total_debt": 300,
                    "inventory": 10,
                    "receivables": 30,
                },
            }
        )
    calc = compute_stage6_metrics(rows, dual_view_mandatory=True)
    m = calc.metrics
    assert m["no_numeric_roic_thresholds"] is True
    assert m["incremental_roic_ne_iom"] is True
    assert m["no_forced_maint_capex"] is True
    dual = m["dual_roic"]
    assert dual["dual_view_emitted"] is True
    assert dual["dual_view_mandatory"] is True
    assert dual["roic_inclusive"] is not None
    assert dual["roic_tangible"] is not None
    assert dual["tangible_ne_ma_success"] is True
    assert m["incremental_roic_windows"]
    assert any(w["window_id"] == "yoy_1y" for w in m["incremental_roic_windows"])
    assert m["reinvestment_composition"]["maint_growth_split"] == "UNKNOWN"


def test_delta_ic_tiny_vs_ic_base_not_meaningful():
    """Tiny ΔIC vs large IC base → not_meaningful (capital-light pathology)."""
    w = _classify_incremental(
        300_000_000.0,
        -150_000_000.0,  # small vs ~80B IC; large vs ΔNOPAT scale alone
        window_id="yoy_1y",
        ic_base=80_000_000_000.0,
    )
    assert w.meaning_class == "not_meaningful"
    assert "delta_ic_near_zero" in w.honesty_flags
    assert "delta_ic_tiny_vs_ic_base" in w.honesty_flags
    assert w.incremental_roic is None


def test_negative_delta_ic_rising_nopat_honesty():
    """Material negative ΔIC with rising NOPAT → noisy/distorted honesty, not auto-excellent."""
    w = _classify_incremental(
        500.0,
        -200.0,  # material vs both sides; not near-zero
        window_id="yoy_1y",
        ic_base=1000.0,  # |ΔIC|/IC = 0.2 > 0.01
    )
    assert w.meaning_class in {"noisy", "distorted"}
    assert "negative_delta_ic_capital_released" in w.honesty_flags
    assert w.incremental_roic is not None
