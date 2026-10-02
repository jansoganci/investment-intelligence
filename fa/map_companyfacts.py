"""Best-effort XBRL→contract mapping; ambiguity → REVIEW not guess."""
from __future__ import annotations

from typing import Any

from .contract import (
    BS_CORE_FIELDS,
    BS_STAGE2_EXTENSIONS,
    BS_STAGE3_EXTENSIONS,
    CF_FIELDS,
    CF_STAGE3_BRIDGE_HELPERS,
    CF_STAGE3_EXTENSIONS,
    blank_period_document,
)
from .lineage import attach_field_with_lineage

# Preferred us-gaap tags per contract field (ordered). Multiple candidates → uncertain if >1 present.
TAG_MAP: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues",
        # IFRS FPI (20-F) — after US-GAAP so domestic issuers unchanged
        "RevenueFromContractsWithCustomers",
        "Revenue",
    ],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "interest_expense": ["InterestExpense"],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
    ],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss"],
    "net_income_attributable": [
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NetIncomeLoss",
    ],
    "net_income_consolidated": [
        "ProfitLoss",
        "NetIncomeLossIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "diluted_eps": ["EarningsPerShareDiluted"],
    # Share counts — NEVER mix concepts (diluted WAD ≠ basic WAD ≠ period-end outstanding)
    "shares_diluted_weighted": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
    ],
    "shares_basic_weighted": [
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ],
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",  # often under dei
    ],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "Cash",
        # Combined cash+restricted (e.g. DHR) — prefer pure cash tags first
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "short_term_investments": [
        "OtherShortTermInvestments",
        "ShortTermInvestments",
        "MarketableSecuritiesCurrent",
        "MarketableSecurities",
        # AFS debt securities current (e.g. INTU) when classic STI tags absent
        "DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent",
        "DebtSecuritiesAvailableForSaleCurrent",
        "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
    ],
    "total_current_assets": ["AssetsCurrent"],
    "total_assets": ["Assets"],
    "short_term_debt": [
        "ShortTermBorrowings",
        "CommercialPaper",
        "OtherShortTermBorrowings",
        "DebtCurrent",
    ],
    "long_term_debt": [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligations",
    ],
    # Interest-bearing secured / securitization borrowings (Wave2 A1) — separate from ST/LT
    "secured_debt": [
        "SecuredDebt",
        "TransfersAccountedForAsSecuredBorrowingsAssociatedLiabilitiesCarryingAmount",
    ],
    "total_debt": [
        "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
        "LongTermDebtAndCapitalLeaseObligations",
    ],  # often incomplete — mark uncertain
    "total_current_liabilities": ["LiabilitiesCurrent"],
    "total_liabilities": ["Liabilities"],
    "equity_parent": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "lease_liability_current": [
        "OperatingLeaseLiabilityCurrent",
        "FinanceLeaseLiabilityCurrent",
    ],
    "lease_liability_noncurrent": [
        "OperatingLeaseLiabilityNoncurrent",
        "FinanceLeaseLiabilityNoncurrent",
    ],
    "current_portion_ltd": [
        "LongTermDebtCurrent",
        "LongTermDebtAndCapitalLeaseObligationsCurrent",
    ],
    "goodwill": ["Goodwill"],
    "intangibles": [
        "IntangibleAssetsNetExcludingGoodwill",
        "FiniteLivedIntangibleAssetsNet",
        "IndefiniteLivedTrademarks",
    ],
    "inventory": [
        "InventoryNet",
        "InventoryFinishedGoods",
        "InventoryFinishedGoodsNetOfReserves",
    ],
    "receivables": [
        "AccountsReceivableNetCurrent",
        "AccountsReceivableNet",
        "ReceivablesNetCurrent",
    ],
    # Client / customer funds asset (Wave2 A4) — payable left unmapped if no structured tag
    "funds_held_for_clients": [
        "FundsHeldForClients",
    ],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "dividends_paid": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "share_repurchases": ["PaymentsForRepurchaseOfCommonStock"],
    "net_change_in_cash": [
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
        "CashAndCashEquivalentsPeriodIncreaseDecrease",
    ],
    "restricted_cash_amount": [
        "RestrictedCashAndCashEquivalents",
        "RestrictedCash",
        "RestrictedCashAndCashEquivalentsAtCarryingValue",
    ],
    "undrawn_revolver_or_liquidity_facilities": [
        "LineOfCreditFacilityRemainingBorrowingCapacity",
    ],
    "accounts_payable": [
        "AccountsPayableTradeCurrent",
        "AccountsPayableCurrent",
        # AccountsPayableAndAccruedLiabilitiesCurrent is mixed AP+accrued — not preferred;
        # if only that tag exists, leave null + MAPPING_AMBIGUOUS (see NULL_FIELD_REASONS).
    ],
    "deferred_revenue_current": [
        "ContractWithCustomerLiabilityCurrent",
        "DeferredRevenueCurrent",
    ],
    "deferred_revenue_noncurrent": [
        "ContractWithCustomerLiabilityNoncurrent",
        "DeferredRevenueNoncurrent",
    ],
    "business_acquisitions_cash": [
        "PaymentsToAcquireBusinessesNetOfCashAcquired",
        "PaymentsToAcquireBusinessesGross",
    ],
    "proceeds_from_asset_sales": [
        "ProceedsFromSaleOfPropertyPlantAndEquipment",
        "ProceedsFromSaleOfProductiveAssets",
    ],
    # Existing contract fields needed by Stage 3 dashboard (were unmapped)
    "depreciation_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
    ],
    "sbc_expense": [
        "AllocatedShareBasedCompensationExpense",
        "ShareBasedCompensation",
    ],
    # OCF–NI bridge helpers (generic; nullable)
    "equity_method_income": [
        "IncomeLossFromEquityMethodInvestments",
    ],
    "equity_method_income_net_of_dividends": [
        "IncomeLossFromEquityMethodInvestmentsNetOfDividendsOrDistributions",
    ],
    "deferred_tax_expense_benefit": [
        "DeferredIncomeTaxExpenseBenefit",
        "DeferredIncomeTaxesAndTaxCredits",
    ],
    "change_in_receivables_cf": [
        "IncreaseDecreaseInAccountsReceivable",
    ],
    "change_in_inventory_cf": [
        "IncreaseDecreaseInInventories",
    ],
    "change_in_payables_cf": [
        "IncreaseDecreaseInAccountsPayable",
        "IncreaseDecreaseInAccountsPayableTrade",
        # IncreaseDecreaseInAccountsPayableAndAccruedLiabilities is mixed — prefer clean;
        # if only mixed present, leave null + MAPPING_AMBIGUOUS below.
    ],
    "foreign_currency_transaction_gain_loss": [
        "ForeignCurrencyTransactionGainLossBeforeTax",
        "ForeignCurrencyTransactionGainLossUnrealized",
    ],
    "significant_gains_losses_net": [
        # Prefer broad "other assets"/business sale gains used on CFS reconciling lines
        "GainLossOnSaleOfOtherAssets",
        "GainLossOnSaleOfBusiness",
        "GainLossOnDispositionOfAssets",
    ],
    "other_operating_charges_cf": [
        "OtherOperatingActivitiesCashFlowStatement",
    ],
    "other_noncash_income_expense": [
        "OtherNoncashIncomeExpense",
    ],
    "increase_decrease_in_operating_capital": [
        "IncreaseDecreaseInOperatingCapital",
        "IncreaseDecreaseInOperatingAssets",
    ],
    # CFS-signed aggregate filled post-map from increase_decrease_in_operating_capital
    "net_change_in_operating_assets_liabilities": [],
}

