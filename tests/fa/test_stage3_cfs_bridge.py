"""Official CFS reconciliation bridge — generic; KO fixture numbers allowed in tests only."""
from __future__ import annotations

from fa.contract import CF_STAGE3_BRIDGE_HELPERS, empty_fields
from fa.map_companyfacts import TAG_MAP, map_companyfacts_to_period
from fa.stage3.calc import compute_stage3_metrics
from fa.stage3.cfs_bridge import assemble_cfs_reconciliation, select_cfs_starting_ni
from fa.stage3.evaluate import evaluate_stage3
from fa.models import Stage3SemanticReview


def _gaap_row(val, fy=2025, end="2025-12-31", accn="0001"):
    return {"fy": fy, "fp": "FY", "form": "10-K", "end": end, "val": val, "accn": accn}


def _facts(tags: dict[str, float]) -> dict:
    gaap = {}
    for tag, val in tags.items():
        gaap[tag] = {"units": {"USD": [_gaap_row(val)]}}
    return {"entityName": "Test Co", "cik": 1, "facts": {"us-gaap": gaap}}


def test_cfs_helpers_in_contract_and_tag_map():
    f = empty_fields()
    for k in (
        "net_income_consolidated",
        "foreign_currency_transaction_gain_loss",
        "significant_gains_losses_net",
        "other_operating_charges_cf",
        "other_noncash_income_expense",
        "increase_decrease_in_operating_capital",
        "net_change_in_operating_assets_liabilities",
    ):
        assert k in f
        if k != "net_change_in_operating_assets_liabilities":
            assert k in TAG_MAP or k in CF_STAGE3_BRIDGE_HELPERS


def test_select_cfs_starting_ni_prefers_consolidated():
    amt, basis, field = select_cfs_starting_ni(
        {"net_income_consolidated": 13137, "net_income": 13107, "net_income_attributable": 13107}
    )
    assert amt == 13137
    assert basis == "consolidated"
    assert field == "net_income_consolidated"


def test_cfs_reconciled_with_ko_fy2025_fixture_numbers():
    """KO FY2025 10-K CFS arithmetic (tests may use KO numbers; production code must not branch on KO)."""
    period = {
        "period_key": "FY2025",
        "version_id": "v001",
        "fields": {
            "operating_cash_flow": 7_408_000_000,
            "net_income_consolidated": 13_137_000_000,
            "net_income": 13_107_000_000,
            "net_income_attributable": 13_107_000_000,
            "depreciation_amortization": 1_050_000_000,
            "sbc_expense": 279_000_000,
            "deferred_tax_expense_benefit": 517_000_000,
            "equity_method_income_net_of_dividends": 1_038_000_000,
            "foreign_currency_transaction_gain_loss": -191_000_000,
            "significant_gains_losses_net": 713_000_000,
            "other_operating_charges_cf": 1_052_000_000,
            "other_noncash_income_expense": -141_000_000,
            "net_change_in_operating_assets_liabilities": -7_208_000_000,
        },
    }
    b = assemble_cfs_reconciliation(period)
    assert b["status"] == "RECONCILED"
    assert b["unexplained_residual"] == 0.0
    assert b["reconstructed_ocf"] == 7_408_000_000
    assert b["net_income_basis"] == "consolidated"
    assert b["buckets"]["equity_income_loss_net_of_dividends"] == -1_038_000_000
    assert b["buckets"]["foreign_currency_adjustments_cf"] == 191_000_000
    assert b["buckets"]["significant_gains_losses_net_cf"] == -713_000_000
    assert b["buckets"]["other_items_cf"] == 141_000_000
    # No unexplained-residual exception when RECONCILED
    uncertain = (b.get("factual_vs_uncertain") or {}).get("uncertain") or []
    assert not any("residual" in u.lower() and "unexplained" in u.lower() for u in uncertain)


def test_cfs_partial_when_residual_nonzero():
    period = {
        "period_key": "FY2025",
        "fields": {
            "operating_cash_flow": 1000,
            "net_income_consolidated": 800,
            "depreciation_amortization": 50,
            # missing other lines → residual nonzero
        },
    }
    b = assemble_cfs_reconciliation(period)
    assert b["status"] == "PARTIALLY_RECONCILED"
    assert b["unexplained_residual"] != 0
    assert "automation/data_problem" in b["interpretation_categories"] or b["data_problems"]


def test_cfs_unresolved_when_cannot_build():
    b = assemble_cfs_reconciliation({"period_key": "FY2025", "fields": {}})
    assert b["status"] == "UNRESOLVED"
    assert "automation/data_problem" in b["interpretation_categories"]


