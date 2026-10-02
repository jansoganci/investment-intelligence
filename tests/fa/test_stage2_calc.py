"""Deterministic Stage 2 calc — null+reason when dishonest; no threshold blocking."""
from __future__ import annotations

from fa.stage2.calc import compute_stage2_metrics


def _doc(fields):
    return {"period_key": "FY2025", "version_id": "v001", "fields": fields}


def test_gross_and_lease_adjusted_debt():
    cur = _doc({
        "short_term_debt": 40,
        "long_term_debt": 360,
        "lease_liability_current": 15,
        "lease_liability_noncurrent": 85,
        "cash_and_equivalents": 250,
        "short_term_investments": 50,
        "equity_parent": 1100,
        "total_assets": 2000,
        "total_current_assets": 500,
        "total_current_liabilities": 300,
        "inventory": 120,
        "goodwill": 200,
        "intangibles": 100,
    })
    r = compute_stage2_metrics(cur)
    assert r.metrics["gross_debt"] == 400
    assert r.metrics["lease_liability_total"] == 100
    assert r.metrics["lease_adjusted_contractual_debt"] == 500
    assert r.metrics["net_debt"] == 400 - 300  # cash+sti=300
    assert r.metrics["current_ratio"] == 500 / 300
    assert r.metrics["debt_to_equity"] == 500 / 1100
    assert r.metrics["gw_intangibles_share_of_equity"] == 300 / 1100


def test_null_reason_when_missing():
    r = compute_stage2_metrics(_doc({}))
    assert r.metrics["gross_debt"] is None
    assert "gross_debt" in r.null_reasons
    assert r.metrics["cash_vs_near_term_obligations"] is None


def test_wc_trends_multi_period():
    cur = _doc({"receivables": 190, "inventory": 130, "revenue": 1100})
    prior = _doc({"receivables": 180, "inventory": 120, "revenue": 1000})
    r = compute_stage2_metrics(cur, prior)
    assert r.metrics["delta_receivables"] == 10
    assert r.metrics["delta_inventory"] == 10


def test_maturity_aggregation():
    cur = _doc({"debt_maturity_buckets": {"Y1": 10, "Y2": 20}})
    r = compute_stage2_metrics(cur)
    assert r.metrics["maturity_aggregation"]["Y1"] == 10.0
