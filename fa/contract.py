"""Operating company field schema + Stage 2/3/4/5 extensions (all nullable)."""
from __future__ import annotations

from typing import Any

# Core income statement keys
IS_FIELDS = [
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "interest_expense",
    "pretax_income",
    "income_tax",
    "net_income",
    "net_income_attributable",
    "net_income_consolidated",  # ProfitLoss / NI including NCI when disclosed
    "diluted_eps",
    "sbc_expense",
    "depreciation_amortization",
]

# Core balance sheet
BS_CORE_FIELDS = [
    "cash_and_equivalents",
    "short_term_investments",
    "total_current_assets",
    "total_assets",
    "short_term_debt",
    "long_term_debt",
    "total_debt",
    "total_current_liabilities",
    "total_liabilities",
    "equity_parent",
    "shares_outstanding",
    "shares_diluted_weighted",
    "shares_basic_weighted",  # WAD basic — never mix with diluted or period-end outstanding
]

# Stage 2 extensions (nullable) — architecture §7.3
BS_STAGE2_EXTENSIONS = [
    "lease_liability_current",
    "lease_liability_noncurrent",
    "current_portion_ltd",
    "debt_maturity_buckets",  # dict or list when present
    "goodwill",
    "intangibles",
    "inventory",
    "receivables",
    "undrawn_revolver_or_liquidity_facilities",
    "restricted_cash_flag",
    "restricted_cash_amount",
    # bool: when True, short_term_debt already embeds CPLTD (omit cpltd in Stage 2 sums)
    "short_term_debt_includes_current_ltd",
    # Wave2 A1/A4 — interest-bearing secured/securitization; client funds asset (no invented payable)
    "secured_debt",
    "funds_held_for_clients",
    # bool: entity uses / used FundsHeldForClients pattern (Wave2 A4)
    "client_funds_business",
]

# Stage 3 balance-sheet extensions (nullable) — SPEC_LOCKED §0.3 / §4.2
BS_STAGE3_EXTENSIONS = [
    "accounts_payable",
    "deferred_revenue_current",
    "deferred_revenue_noncurrent",  # optional pair; nullable
]

CF_FIELDS = [
    "operating_cash_flow",
    "capex",
    "purchases_of_investments",
    "sales_of_investments",
    "dividends_paid",
    "share_issuances",
    "share_repurchases",
    "net_change_in_cash",
]

# Stage 3 cash-flow extensions (nullable) — SPEC_LOCKED §0.3 / §4.2
CF_STAGE3_EXTENSIONS = [
    "business_acquisitions_cash",
    "proceeds_from_asset_sales",
]

# Minimal OCF–NI / CFS reconciliation helpers (nullable, generic)
CF_STAGE3_BRIDGE_HELPERS = [
    "equity_method_income",
    "equity_method_income_net_of_dividends",
    "deferred_tax_expense_benefit",
    "change_in_receivables_cf",
    "change_in_inventory_cf",
    "change_in_payables_cf",
    # Official CFS reconciliation (generic US-GAAP / CF presentation)
    "foreign_currency_transaction_gain_loss",  # P&L-signed; bridge negates for CFS
    "significant_gains_losses_net",  # P&L-signed; bridge negates for CFS
    "other_operating_charges_cf",  # CF presentation (as_is)
    "other_noncash_income_expense",  # P&L-signed; bridge negates for CFS
    "increase_decrease_in_operating_capital",  # XBRL IncreaseDecrease*; bridge negates
    "net_change_in_operating_assets_liabilities",  # CFS-signed aggregate WC change
]


# Stage 4 optional growth extensions (nullable, disclosed-only) — SPEC_LOCKED §7.2
# Only when company discloses; else remain None with reason codes at eval time.
IS_STAGE4_OPTIONAL = [
    "revenue_organic_growth_yoy",  # fraction when disclosed
    "revenue_acquired_impact_yoy",
    "constant_currency_revenue_growth_yoy",
    "volume_metric",
    "same_store_sales_yoy",
    "backlog_or_rpo",
]
# Non-numeric / definition companions (nullable)
STAGE4_DEFINITION_FIELDS = [
    "volume_metric_definition",
    "price_mix_comment_ref",
    "geo_revenue_split",  # coarse dict when mapped
]