def test_map_derives_cfs_wc_aggregate_and_consolidated_ni():
    facts = _facts(
        {
            "ProfitLoss": 13_137_000_000,
            "NetIncomeLoss": 13_107_000_000,
            "DepreciationDepletionAndAmortization": 1_050_000_000,
            "ShareBasedCompensation": 279_000_000,
            "DeferredIncomeTaxExpenseBenefit": 517_000_000,
            "IncomeLossFromEquityMethodInvestmentsNetOfDividendsOrDistributions": 1_038_000_000,
            "ForeignCurrencyTransactionGainLossBeforeTax": -191_000_000,
            "GainLossOnSaleOfOtherAssets": 713_000_000,
            "OtherOperatingActivitiesCashFlowStatement": 1_052_000_000,
            "OtherNoncashIncomeExpense": -141_000_000,
            "IncreaseDecreaseInOperatingCapital": 7_208_000_000,
            "NetCashProvidedByUsedInOperatingActivities": 7_408_000_000,
            "IncreaseDecreaseInAccountsReceivable": -334_000_000,
            "IncreaseDecreaseInInventories": 154_000_000,
        }
    )
    doc = map_companyfacts_to_period(
        facts,
        ticker="T",
        period_key="FY2025",
        fiscal_year=2025,
        accession="0001",
        period_end="2025-12-31",
    )
    assert doc["fields"]["net_income_consolidated"] == 13_137_000_000
    assert doc["fields"]["increase_decrease_in_operating_capital"] == 7_208_000_000
    assert doc["fields"]["net_change_in_operating_assets_liabilities"] == -7_208_000_000
    assert doc["fields"]["foreign_currency_transaction_gain_loss"] == -191_000_000
    assert doc["fields"]["significant_gains_losses_net"] == 713_000_000
    assert doc["fields"]["other_operating_charges_cf"] == 1_052_000_000
    assert doc["fields"]["other_noncash_income_expense"] == -141_000_000
    b = assemble_cfs_reconciliation(doc)
    assert b["status"] == "RECONCILED"
    assert b["unexplained_residual"] == 0.0


def test_company_specific_preserved_not_dropped():
    period = {
        "period_key": "FY2025",
        "fields": {
            "operating_cash_flow": 100,
            "net_income_consolidated": 80,
            "depreciation_amortization": 10,
        },
        "company_specific_cfs_adjustments": [
            {
                "label": "CustomLine",
                "amount": 10,
                "tag_or_source": "us-gaap:Custom",
                "include_in_sum": True,
            }
        ],
    }
    b = assemble_cfs_reconciliation(period)
    assert b["company_specific_cfs_adjustments"]
    assert b["status"] == "RECONCILED"
    assert b["reconstructed_ocf"] == 100


def test_evaluate_reconciled_does_not_carry_unexplained_residual():
    periods = [
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "version_id": "v001",
            "fields": {
                "operating_cash_flow": 7_408_000_000,
                "net_income_consolidated": 13_137_000_000,
                "net_income": 13_107_000_000,
                "capex": 2_112_000_000,
                "depreciation_amortization": 1_050_000_000,
                "sbc_expense": 279_000_000,
                "deferred_tax_expense_benefit": 517_000_000,
                "equity_method_income_net_of_dividends": 1_038_000_000,
                "foreign_currency_transaction_gain_loss": -191_000_000,
                "significant_gains_losses_net": 713_000_000,
                "other_operating_charges_cf": 1_052_000_000,
                "other_noncash_income_expense": -141_000_000,
                "net_change_in_operating_assets_liabilities": -7_208_000_000,
                "accounts_payable": 100,
                "receivables": 80,
                "inventory": 70,
                "revenue": 500,
            },
        },
        {
            "period_key": "FY2025",
            "period_type": "FY",
            "version_id": "v001",
            "fields": {
                "operating_cash_flow": 7_408_000_000,
                "net_income_consolidated": 13_137_000_000,
                "net_income": 13_107_000_000,
                "capex": 2_112_000_000,
                "depreciation_amortization": 1_050_000_000,
                "sbc_expense": 279_000_000,
                "deferred_tax_expense_benefit": 517_000_000,
                "equity_method_income_net_of_dividends": 1_038_000_000,
                "foreign_currency_transaction_gain_loss": -191_000_000,
                "significant_gains_losses_net": 713_000_000,
                "other_operating_charges_cf": 1_052_000_000,
                "other_noncash_income_expense": -141_000_000,
                "net_change_in_operating_assets_liabilities": -7_208_000_000,
                "accounts_payable": 110,
                "receivables": 90,
                "inventory": 75,
                "revenue": 550,
            },
        },
    ]
    report = evaluate_stage3(
        "SYNTH",
        periods,
        semantic=Stage3SemanticReview(filled=True, maintenance_capex_status="UNKNOWN"),
    )
    cfs = report.calc.metrics["latest_cfs_reconciliation"]
    assert cfs["status"] == "RECONCILED"
    carry_text = " ".join(report.carry_forward_concerns).lower()
    why_text = " ".join(report.why_bullets).lower()
    assert "unexplained residual" not in carry_text
    assert "reconciles" in why_text or "residual=0" in why_text or "residual=0.0" in why_text.replace(",", "")
    m1 = next(a for a in report.question_answers if a.question_id == "S3-M1")
    assert "RECONCILED" in m1.answer_summary


def test_calc_exposes_cfs_reconciliation():
    period = {
        "period_key": "FY2025",
        "period_type": "FY",
        "version_id": "v001",
        "fields": {
            "operating_cash_flow": 100,
            "net_income_consolidated": 80,
            "net_income": 80,
            "capex": 10,
            "depreciation_amortization": 20,
        },
    }
    r = compute_stage3_metrics([period])
    assert r.metrics["latest_cfs_reconciliation"]["status"] in {
        "RECONCILED",
        "PARTIALLY_RECONCILED",
        "UNRESOLVED",
    }


def test_no_ko_hardcoding_in_cfs_bridge_module():
    import inspect
    import fa.stage3.cfs_bridge as mod

    src = inspect.getsource(mod)
    assert 'ticker == "KO"' not in src
    assert "ticker == 'KO'" not in src
    assert "fairlife" not in src.lower()
