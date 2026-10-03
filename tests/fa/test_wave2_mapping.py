"""Wave 2 regression — A1 debt perimeter, A3 cash, A4 STI/client funds, A5 inv, A6 recv."""
from __future__ import annotations

from fa.map_companyfacts import TAG_MAP
from fa.stage2.calc import compute_stage2_metrics
from fa.stage2.evaluate import evaluate_stage2
from fa.stage2.semantic import placeholder_semantic_review
from fa.stage6.calc import (
    compute_ic_inclusive,
    compute_nibol,
    compute_stage6_metrics,
    _wc_metrics,
)


def _doc(fields):
    return {"period_key": "FY2025", "period_type": "FY", "version_id": "v001", "fields": fields}


# ---------------------------------------------------------------------------
# TAG_MAP coverage (cheap factual locks)
# ---------------------------------------------------------------------------


def test_w2_tag_map_covers_wave2_concepts():
    assert "SecuredDebt" in TAG_MAP["secured_debt"]
    assert "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents" in TAG_MAP[
        "cash_and_equivalents"
    ]
    assert "DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent" in TAG_MAP[
        "short_term_investments"
    ]
    assert "InventoryFinishedGoodsNetOfReserves" in TAG_MAP["inventory"]
    assert "ReceivablesNetCurrent" in TAG_MAP["receivables"]
    assert "FundsHeldForClients" in TAG_MAP["funds_held_for_clients"]


# ---------------------------------------------------------------------------
# A1 — gross_debt honesty + securitization
# ---------------------------------------------------------------------------


def test_w2_a1_secured_debt_included_in_gross():
    r = compute_stage2_metrics(
        _doc(
            {
                "short_term_debt": 13_796_000_000,
                "secured_debt": 6_596_000_000,
                "long_term_debt": None,
                "cash_and_equivalents": 8_000_000_000,
            }
        )
    )
    assert r.metrics["gross_debt"] == 13_796_000_000 + 6_596_000_000
    assert r.metrics["gross_debt_incomplete"] is True
    assert r.metrics["opco_fs_split_unavailable"] is True
    assert r.metrics["debt_view_label"] == "consolidated_interest_bearing_incomplete"
    assert "gross_debt_incomplete" in r.null_reasons


def test_w2_a1_st_only_without_evidence_not_incomplete():
    """Simple ST-only issuer (no secured/total_debt/maturity) → complete ST debt OK."""
    r = compute_stage2_metrics(
        _doc({"short_term_debt": 100, "long_term_debt": None, "cash_and_equivalents": 50})
    )
    assert r.metrics["gross_debt"] == 100
    assert r.metrics["gross_debt_incomplete"] is False
    assert r.metrics["opco_fs_split_unavailable"] is False


def test_w2_a1_complete_st_plus_ltd_unchanged():
    r = compute_stage2_metrics(
        _doc(
            {
                "short_term_debt": 40,
                "long_term_debt": 360,
                "lease_liability_current": 15,
                "lease_liability_noncurrent": 85,
                "cash_and_equivalents": 250,
            }
        )
    )
    assert r.metrics["gross_debt"] == 400
    assert r.metrics["gross_debt_incomplete"] is False


def test_w2_a1_evaluate_review_when_opco_fs_unavailable():
    periods = [
        _doc(
            {
                "short_term_debt": 13_796_000_000,
                "secured_debt": 6_596_000_000,
                "long_term_debt": None,
                "cash_and_equivalents": 8_276_000_000,
                "total_assets": 100_000_000_000,
                "equity_parent": 20_000_000_000,
                "total_current_assets": 40_000_000_000,
                "total_current_liabilities": 30_000_000_000,
            }
        )
    ]
    report = evaluate_stage2(
        ticker="DE",
        periods=periods,
        gate0_class="operating",
        semantic=placeholder_semantic_review(),
    )
    assert report.process_outcome == "REVIEW_REQUIRED"
    assert report.calc.metrics["gross_debt_incomplete"] is True


# ---------------------------------------------------------------------------
# A3 / A4-p1 — IC cash policy + STI exclusion
# ---------------------------------------------------------------------------


def test_w2_a3_missing_cash_blocks_ic_not_zero_exclusion():
    ic = compute_ic_inclusive(
        {
            "total_assets": 80_000_000_000,
            "cash_and_equivalents": None,
            "accounts_payable": 1_000_000_000,
            "deferred_revenue_current": 500_000_000,
        }
    )
    assert ic["ic_inclusive"] is None
    assert ic.get("cash_missing_blocks_ic") is True
    assert ic.get("cash_missing_treated_as_zero") is False


