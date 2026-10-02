"""Stage 7 deterministic cash-use / share / debt exhibits."""
from __future__ import annotations

from fa.stage7.calc import compute_stage7_metrics


def _fy(year, **fields):
    return {
        "period_key": f"FY{year}",
        "period_type": "FY",
        "version_id": "v1",
        "fields": fields,
    }


def test_cash_use_composition_and_revealed_rank():
    periods = [
        _fy(2021, business_acquisitions_cash=100, dividends_paid=10, share_repurchases=20, capex=-5),
        _fy(2022, business_acquisitions_cash=200, dividends_paid=10, share_repurchases=30, capex=-5),
        _fy(2023, business_acquisitions_cash=300, dividends_paid=12, share_repurchases=40, capex=-6),
        _fy(2024, business_acquisitions_cash=250, dividends_paid=12, share_repurchases=50, capex=-6),
        _fy(2025, business_acquisitions_cash=400, dividends_paid=15, share_repurchases=60, capex=-7),
    ]
    r = compute_stage7_metrics(periods)
    h = r.metrics["revealed_hierarchy"]
    assert h["no_fixed_universal_order"] is True
    assert h["dominant_use"] == "acquisitions"
    assert h["revealed_rank_desc"][0] == "acquisitions"
    assert r.metrics["no_roic_recompute"] is True
    assert r.metrics["no_roiic_recompute"] is True
    assert r.metrics["distributions_combined_buybacks_and_dividends"] is True


def test_gross_and_net_share():
    periods = [
        _fy(2021, share_repurchases=100, sbc_expense=40, shares_outstanding=1000),
        _fy(2022, share_repurchases=120, sbc_expense=45, shares_outstanding=980),
        _fy(2023, share_repurchases=140, sbc_expense=50, shares_outstanding=960),
    ]
    r = compute_stage7_metrics(periods)
    s = r.metrics["share_trend"]
    assert s["gross_repurchase_multi_year"] == 360
    assert s["sbc_expense_multi_year"] == 135
    assert s["net_share_change"] == -40
    assert s["net_share_basis"] == "shares_outstanding"
    assert s["no_payout_threshold"] is True
    assert s["no_buyback_yield_gate"] is True


def test_debt_motive_deal_finance_heuristic():
    periods = [
        _fy(2021, total_debt=1000, business_acquisitions_cash=200, share_repurchases=10, dividends_paid=5),
        _fy(2022, total_debt=1500, business_acquisitions_cash=400, share_repurchases=10, dividends_paid=5),
        _fy(2023, total_debt=2000, business_acquisitions_cash=500, share_repurchases=10, dividends_paid=5),
    ]
    r = compute_stage7_metrics(periods)
    assert "deal_finance" in r.metrics["debt_motive_tags"]
    assert r.metrics["debt_context"]["no_solvency_retest"] is True
    assert r.metrics["debt_context"]["stage2_owns_solvency"] is True


def test_empty_periods_unknown():
    r = compute_stage7_metrics([])
    assert r.metrics["n_fy"] == 0
    assert r.null_reasons.get("cash_use_spine") == "UNKNOWN"
    assert r.metrics["no_roic_recompute"] is True


def test_material_input_uncertainty_preserved():
    """Normalized field_uncertainty must not be silently dropped in Stage 7 calc."""
    periods = [
        {
            "period_key": "FY2021",
            "period_type": "FY",
            "version_id": "v1",
            "accession": "0000000001",
            "filed_at": "2022-02-01",
            "period_end": "2021-12-31",
            "source_id": "0000000001",
            "fields": {
                "capex": 10,
                "share_repurchases": 20,
                "sbc_expense": 5,
                "shares_diluted_weighted": 100,
            },
            "field_uncertainty": {
                "sbc_expense": "SOURCE_CONFLICT: Multiple tags present",
            },
            "lineage": [
                {
                    "field": "sbc_expense",
                    "value": 5,
                    "source_kind": "sec_companyfacts",
                    "source_ref": "us-gaap:AllocatedShareBasedCompensationExpense",
                    "source_id": "0000000001",
                    "uncertain": True,
                    "notes": "SOURCE_CONFLICT: Multiple tags present",
                },
                {
                    "field": "capex",
                    "value": 10,
                    "source_kind": "sec_companyfacts",
                    "source_ref": "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
                    "source_id": "0000000001",
                    "uncertain": False,
                    "notes": None,
                },
            ],
        },
        {
            "period_key": "FY2022",
            "period_type": "FY",
            "version_id": "v1",
            "accession": "0000000002",
            "filed_at": "2023-02-01",
            "period_end": "2022-12-31",
            "source_id": "0000000002",
            "fields": {
                "capex": 12,
                "share_repurchases": 22,
                "sbc_expense": 6,
                "shares_diluted_weighted": 95,
            },
            "field_uncertainty": {
                "sbc_expense": "SOURCE_CONFLICT: Multiple tags present",
            },
            "lineage": [
                {
                    "field": "sbc_expense",
                    "value": 6,
                    "source_kind": "sec_companyfacts",
                    "source_ref": "us-gaap:AllocatedShareBasedCompensationExpense",
                    "source_id": "0000000002",
                    "uncertain": True,
                    "notes": "SOURCE_CONFLICT: Multiple tags present",
                },
            ],
        },
    ]
    r = compute_stage7_metrics(periods)
    rows = r.metrics["cash_use_rows"]
    assert rows[0]["provenance"]["accession"] == "0000000001"
    assert rows[0]["provenance"]["filed_at"] == "2022-02-01"
    assert "sbc_expense" in (rows[0]["provenance"]["field_uncertainty"] or {})
    assert rows[0]["provenance"]["field_lineage"]["capex"]["source_ref"].endswith(
        "PaymentsToAcquirePropertyPlantAndEquipment"
    )
    miu = r.metrics["material_input_uncertainty"]
    assert miu["sbc_expense_uncertain"] is True
    assert "sbc_expense" in miu["fields_with_uncertainty"]
    assert r.metrics["share_trend"]["sbc_expense_uncertain"] is True
    assert r.metrics["input_provenance"]["source_type"] == "Normalized"
    assert r.metrics["input_provenance"]["periods"][0]["accession"] == "0000000001"