# Stage 5 optional economics extensions (nullable, disclosed-only) — SPEC_LOCKED §10.2 / D9
# Prefer derive + semantic-first; add Normalized only if UAT proves need. Zero required in v1.
IS_STAGE5_OPTIONAL = [
    "contribution_margin",  # rare; only if issuer discloses comparable
    "take_rate",  # network/payments when disclosed
    "incremental_operating_margin_disclosed",  # only if issuer discloses
]
# Non-numeric / nested companions (nullable)
STAGE5_DEFINITION_FIELDS = [
    "segment_operating_margin",  # dict when mapped
    "contribution_margin_definition",
    "take_rate_definition",
]


_NON_NUMERIC_EXTENSIONS = (
    "debt_maturity_buckets",
    "restricted_cash_flag",
    "short_term_debt_includes_current_ltd",
    "client_funds_business",
    "volume_metric_definition",
    "price_mix_comment_ref",
    "geo_revenue_split",
    "segment_operating_margin",
    "contribution_margin_definition",
    "take_rate_definition",
)

ALL_NUMERIC_FIELDS = (
    IS_FIELDS
    + BS_CORE_FIELDS
    + [f for f in BS_STAGE2_EXTENSIONS if f not in _NON_NUMERIC_EXTENSIONS]
    + BS_STAGE3_EXTENSIONS
    + CF_FIELDS
    + CF_STAGE3_EXTENSIONS
    + CF_STAGE3_BRIDGE_HELPERS
    + IS_STAGE4_OPTIONAL
    + IS_STAGE5_OPTIONAL
)

META_KEYS = [
    "ticker",
    "cik",
    "entity_name",
    "gate0_class",
    "reporting_currency",
    "period_type",
    "period_key",
    "fiscal_year",
    "fiscal_period",
    "period_start",
    "period_end",
    "filed_at",
    "available_as_of",
    "accession",
    "source_id",
    "version_id",
    "status",
    "accepted_at",
    "supersedes",
    "superseded_by",
    "change_reason",
    "statement_basis",
    "unit_scale",
    "review_status",
]


def empty_fields() -> dict[str, Any]:
    """Return contract field dict with all numeric/nullable fields set to None."""
    out: dict[str, Any] = {k: None for k in ALL_NUMERIC_FIELDS}
    out["debt_maturity_buckets"] = None
    out["restricted_cash_flag"] = None
    out["short_term_debt_includes_current_ltd"] = None
    for k in STAGE4_DEFINITION_FIELDS:
        out[k] = None
    for k in STAGE5_DEFINITION_FIELDS:
        out[k] = None
    return out


def blank_period_document(
    ticker: str,
    period_key: str,
    version_id: str,
    period_type: str = "FY",
    **meta_overrides: Any,
) -> dict[str, Any]:
    """Build a blank Normalized period version document."""
    doc: dict[str, Any] = {
        "ticker": ticker.upper(),
        "cik": None,
        "entity_name": None,
        "gate0_class": "operating",
        "reporting_currency": "USD",
        "period_type": period_type,
        "period_key": period_key,
        "fiscal_year": None,
        "fiscal_period": None,
        "period_start": None,
        "period_end": None,
        "filed_at": None,
        "available_as_of": None,
        "accession": None,
        "source_id": None,
        "version_id": version_id,
        "status": "draft",
        "accepted_at": None,
        "supersedes": None,
        "superseded_by": None,
        "change_reason": "initial",
        "statement_basis": "us-gaap",
        "unit_scale": "as_reported",
        "review_status": "pending",
        "fields": empty_fields(),
        "lineage": [],
        "field_uncertainty": {},
        "notes": [],
    }
    for k, v in meta_overrides.items():
        if k == "fields" and isinstance(v, dict):
            doc["fields"].update(v)
        elif k in doc:
            doc[k] = v
        else:
            doc[k] = v
    return doc


def validate_gate0_operating(doc: dict[str, Any]) -> tuple[bool, str | None]:
    g = doc.get("gate0_class") or "operating"
    if g != "operating":
        return False, f"gate0_class={g}: Operating contract N/A (FI/Commodity out of scope for v1)"
    return True, None