def test_w2_a4_sti_excluded_from_ic():
    ic = compute_ic_inclusive(
        {
            "total_assets": 40_000_000_000,
            "cash_and_equivalents": 2_884_000_000,
            "short_term_investments": 1_668_000_000,
            "accounts_payable": 700_000_000,
            "deferred_revenue_current": 1_000_000_000,
        }
    )
    # 40B - 2.884B - 1.668B - 0 - 1.7B = 33.748B
    assert abs(ic["ic_inclusive"] - 33_748_000_000) < 1.0
    assert ic["components"]["sti_excluded"] == 1_668_000_000


def test_w2_a4_client_restricted_excluded_and_honesty_flag():
    """INTU-class: restricted >> cash → exclude from IC; payable not invented."""
    fields = {
        "total_assets": 40_000_000_000,
        "cash_and_equivalents": 2_884_000_000,
        "short_term_investments": None,
        "restricted_cash_amount": 6_597_000_000,
        "accounts_payable": 700_000_000,
        "deferred_revenue_current": 1_245_000_000,
    }
    nibol = compute_nibol(fields)
    assert nibol["client_funds_incomplete"] is True
    assert nibol["nibol_incomplete"] is True  # honesty even though AP+deferred present

    ic = compute_ic_inclusive(fields)
    assert ic["cash_policy"] == "exclude_cash_sti_and_client_restricted_funds"
    assert ic["components"]["client_funds_excluded"] == 6_597_000_000
    # 40 - 2.884 - 0 - 6.597 - 1.945 = 28.574B
    expected = 40_000_000_000 - 2_884_000_000 - 6_597_000_000 - (700_000_000 + 1_245_000_000)
    assert abs(ic["ic_inclusive"] - expected) < 1.0


def test_w2_a4_restricted_inside_cash_not_double_excluded():
    """DE-class: restricted << cash, no client_funds_business → of-which inside cash."""
    fields = {
        "total_assets": 100_000_000_000,
        "cash_and_equivalents": 8_276_000_000,
        "restricted_cash_amount": 257_000_000,
        "accounts_payable": 1_000_000_000,
        "deferred_revenue_current": 500_000_000,
    }
    ic = compute_ic_inclusive(fields)
    assert ic["components"]["client_funds_excluded"] == 0.0
    assert ic["cash_policy"] == "exclude_cash_and_sti"
    assert compute_nibol(fields)["client_funds_incomplete"] is False


def test_w2_a4_client_funds_business_excludes_restricted_even_if_lt_cash():
    """INTU FY2026-class: restricted < cash but client_funds_business → exclude."""
    fields = {
        "total_assets": 40_000_000_000,
        "cash_and_equivalents": 4_705_000_000,
        "restricted_cash_amount": 4_511_000_000,
        "short_term_investments": 2_495_000_000,
        "client_funds_business": True,
        "accounts_payable": 873_000_000,
        "deferred_revenue_current": 1_072_000_000,
    }
    assert compute_nibol(fields)["client_funds_incomplete"] is True
    ic = compute_ic_inclusive(fields)
    assert ic["components"]["client_funds_excluded"] == 4_511_000_000
    expected = (
        40_000_000_000
        - 4_705_000_000
        - 2_495_000_000
        - 4_511_000_000
        - (873_000_000 + 1_072_000_000)
    )
    assert abs(ic["ic_inclusive"] - expected) < 1.0


def test_w2_a4_no_invented_payable_in_nibol():
    fields = {
        "accounts_payable": 100,
        "deferred_revenue_current": 50,
        "restricted_cash_amount": 1000,
        "cash_and_equivalents": 10,
    }
    nibol = compute_nibol(fields)
    assert nibol["nibol"] == 150  # AP + deferred only
    assert "client_funds_payable" not in (nibol.get("components") or {})
    assert nibol["client_funds_incomplete"] is True


# ---------------------------------------------------------------------------
# A5 / A6 — WC null ≠ 0
# ---------------------------------------------------------------------------


def test_w2_a5_null_inventory_refuses_coerced_wc():
    rows = [
        {
            "period_key": "FY2025",
            "inventory": None,
            "receivables": 670_137_000,
            "accounts_payable": 8_025_590_000,
        }
    ]
    wc = _wc_metrics(rows)
    assert wc["latest_wc_proxy"] is None
    assert wc["wc_incomplete"] is True
    assert "inventory" in wc["wc_missing_components"]