# Structured null reason codes (persist on Normalized docs).
NULL_REASON_CODES = (
    "NOT_DISCLOSED",
    "NOT_APPLICABLE",
    "MAPPING_AMBIGUOUS",
    "SOURCE_CONFLICT",
)


def make_null_reason(code: str, detail: str) -> dict[str, str]:
    if code not in NULL_REASON_CODES:
        raise ValueError(f"unknown null reason code: {code}")
    return {"code": code, "detail": detail}


def null_reason_text(reason: dict[str, str] | str | None) -> str:
    if reason is None:
        return ""
    if isinstance(reason, dict):
        return f"{reason.get('code', '')}: {reason.get('detail', '')}".strip(": ")
    return str(reason)


# Explicit null reasons when no usable XBRL tag (do not coerce to 0).
NULL_FIELD_REASONS: dict[str, dict[str, str]] = {
    "total_liabilities": make_null_reason(
        "NOT_DISCLOSED",
        "No us-gaap:Liabilities instant in companyfacts for this period; "
        "do not derive Assets−Equity without human accept",
    ),
    "debt_maturity_buckets": make_null_reason(
        "NOT_DISCLOSED",
        "Not assembled from clean single tag; see notes / 10-K debt footnote if empty",
    ),
    "undrawn_revolver_or_liquidity_facilities": make_null_reason(
        "NOT_DISCLOSED",
        "No LineOfCreditFacilityRemainingBorrowingCapacity (or equivalent) for period",
    ),
    "restricted_cash_amount": make_null_reason(
        "NOT_DISCLOSED", "No RestrictedCash* tag for period"
    ),
    "short_term_investments": make_null_reason(
        "NOT_DISCLOSED",
        "No ShortTermInvestments / OtherShortTermInvestments / MarketableSecurities* / "
        "DebtSecuritiesAvailableForSale*Current for period",
    ),
    "secured_debt": make_null_reason(
        "NOT_DISCLOSED",
        "No SecuredDebt / TransfersAccountedForAsSecuredBorrowings* for period",
    ),
    "funds_held_for_clients": make_null_reason(
        "NOT_DISCLOSED",
        "No FundsHeldForClients (or equivalent client-funds asset) for period",
    ),
    "intangibles": make_null_reason(
        "NOT_DISCLOSED",
        "No IntangibleAssetsNetExcludingGoodwill / FiniteLived / IndefiniteLivedTrademarks for period",
    ),
    "long_term_debt": make_null_reason(
        "NOT_DISCLOSED",
        "No LongTermDebt* / LongTermDebtAndCapitalLeaseObligations for period",
    ),
    "accounts_payable": make_null_reason(
        "MAPPING_AMBIGUOUS",
        "No clean AccountsPayableTradeCurrent / AccountsPayableCurrent for period; "
        "do not coerce AccountsPayableAndAccruedLiabilitiesCurrent without human accept "
        "(mixed AP+accrued is ambiguous)",
    ),
    "deferred_revenue_current": make_null_reason(
        "NOT_DISCLOSED",
        "No ContractWithCustomerLiabilityCurrent / DeferredRevenueCurrent for period",
    ),
    "deferred_revenue_noncurrent": make_null_reason(
        "NOT_DISCLOSED",
        "No ContractWithCustomerLiabilityNoncurrent / DeferredRevenueNoncurrent for period",
    ),
    "business_acquisitions_cash": make_null_reason(
        "NOT_DISCLOSED", "No PaymentsToAcquireBusinesses* for period"
    ),
    "proceeds_from_asset_sales": make_null_reason(
        "NOT_DISCLOSED",
        "No ProceedsFromSaleOfPropertyPlantAndEquipment / ProceedsFromSaleOfProductiveAssets for period",
    ),
    "depreciation_amortization": make_null_reason(
        "NOT_DISCLOSED",
        "No DepreciationDepletionAndAmortization / DepreciationAndAmortization / Depreciation for period",
    ),
    "sbc_expense": make_null_reason(
        "NOT_DISCLOSED",
        "No AllocatedShareBasedCompensationExpense / ShareBasedCompensation for period",
    ),
    "shares_diluted_weighted": make_null_reason(
        "NOT_DISCLOSED",
        "No WeightedAverageNumberOfDilutedSharesOutstanding for period",
    ),
    "shares_basic_weighted": make_null_reason(
        "NOT_DISCLOSED",
        "No WeightedAverageNumberOfSharesOutstandingBasic for period",
    ),
    "shares_outstanding": make_null_reason(
        "NOT_DISCLOSED",
        "No CommonStockSharesOutstanding / EntityCommonStockSharesOutstanding for period",
    ),
    "equity_method_income": make_null_reason(
        "NOT_DISCLOSED", "No IncomeLossFromEquityMethodInvestments for period"
    ),
    "equity_method_income_net_of_dividends": make_null_reason(
        "NOT_DISCLOSED",
        "No IncomeLossFromEquityMethodInvestmentsNetOfDividendsOrDistributions for period",
    ),
    "deferred_tax_expense_benefit": make_null_reason(
        "NOT_DISCLOSED",
        "No DeferredIncomeTaxExpenseBenefit / DeferredIncomeTaxesAndTaxCredits for period",
    ),
    "change_in_receivables_cf": make_null_reason(
        "NOT_DISCLOSED", "No IncreaseDecreaseInAccountsReceivable CF line for period"
    ),
    "change_in_inventory_cf": make_null_reason(
        "NOT_DISCLOSED", "No IncreaseDecreaseInInventories CF line for period"
    ),
    "change_in_payables_cf": make_null_reason(
        "MAPPING_AMBIGUOUS",
        "No clean IncreaseDecreaseInAccountsPayable / Trade CF line; "
        "do not coerce IncreaseDecreaseInAccountsPayableAndAccruedLiabilities without human accept",
    ),
    "net_income_consolidated": make_null_reason(
        "NOT_DISCLOSED",
        "No ProfitLoss / NetIncomeLossIncludingPortionAttributableToNoncontrollingInterest for period",
    ),
    "foreign_currency_transaction_gain_loss": make_null_reason(
        "NOT_DISCLOSED",
        "No ForeignCurrencyTransactionGainLoss* for period",
    ),
    "significant_gains_losses_net": make_null_reason(
        "NOT_DISCLOSED",
        "No GainLossOnSaleOfOtherAssets / GainLossOnSaleOfBusiness / GainLossOnDispositionOfAssets for period",
    ),
    "other_operating_charges_cf": make_null_reason(
        "NOT_DISCLOSED",
        "No OtherOperatingActivitiesCashFlowStatement for period",
    ),
    "other_noncash_income_expense": make_null_reason(
        "NOT_DISCLOSED",
        "No OtherNoncashIncomeExpense for period",
    ),
    "increase_decrease_in_operating_capital": make_null_reason(
        "NOT_DISCLOSED",
        "No IncreaseDecreaseInOperatingCapital / IncreaseDecreaseInOperatingAssets for period",
    ),
    "net_change_in_operating_assets_liabilities": make_null_reason(
        "NOT_DISCLOSED",
        "No aggregate operating WC CF change (IncreaseDecreaseInOperatingCapital*) to derive CFS-signed net change",
    ),
}

