"""Deterministic Stage 3 calc — multi-period, WC, CapEx conflict, nulls."""
from __future__ import annotations

from fa.stage3.calc import compute_stage3_metrics


def _p(pk, fields, **extra):
    doc = {
        "period_key": pk,
        "period_type": "FY",
        "version_id": "v001",
        "fields": fields,
        "field_uncertainty": {},
        "lineage": [],
    }
    doc.update(extra)
    return doc


def test_fcf_ocf_minus_capex_with_lineage():
    periods = [
        _p("FY2024", {"operating_cash_flow": 100, "net_income": 80, "capex": 30}),
        _p("FY2025", {"operating_cash_flow": 120, "net_income": 90, "capex": 40}),
    ]
    r = compute_stage3_metrics(periods)
    assert r.metrics["latest_fcf"] == 80  # 120-40
    lin = r.metrics["latest_fcf_lineage"]
    assert lin["formula"] == "OCF - CapEx"
    assert lin["status"] == "ok"
    assert lin["fcf"] == 80


def test_capex_conflict_nulls_fcf():
    periods = [
        _p(
            "FY2025",
            {"operating_cash_flow": 120, "net_income": 90, "capex": 40},
            field_uncertainty={"capex": "CapEx taxonomy conflict: tags disagree"},
        )
    ]
    r = compute_stage3_metrics(periods)
    assert r.metrics["latest_fcf"] is None
    assert r.metrics["latest_capex_conflict"] is True
    assert "fcf:FY2025" in r.null_reasons


def test_multi_period_ocf_vs_ni_and_cumulative():
    periods = [
        _p("FY2023", {"operating_cash_flow": 50, "net_income": 40, "capex": 10}),
        _p("FY2024", {"operating_cash_flow": 60, "net_income": 55, "capex": 12}),
        _p("FY2025", {"operating_cash_flow": 70, "net_income": 50, "capex": 15}),
    ]
    r = compute_stage3_metrics(periods)
    assert len(r.metrics["ocf_vs_ni_series"]) == 3
    assert r.metrics["cumulative_ocf"] == 180
    assert r.metrics["cumulative_ni"] == 145
    assert r.metrics["cumulative_ocf_minus_ni"] == 35
    assert r.metrics["fcf_trend_direction"] in {"up", "down", "flat"}


def test_wc_deltas_including_ap_and_deferred():
    periods = [
        _p(
            "FY2024",
            {
                "receivables": 100,
                "inventory": 50,
                "accounts_payable": 40,
                "deferred_revenue_current": 10,
                "deferred_revenue_noncurrent": 5,
                "revenue": 1000,
                "operating_cash_flow": 1,
                "net_income": 1,
                "capex": 1,
            },
        ),
        _p(
            "FY2025",
            {
                "receivables": 120,
                "inventory": 55,
                "accounts_payable": 48,
                "deferred_revenue_current": 12,
                "deferred_revenue_noncurrent": 6,
                "revenue": 1100,
                "operating_cash_flow": 1,
                "net_income": 1,
                "capex": 1,
            },
        ),
    ]
    r = compute_stage3_metrics(periods)
    d = r.metrics["wc_deltas"][0]
    assert d["delta_receivables"] == 20
    assert d["delta_inventory"] == 5
    assert d["delta_accounts_payable"] == 8
    assert d["delta_deferred_revenue_total"] == 3
    assert d["delta_revenue"] == 100


def test_nulls_when_missing_fields():
    r = compute_stage3_metrics([_p("FY2025", {})])
    assert r.metrics["latest_fcf"] is None
    assert "fcf:FY2025" in r.null_reasons
    assert r.metrics["sbc_context"]["sbc_expense"] is None


def test_capex_da_and_sbc_context():
    periods = [
        _p(
            "FY2025",
            {
                "operating_cash_flow": 200,
                "net_income": 150,
                "capex": 80,
                "depreciation_amortization": 40,
                "sbc_expense": 10,
            },
        )
    ]
    r = compute_stage3_metrics(periods)
    assert r.metrics["latest_capex_to_da"] == 2.0
    assert r.metrics["sbc_context"]["sbc_expense"] == 10
    assert r.metrics["sbc_context"]["vs_ocf"] == 10 / 200


def test_empty_periods():
    r = compute_stage3_metrics([])
    assert "periods" in r.null_reasons