def test_w2_a6_null_receivables_refuses_coerced_wc():
    rows = [
        {
            "period_key": "FY2025",
            "inventory": 18_116_000_000,
            "receivables": None,
            "accounts_payable": 19_783_000_000,
        }
    ]
    wc = _wc_metrics(rows)
    assert wc["latest_wc_proxy"] is None
    assert wc["wc_incomplete"] is True
    assert "receivables" in wc["wc_missing_components"]


def test_w2_wc_complete_when_all_components_present():
    rows = [
        {
            "period_key": "FY2024",
            "inventory": 100,
            "receivables": 50,
            "accounts_payable": 80,
        },
        {
            "period_key": "FY2025",
            "inventory": 7_025_688_000,
            "receivables": 670_137_000,
            "accounts_payable": 8_025_590_000,
        },
    ]
    wc = _wc_metrics(rows)
    assert wc["wc_incomplete"] is False
    expected = 7_025_688_000 + 670_137_000 - 8_025_590_000
    assert abs(wc["latest_wc_proxy"] - expected) < 1.0


def test_w2_stage6_metrics_propagates_client_funds_flag():
    rows = []
    for i in range(3):
        rows.append(
            {
                "period_key": f"FY{2023+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "operating_income": 100 + i * 10,
                    "pretax_income": 90 + i * 10,
                    "income_tax": 20 + i,
                    "total_assets": 40_000 + i * 100,
                    "cash_and_equivalents": 2_000,
                    "restricted_cash_amount": 6_000,  # >> cash → client funds
                    "accounts_payable": 700,
                    "deferred_revenue_current": 300,
                    "goodwill": 200,
                    "intangibles": 100,
                    "inventory": 10,
                    "receivables": 30,
                    "capex": -30,
                    "depreciation_amortization": 25,
                },
            }
        )
    calc = compute_stage6_metrics(rows)
    dual = calc.metrics["dual_roic"]
    assert dual["client_funds_incomplete"] is True
    assert dual["nibol_incomplete"] is True
    assert dual["definition_labels"]["cash_policy"] == (
        "exclude_cash_sti_and_client_restricted_funds"
    )
    # IC excludes client funds 6000
    # TA 40200 - cash 2000 - client 6000 - nibol 1000 = 31200 (approx last row)
    assert dual["ic_inclusive"] == 40_200 - 2_000 - 6_000 - 1_000


# ---------------------------------------------------------------------------
# A1 — convertible-only issuers (NET class)
# ---------------------------------------------------------------------------


def _companyfacts(usd_tags: dict[str, int]) -> dict:
    def _row(val):
        return {"fy": 2025, "fp": "FY", "form": "10-K", "end": "2025-12-31", "val": val}

    return {
        "cik": 1477333,
        "entityName": "Convertible-only issuer",
        "facts": {"us-gaap": {t: {"units": {"USD": [_row(v)]}} for t, v in usd_tags.items()}},
    }


def test_w2_a1_convertible_only_issuer_maps_debt_and_ev():
    from fa.map_companyfacts import map_companyfacts_to_period
    from fa.stage8.calc import build_ev_equity_bridge, extract_cs_from_period

    doc = map_companyfacts_to_period(
        _companyfacts(
            {
                "ConvertibleDebtNoncurrent": 1_974_120_000,
                "ConvertibleDebtCurrent": 1_291_281_000,
                "CashAndCashEquivalentsAtCarryingValue": 1_000_000_000,
            }
        ),
        ticker="NETX",
        period_key="FY2025",
        fiscal_year=2025,
    )
    assert doc["fields"]["long_term_debt"] == 1_974_120_000
    assert doc["fields"]["short_term_debt"] == 1_291_281_000

    cs = extract_cs_from_period(doc)
    cs["shares_diluted_weighted"] = 348_421_000
    bridge = build_ev_equity_bridge(share_price=100.0, cs=cs)
    assert bridge["gross_debt"] == 3_265_401_000
    assert bridge["enterprise_value"] is not None


def test_w2_a1_convertible_not_used_when_regular_debt_tags_present():
    from fa.map_companyfacts import map_companyfacts_to_period

    doc = map_companyfacts_to_period(
        _companyfacts(
            {
                "LongTermDebtNoncurrent": 5_000_000_000,
                "ConvertibleDebtNoncurrent": 1_000_000_000,
                "ConvertibleDebtCurrent": 500_000_000,
            }
        ),
        ticker="MIXD",
        period_key="FY2025",
        fiscal_year=2025,
    )
    assert doc["fields"]["long_term_debt"] == 5_000_000_000
    assert doc["fields"].get("short_term_debt") is None