DEBT_MATURITY_TAGS: list[tuple[str, str]] = [
    ("year_1", "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"),
    ("year_2", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"),
    ("year_3", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree"),
    ("year_4", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour"),
    ("year_5", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive"),
]


def _facts_us_gaap(companyfacts: dict) -> dict:
    return (companyfacts or {}).get("facts", {}).get("us-gaap", {})


def _facts_for_mapping(companyfacts: dict) -> dict:
    """Merge dei + us-gaap (us-gaap wins on collision) for tag lookup.

    EntityCommonStockSharesOutstanding often lives under dei; share WAD tags under us-gaap.
    """
    facts = (companyfacts or {}).get("facts", {}) or {}
    merged: dict = {}
    for ns in ("dei", "ifrs-full", "us-gaap"):
        node = facts.get(ns) or {}
        if isinstance(node, dict):
            merged.update(node)
    return merged


def _tag_namespace(companyfacts: dict, tag: str | None) -> str:
    if not tag:
        return "us-gaap"
    facts = (companyfacts or {}).get("facts", {}) or {}
    for ns in ("us-gaap", "dei", "ifrs-full"):
        if tag in (facts.get(ns) or {}):
            return ns
    return "us-gaap"


def _row_duration_days(row: dict) -> int | None:
    start, end = row.get("start"), row.get("end")
    if not start or not end:
        return None
    try:
        from datetime import date

        a = date.fromisoformat(str(start)[:10])
        b = date.fromisoformat(str(end)[:10])
        return (b - a).days
    except ValueError:
        return None


def _prefer_duration_for_period(period_type: str | None, fp: str | None) -> tuple[int, int] | None:
    """Return (lo, hi) inclusive day window for duration preference, or None."""
    if period_type == "FY" or fp == "FY":
        return (300, 400)
    if period_type == "Q" or (fp and str(fp).startswith("Q")):
        return (70, 110)
    return None


# Duration CF / additive flow fields — YTD vs discrete matters for derivation.
_DURATION_FLOW_FIELDS = frozenset(
    list(CF_FIELDS)
    + list(CF_STAGE3_EXTENSIONS)
    + [
        "depreciation_amortization",
        "revenue",
        "cost_of_revenue",
        "gross_profit",
        "operating_income",
        "interest_expense",
        "pretax_income",
        "income_tax",
        "net_income",
        "net_income_attributable",
        "net_income_consolidated",
        "sbc_expense",
    ]
)


def _flow_basis_from_duration(days: int | None, fiscal_period: str | None) -> str | None:
    """Classify row duration as DISCRETE / YTD. None if inconclusive.

    Do not treat fiscal label alone as discrete quarter (architecture §YTD trap).
    """
    if days is None:
        return None
    fp = (fiscal_period or "").upper()
    if 70 <= days <= 110:
        return "DISCRETE"
    if fp == "Q2" and 150 <= days <= 210:
        return "YTD"
    if fp == "Q3" and 230 <= days <= 300:
        return "YTD"
    if 110 < days < 300:
        return "YTD"
    if 300 <= days <= 400:
        return "DISCRETE" if fp in ("FY", "") else "YTD"
    return None


def _row_score(
    row: dict,
    *,
    period_end: str | None,
    accession: str | None,
    form_prefer: tuple[str, ...],
    fy: int | None,
    prefer_duration: tuple[int, int] | None = None,
) -> tuple:
    """Higher is better. Prefer exact period_end, duration window, accession, form, end-year==fy."""
    end = row.get("end") or ""
    form = row.get("form") or ""
    exact_end = 1 if period_end and end == period_end else 0
    # When period_end known, heavily penalize comparative prior columns in same fy filing
    end_year_match = 0
    if fy is not None and end:
        try:
            end_year_match = 1 if int(end[:4]) == fy else 0
        except ValueError:
            end_year_match = 0
    acc_match = 1 if accession and row.get("accn") == accession else 0
    form_ok = 1 if (not form_prefer or form in form_prefer) else 0
    dur_ok = 0
    if prefer_duration is not None:
        dur = _row_duration_days(row)
        if dur is not None and prefer_duration[0] <= dur <= prefer_duration[1]:
            dur_ok = 1
        elif dur is None and prefer_duration[0] >= 300:
            # Instant / missing start on annual — acceptable fallback for FY instants
            dur_ok = 0
    else:
        dur_ok = 0
    return (exact_end, end_year_match, dur_ok, acc_match, form_ok)


def _pick_fact_value(
    gaap: dict,
    tags: list[str],
    *,
    fy: int | None,
    fp: str | None,
    form_prefer: tuple[str, ...] = ("10-K", "10-Q", "20-F", "20-F/A"),
    period_end: str | None = None,
    accession: str | None = None,
    prefer_duration: tuple[int, int] | None = None,
    unit_prefer: tuple[str, ...] | None = None,
) -> tuple[Any, str | None, list[str], bool]:
    """
    Returns (value, chosen_tag, candidate_tags_present, ambiguous, chosen_row).
    Ambiguous if multiple distinct tags have values for the same period.
    Prefers rows matching period_end (fiscal year-end) over comparative columns.
    For quarterly, prefer ~90-day duration over YTD; for FY prefer ~365-day.
    """
    # Collect best row per tag
    best_by_tag: dict[str, tuple[tuple, Any, dict | None]] = {}
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        units = node.get("units", {})
        series = None
        unit_order = unit_prefer or ("USD", "USD/shares", "shares", "pure")
        for u in unit_order:
            if u in units and units[u]:
                series = units[u]
                break
        if series is None:
            series = next(iter(units.values()), None) if units else None
        if not series:
            continue
        for row in series:
            if fy is not None and row.get("fy") != fy:
                continue
            if fp is not None and row.get("fp") and row.get("fp") != fp:
                continue
            score = _row_score(
                row,
                period_end=period_end,
                accession=accession,
                form_prefer=form_prefer,
                fy=fy,
                prefer_duration=prefer_duration,
            )
            # If we know period_end, skip rows that neither match end nor end-year==fy
            # when better matches may exist — still keep as fallback if nothing else.
            prev = best_by_tag.get(tag)
            if prev is None or score > prev[0]:
                best_by_tag[tag] = (score, row.get("val"), row)

    if not best_by_tag:
        return None, None, [], False, None

    # If period_end specified, drop tags whose best row fails end-year match when any tag has it
    if period_end or fy is not None:
        strong = {
            t: tup
            for t, tup in best_by_tag.items()
            if (period_end and tup[0][0] == 1) or tup[0][1] == 1
        }
        if strong:
            best_by_tag = strong

    # Prefer duration-ok rows when any tag has duration match
    if prefer_duration is not None:
        dur_strong = {t: tup for t, tup in best_by_tag.items() if tup[0][2] == 1}
        if dur_strong:
            best_by_tag = dur_strong

    chosen_tag = None
    chosen_val = None
    chosen_row = None
    for tag in tags:
        if tag in best_by_tag:
            chosen_tag = tag
            chosen_val = best_by_tag[tag][1]
            chosen_row = best_by_tag[tag][2]
            break

    ambiguous = len(best_by_tag) > 1
    return chosen_val, chosen_tag, list(best_by_tag.keys()), ambiguous, chosen_row


def _attach_debt_maturity_buckets(
    doc: dict[str, Any],
    gaap: dict,
    *,
    fiscal_year: int,
    fp: str,
    accession: str | None,
    period_end: str | None,
    review_notes: list[str],
) -> None:
    buckets: dict[str, Any] = {}
    refs: list[str] = []
    for key, tag in DEBT_MATURITY_TAGS:
        val, chosen, _cands, _amb, _row = _pick_fact_value(
            gaap,
            [tag],
            fy=fiscal_year,
            fp=fp,
            period_end=period_end,
            accession=accession,
        )
        if val is not None:
            buckets[key] = val
            refs.append(f"us-gaap:{chosen}={val}")
    if not buckets:
        attach_field_with_lineage(
            doc,
            "debt_maturity_buckets",
            None,
            source_kind="sec_companyfacts",
            source_ref=None,
            source_id=accession,
            notes=null_reason_text(NULL_FIELD_REASONS["debt_maturity_buckets"])
            + "; human: confirm from 10-K Note on debt maturities",
            uncertain=True,
            review_status="pending",
            reviewed_by="machine_extracted",
        )
        review_notes.append(
            "debt_maturity_buckets: null — no LongTermDebtMaturities* tags for period; check 10-K notes"
        )
        return

    note = (
        "Assembled from LongTermDebtMaturities* XBRL tags (principal repayments only; "
        "excludes commercial paper / other ST borrowings unless tagged). "
        f"Refs: {', '.join(refs)}"
    )
    # Beyond year 5 often in notes only — leave null key if absent
    attach_field_with_lineage(
        doc,
        "debt_maturity_buckets",
        buckets,
        source_kind="sec_companyfacts",
        source_ref=";".join(refs),
        source_id=accession,
        notes=note,
        uncertain=True,  # buckets incomplete vs full debt schedule in notes
        review_status="pending",
        reviewed_by="machine_extracted",
    )
    review_notes.append(
        "debt_maturity_buckets: machine-assembled from XBRL maturity tags; verify vs 10-K debt note "
        "(may omit CP and >5y detail)"
    )


def map_companyfacts_to_period(
    companyfacts: dict,
    *,
    ticker: str,
    period_key: str,
    fiscal_year: int,
    fiscal_period: str = "FY",
    period_type: str = "FY",
    accession: str | None = None,
    version_id: str = "v001",
    period_end: str | None = None,
    filed_at: str | None = None,
) -> dict[str, Any]:
    """
    Best-effort map. Ambiguous multi-tag fields → value may be set from preferred tag
    but marked uncertain + REVIEW note (do not silently pick without flag).
    """
    if period_end is None and period_type == "FY":
        period_end = f"{fiscal_year}-12-31"

    doc = blank_period_document(
        ticker=ticker,
        period_key=period_key,
        version_id=version_id,
        period_type=period_type,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        accession=accession,
        source_id=accession,
        entity_name=(companyfacts or {}).get("entityName"),
        cik=str((companyfacts or {}).get("cik", "")).zfill(10) if companyfacts else None,
        change_reason="initial",
        status="draft",
        review_status="pending",
        period_end=period_end,
        filed_at=filed_at,
        available_as_of=filed_at,
    )

    gaap = _facts_for_mapping(companyfacts)
    fp = "FY" if period_type == "FY" else fiscal_period
    review_notes: list[str] = []
    null_reasons: dict[str, dict[str, str]] = {}
    prefer_dur = _prefer_duration_for_period(period_type, fp)
    share_fields = {
        "shares_diluted_weighted",
        "shares_basic_weighted",
        "shares_outstanding",
    }
    share_concept_notes = {
        "shares_diluted_weighted": (
            "concept=diluted_weighted_average; unit=shares; "
            "Stage 4 BD4 prefers this when available — do not mix with basic WAD "
            "or period-end outstanding"
        ),
        "shares_basic_weighted": (
            "concept=basic_weighted_average; unit=shares; "
            "distinct from diluted WAD and period-end outstanding"
        ),
        "shares_outstanding": (
            "concept=period_end_shares_outstanding; unit=shares; "
            "instant / DEI filing-date outstanding may not equal fiscal period-end; "
            "distinct from weighted-average diluted/basic"
        ),
    }

    for field, tags in TAG_MAP.items():
        unit_prefer = None
        if field in share_fields:
            unit_prefer = ("shares", "pure", "USD", "USD/shares")
        val, tag, candidates, ambiguous, chosen_row = _pick_fact_value(
            gaap,
            tags,
            fy=fiscal_year,
            fp=fp if period_type == "FY" else fiscal_period,
            period_end=period_end,
            accession=accession,
            prefer_duration=prefer_dur,
            unit_prefer=unit_prefer,
        )
        if val is None and not candidates:
            continue
        notes = None
        uncertain = False
        if field in share_concept_notes:
            notes = share_concept_notes[field]
        if ambiguous:
            uncertain = True
            # Distinct preferred-tag family with multiple hits → SOURCE_CONFLICT signal
            null_reasons[field] = make_null_reason(
                "SOURCE_CONFLICT",
                f"Multiple tags present {candidates}; preferred {tag} — do not treat as final",
            )
            notes = ((notes + "; ") if notes else "") + null_reason_text(null_reasons[field])
            review_notes.append(f"{field}: SOURCE_CONFLICT tags {candidates}")
            doc.setdefault("field_uncertainty", {})[field] = notes
        if field == "total_debt":
            uncertain = True
            notes = (notes or "") + (
                " total_debt from XBRL often incomplete (may exclude CP / leases nuance); "
                "prefer components"
            )
        if field == "intangibles" and tag == "IndefiniteLivedTrademarks":
            uncertain = True
            notes = (notes or "") + (
                " mapped from IndefiniteLivedTrademarks only — may omit other intangibles"
            )
            review_notes.append("intangibles: IndefiniteLivedTrademarks only (incomplete?)")
        if field == "short_term_debt" and ambiguous:
            notes = (notes or "") + (
                "; CommercialPaper and OtherShortTermBorrowings may appear separately "
                "— do not sum without human accept"
            )
        if field == "short_term_investments" and ambiguous:
            notes = (notes or "") + (
                "; OtherShortTermInvestments vs MarketableSecurities may overlap — verify BS line"
            )
        if field == "cash_and_equivalents" and tag == (
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
        ):
            uncertain = True
            notes = (notes or "") + (
                " mapped from combined cash+restricted tag — may include restricted cash; "
                "prefer CashAndCashEquivalentsAtCarryingValue when available"
            )
            review_notes.append(
                "cash_and_equivalents: combined cash+restricted tag (restricted may be included)"
            )
        if field == "secured_debt" and ambiguous:
            notes = (notes or "") + (
                "; SecuredDebt vs TransfersAccountedForAsSecuredBorrowings may overlap — "
                "prefer SecuredDebt; do not sum duplicates"
            )
        if field == "inventory" and tag == "InventoryFinishedGoodsNetOfReserves":
            notes = (notes or "") + (
                " mapped from InventoryFinishedGoodsNetOfReserves"
            )
        if field == "receivables" and tag == "ReceivablesNetCurrent":
            notes = (notes or "") + (
                " mapped from ReceivablesNetCurrent (broader than trade AR alone)"
            )
        if field == "short_term_investments" and tag and "AvailableForSale" in tag:
            notes = (notes or "") + (
                " mapped from AFS debt securities current — verify STI classification on BS"
            )
        if field == "shares_outstanding" and tag == "EntityCommonStockSharesOutstanding":
            uncertain = True

        # Duration / YTD annotation for flow fields (A2): fiscal label ≠ discrete.
        row_dur = _row_duration_days(chosen_row) if chosen_row else None
        flow_basis = None
        if field in _DURATION_FLOW_FIELDS and period_type != "FY":
            flow_basis = _flow_basis_from_duration(
                row_dur, fiscal_period if period_type != "FY" else "FY"
            )
            if flow_basis == "YTD":
                # Provenance only — do NOT put in field_uncertainty (that would
                # block YTD-aware Q4 derivation). Derivation consumes flow_basis.
                ytd_note = (
                    f"duration_days={row_dur}; flow_basis=YTD — "
                    "YTD cumulative interim, not discrete quarter "
                    "(do not treat fiscal label as discrete)"
                )
                notes = ((notes + "; ") if notes else "") + ytd_note
                review_notes.append(f"{field}: YTD duration {row_dur}d (not discrete Q)")
            elif flow_basis == "DISCRETE" and row_dur is not None:
                notes = ((notes + "; ") if notes else "") + (
                    f"duration_days={row_dur}; flow_basis=DISCRETE"
                )
            elif row_dur is None and field in _DURATION_FLOW_FIELDS:
                notes = ((notes + "; ") if notes else "") + (
                    "duration_days=unknown; flow_basis=UNKNOWN — "
                    "start/end missing; fiscal label not treated as discrete"
                )
            doc.setdefault("field_flow_basis", {})[field] = flow_basis or "UNKNOWN"
            if row_dur is not None:
                doc.setdefault("field_duration_days", {})[field] = row_dur

        # Persist period_start/end from fact row when document lacks them
        if chosen_row:
            if not doc.get("period_start") and chosen_row.get("start"):
                doc["period_start"] = str(chosen_row.get("start"))[:10]
            if not doc.get("period_end") and chosen_row.get("end"):
                doc["period_end"] = str(chosen_row.get("end"))[:10]
            # SD-W4-C2: persist duration_days for consumers (no 53→52 normalize)
            if doc.get("period_start") and doc.get("period_end") and doc.get("duration_days") is None:
                try:
                    from datetime import date as _date
                    _dur = (
                        _date.fromisoformat(str(doc["period_end"])[:10])
                        - _date.fromisoformat(str(doc["period_start"])[:10])
                    ).days + 1
                    doc["duration_days"] = _dur
                    doc["fifty_three_week"] = 368 <= _dur <= 375
                except ValueError:
                    pass

        ns = _tag_namespace(companyfacts, tag)
        attach_field_with_lineage(
            doc,
            field,
            val,
            source_kind="sec_companyfacts",
            source_ref=f"{ns}:{tag}" if tag else None,
            source_id=accession,
            notes=notes,
            uncertain=uncertain,
            review_status="pending",
            reviewed_by="machine_extracted",
        )

    # Mixed AP+accrued tag: do not invent clean accounts_payable — leave null + MAPPING_AMBIGUOUS
    if doc["fields"].get("accounts_payable") is None:
        mixed_val, mixed_tag, _mixed_cands, _, _mixed_row = _pick_fact_value(
            gaap,
            ["AccountsPayableAndAccruedLiabilitiesCurrent"],
            fy=fiscal_year,
            fp=fp if period_type == "FY" else fiscal_period,
            period_end=period_end,
            accession=accession,
        )
        if mixed_val is not None:
            reason = make_null_reason(
                "MAPPING_AMBIGUOUS",
                "AccountsPayableAndAccruedLiabilitiesCurrent present "
                f"(us-gaap:{mixed_tag}={mixed_val}) but mixes AP+accrued — "
                "accounts_payable left null; do not invent split without human accept",
            )
            null_reasons["accounts_payable"] = reason
            note = null_reason_text(reason)
            attach_field_with_lineage(
                doc,
                "accounts_payable",
                None,
                source_kind="sec_companyfacts",
                source_ref=f"us-gaap:{mixed_tag}" if mixed_tag else None,
                source_id=accession,
                notes=note,
                uncertain=True,
                review_status="pending",
                reviewed_by="machine_extracted",
                null_reason=reason,
            )
            doc.setdefault("field_uncertainty", {})["accounts_payable"] = note
            review_notes.append("accounts_payable: NULL — MAPPING_AMBIGUOUS mixed AP+accrued")

    # Mixed payables CF change: do not coerce to change_in_payables_cf
    if doc["fields"].get("change_in_payables_cf") is None:
        mixed_val, mixed_tag, _, _, _mixed_row2 = _pick_fact_value(
            gaap,
            ["IncreaseDecreaseInAccountsPayableAndAccruedLiabilities"],
            fy=fiscal_year,
            fp=fp if period_type == "FY" else fiscal_period,
            period_end=period_end,
            accession=accession,
        )
        if mixed_val is not None:
            reason = make_null_reason(
                "MAPPING_AMBIGUOUS",
                "IncreaseDecreaseInAccountsPayableAndAccruedLiabilities present "
                f"(us-gaap:{mixed_tag}={mixed_val}) but mixes AP+accrued CF — "
                "change_in_payables_cf left null; do not invent split without human accept",
            )
            null_reasons["change_in_payables_cf"] = reason
            note = null_reason_text(reason)
            attach_field_with_lineage(
                doc,
                "change_in_payables_cf",
                None,
                source_kind="sec_companyfacts",
                source_ref=f"us-gaap:{mixed_tag}" if mixed_tag else None,
                source_id=accession,
                notes=note,
                uncertain=True,
                review_status="pending",
                reviewed_by="machine_extracted",
                null_reason=reason,
            )
            doc.setdefault("field_uncertainty", {})["change_in_payables_cf"] = note
            review_notes.append(
                "change_in_payables_cf: NULL — MAPPING_AMBIGUOUS mixed AP+accrued CF"
            )

    # CFS-signed aggregate WC change: IncreaseDecreaseInOperatingCapital is BS-increase signed;
    # CFS net change in operating assets/liabilities uses the opposite sign.
    inc_op = doc["fields"].get("increase_decrease_in_operating_capital")
    if inc_op is not None and doc["fields"].get("net_change_in_operating_assets_liabilities") is None:
        try:
            cfs_wc = -float(inc_op)
        except (TypeError, ValueError):
            cfs_wc = None
        if cfs_wc is not None:
            note = (
                "CFS presentation = -IncreaseDecreaseInOperatingCapital "
                f"(raw XBRL={inc_op}); BS increase reduces operating cash"
            )
            attach_field_with_lineage(
                doc,
                "net_change_in_operating_assets_liabilities",
                cfs_wc,
                source_kind="sec_companyfacts",
                source_ref="derived:-us-gaap:IncreaseDecreaseInOperatingCapital",
                source_id=accession,
                notes=note,
                uncertain=False,
                review_status="pending",
                reviewed_by="machine_extracted",
            )
            review_notes.append(
                "net_change_in_operating_assets_liabilities: derived CFS-signed from "
                "IncreaseDecreaseInOperatingCapital"
            )

    # Harvest additional CF reconciliation tags not mapped into canonical buckets → company_specific
    _CFS_CONSUMED_TAGS = {
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
        "ShareBasedCompensation",
        "AllocatedShareBasedCompensationExpense",
        "DeferredIncomeTaxExpenseBenefit",
        "DeferredIncomeTaxesAndTaxCredits",
        "IncomeLossFromEquityMethodInvestments",
        "IncomeLossFromEquityMethodInvestmentsNetOfDividendsOrDistributions",
        "ForeignCurrencyTransactionGainLossBeforeTax",
        "ForeignCurrencyTransactionGainLossUnrealized",
        "GainLossOnSaleOfOtherAssets",
        "GainLossOnSaleOfBusiness",
        "GainLossOnDispositionOfAssets",
        "OtherOperatingActivitiesCashFlowStatement",
        "OtherNoncashIncomeExpense",
        "IncreaseDecreaseInOperatingCapital",
        "IncreaseDecreaseInOperatingAssets",
        "IncreaseDecreaseInAccountsReceivable",
        "IncreaseDecreaseInInventories",
        "IncreaseDecreaseInAccountsPayable",
        "IncreaseDecreaseInAccountsPayableTrade",
        "IncreaseDecreaseInAccountsPayableAndAccruedLiabilities",
        "NetCashProvidedByUsedInOperatingActivities",
        "ProfitLoss",
        "NetIncomeLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NetIncomeLossIncludingPortionAttributableToNoncontrollingInterest",
    }
    _EXTRA_CFS_TAG_HINTS = (
        "AdjustmentsToReconcile",
        "OtherNoncash",
        "IncreaseDecreaseInOperating",
        "IncreaseDecreaseInOther",
        "PensionAndOtherPostretirementBenefitsExpenseReconcilingItem",
        "ProvisionForLoanLeaseAndOtherLosses",
        "AssetImpairmentCharges",
        "RestructuringCosts",
        "DeferredIncomeTax",
    )
    company_specific: list[dict] = []
    for tag, body in gaap.items():
        if tag in _CFS_CONSUMED_TAGS:
            continue
        if not any(h in tag for h in _EXTRA_CFS_TAG_HINTS):
            continue
        val, chosen, _c, _a, _row = _pick_fact_value(
            gaap,
            [tag],
            fy=fiscal_year,
            fp=fp if period_type == "FY" else fiscal_period,
            period_end=period_end,
            accession=accession,
        )
        if val is None:
            continue
        # Preserve unmapped line; do NOT auto-include in sum (sign unsafe across issuers)
        company_specific.append(
            {
                "label": tag,
                "amount": None,
                "tag_or_source": f"us-gaap:{tag}={val}",
                "include_in_sum": False,
                "notes": (
                    "Unmapped CF-related companyfacts tag preserved for human/CFS review; "
                    "amount not auto-included (sign convention unsafe without statement role)"
                ),
                "raw_xbrl_value": val,
            }
        )
    if company_specific:
        doc["company_specific_cfs_adjustments"] = company_specific
        review_notes.append(
            f"company_specific_cfs_adjustments: {len(company_specific)} unmapped CF-related tags preserved"
        )

    _attach_debt_maturity_buckets(
        doc,
        gaap,
        fiscal_year=fiscal_year,
        fp=fp,
        accession=accession,
        period_end=period_end,
        review_notes=review_notes,
    )

    # restricted cash flag if amount present
    amt = doc["fields"].get("restricted_cash_amount")
    if amt is not None:
        doc["fields"]["restricted_cash_flag"] = True
        attach_field_with_lineage(
            doc,
            "restricted_cash_flag",
            True,
            source_kind="sec_companyfacts",
            source_ref="derived:restricted_cash_amount_present",
            source_id=accession,
            notes="True because restricted_cash_amount was machine-extracted",
            uncertain=False,
            review_status="pending",
            reviewed_by="machine_extracted",
        )

    # Wave2 A4: entity-level client-funds pattern if FundsHeldForClients ever tagged
    # (successor periods may only show restricted cash for customer funds).
    if "FundsHeldForClients" in gaap or doc["fields"].get("funds_held_for_clients") is not None:
        doc["fields"]["client_funds_business"] = True
        attach_field_with_lineage(
            doc,
            "client_funds_business",
            True,
            source_kind="sec_companyfacts",
            source_ref="derived:FundsHeldForClients_pattern",
            source_id=accession,
            notes=(
                "True because FundsHeldForClients present in companyfacts and/or period — "
                "treat restricted cash as customer-related matched-book for IC exclusion"
            ),
            uncertain=False,
            review_status="pending",
            reviewed_by="machine_extracted",
        )

    # Explicit null lineage for critical BS / Stage2 / Stage3 / bridge helpers still null
    already_lined = {x.get("field") for x in doc.get("lineage", [])}
    critical_nulls = [
        f
        for f in (
            BS_CORE_FIELDS
            + BS_STAGE2_EXTENSIONS
            + BS_STAGE3_EXTENSIONS
            + CF_STAGE3_EXTENSIONS
            + CF_STAGE3_BRIDGE_HELPERS
            + ["depreciation_amortization", "sbc_expense"]
        )
        if f not in ("restricted_cash_flag", "client_funds_business")
        and doc["fields"].get(f) is None
        and f not in already_lined
    ]
    for field in critical_nulls:
        reason = NULL_FIELD_REASONS.get(
            field,
            make_null_reason(
                "NOT_DISCLOSED",
                f"No reliable us-gaap mapping for {field} in companyfacts for this period; "
                "left null (not zero)",
            ),
        )
        null_reasons[field] = reason
        note = null_reason_text(reason)
        attach_field_with_lineage(
            doc,
            field,
            None,
            source_kind="sec_companyfacts",
            source_ref=None,
            source_id=accession,
            notes=note,
            uncertain=True,
            review_status="pending",
            reviewed_by="machine_extracted",
            null_reason=reason,
        )
        doc.setdefault("field_uncertainty", {})[field] = note
        review_notes.append(f"{field}: NULL — {note}")

    if null_reasons:
        doc.setdefault("null_reasons", {}).update(null_reasons)

    if review_notes:
        doc.setdefault("notes", []).append({"type": "mapping_review", "items": review_notes})
        doc["review_status"] = "pending"

    doc["accepted"] = False
    doc["status"] = "draft"
    return doc
