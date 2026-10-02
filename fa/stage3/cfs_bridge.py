"""Official Cash Flow Statement reconciliation bridge (generic; deterministic arithmetic only).

Reconstructs OCF from the NI→OCF reconciliation lines when available.
No issuer hardcoding. Ambiguous mappings stay null + reason; unmapped lines
go to company_specific_cfs_adjustments rather than being dropped.
"""
from __future__ import annotations

from typing import Any

# Residual tolerance for money rounding / scale (as-reported USD floats).
_MONEY_EPS = 0.51

# Canonical buckets (nullable conceptual). Each row:
#   bucket_key, normalized_field, sign_multiplier, nature_category, role
# sign_multiplier applied to Normalized field value to get CFS addend
# (amount added in NI + adjustments → OCF). Fields that already store CFS
# presentation amounts use sign=+1.
_CFS_ADJUSTMENT_SPECS: list[tuple[str, str, int, str, str]] = [
    ("depreciation_amortization", "depreciation_amortization", 1, "accounting/non_cash", "non_cash_addback"),
    ("sbc_expense", "sbc_expense", 1, "accounting/non_cash", "non_cash_addback"),
    ("deferred_tax_expense_benefit", "deferred_tax_expense_benefit", 1, "accounting/non_cash", "deferred_tax"),
    # Equity-method income net of dividends is income in NI; CFS deducts it.
    (
        "equity_income_loss_net_of_dividends",
        "equity_method_income_net_of_dividends",
        -1,
        "structural",
        "cf_equity_method_adjustment",
    ),
    # P&L FX gain/(loss): CFS reverses → negate.
    (
        "foreign_currency_adjustments_cf",
        "foreign_currency_transaction_gain_loss",
        -1,
        "accounting/non_cash",
        "fx_cf_adjustment",
    ),
    # Significant gains/(losses) in NI: CFS reverses → negate.
    (
        "significant_gains_losses_net_cf",
        "significant_gains_losses_net",
        -1,
        "one_time/deal",
        "gains_losses_cf_adjustment",
    ),
    # Other operating charges already in CF-statement presentation.
    (
        "other_operating_charges_cf",
        "other_operating_charges_cf",
        1,
        "accounting/non_cash",
        "other_operating_cf",
    ),
    # Other noncash income/(expense) P&L-signed: CFS reverses → negate.
    (
        "other_items_cf",
        "other_noncash_income_expense",
        -1,
        "accounting/non_cash",
        "other_items_cf",
    ),
    # Prefer CFS-signed aggregate when mapped; else derive from IncreaseDecrease*.
    (
        "net_change_in_operating_assets_liabilities",
        "net_change_in_operating_assets_liabilities",
        1,
        "wc/timing",
        "wc_aggregate_cf",
    ),
]


def _num(fields: dict, key: str) -> float | None:
    v = fields.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _money_equal(a: float, b: float) -> bool:
    return abs(a - b) <= _MONEY_EPS


def select_cfs_starting_ni(fields: dict[str, Any]) -> tuple[float | None, str | None, str | None]:
    """
    Prefer consolidated NI when CFS starts from consolidated (ProfitLoss).
    Returns (amount, basis_label, source_field).
    """
    consol = _num(fields, "net_income_consolidated")
    if consol is not None:
        return consol, "consolidated", "net_income_consolidated"
    # Fallbacks — do not mix bases silently
    for field, basis in (
        ("net_income", "attributable_or_reported"),
        ("net_income_attributable", "attributable"),
    ):
        v = _num(fields, field)
        if v is not None:
            return v, basis, field
    return None, None, None


def _company_specific_from_period(period: dict[str, Any]) -> list[dict[str, Any]]:
    """Preserve issuer-specific CFS lines attached on the period document."""
    raw = period.get("company_specific_cfs_adjustments")
    if not raw:
        # Also allow under fields meta
        raw = (period.get("fields") or {}).get("company_specific_cfs_adjustments")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = item.get("label") or item.get("tag_or_source") or "unlabeled"
        amt = item.get("amount")
        try:
            amt_f = float(amt) if amt is not None else None
        except (TypeError, ValueError):
            amt_f = None
        out.append(
            {
                "label": label,
                "amount": amt_f,
                "tag_or_source": item.get("tag_or_source"),
                "include_in_sum": bool(item.get("include_in_sum", amt_f is not None)),
                "notes": item.get("notes"),
            }
        )
    return out


def assemble_cfs_reconciliation(period: dict[str, Any]) -> dict[str, Any]:
    """
    Reconstruct OCF from official CFS NI→OCF reconciliation lines.

    Status:
      RECONCILED — residual exactly 0 within money rounding/scale
      PARTIALLY_RECONCILED — some components present but residual nonzero or key lines missing
      UNRESOLVED — cannot build (missing CFS-basis NI and/or reported OCF)

    Missing ingestion/mapping → automation/data_problem (not automatic cash-quality concern).
    """
    f = period.get("fields") or {}
    pk = period.get("period_key") or ""
    ocf = _num(f, "operating_cash_flow")
    ni_cfs, ni_basis, ni_field = select_cfs_starting_ni(f)
    ni_attr = _num(f, "net_income_attributable")
    if ni_attr is None:
        ni_attr = _num(f, "net_income")
    ni_consol = _num(f, "net_income_consolidated")

    buckets: dict[str, float | None] = {
        "net_income_cfs_basis": ni_cfs,
        "depreciation_amortization": None,
        "sbc_expense": None,
        "deferred_tax_expense_benefit": None,
        "equity_income_loss_net_of_dividends": None,
        "foreign_currency_adjustments_cf": None,
        "significant_gains_losses_net_cf": None,
        "other_operating_charges_cf": None,
        "other_items_cf": None,
        "net_change_in_operating_assets_liabilities": None,
    }
    components: list[dict[str, Any]] = []
    nature: set[str] = set()
    null_reasons: dict[str, str] = {}
    data_problems: list[str] = []

    # WC aggregate fallback: if CFS-signed field null, derive from IncreaseDecrease*
    wc_cfs = _num(f, "net_change_in_operating_assets_liabilities")
    if wc_cfs is None:
        inc = _num(f, "increase_decrease_in_operating_capital")
        if inc is not None:
            wc_cfs = -inc
            # Treat as available for this assembly only
            f = dict(f)
            f["net_change_in_operating_assets_liabilities"] = wc_cfs

    for bucket, field, sign, category, role in _CFS_ADJUSTMENT_SPECS:
        raw = _num(f, field)
        if raw is None:
            null_reasons[bucket] = f"Normalized field '{field}' null — mapping/ingestion gap"
            data_problems.append(f"missing:{field}")
            continue
        cfs_amt = raw * sign
        buckets[bucket] = cfs_amt
        components.append(
            {
                "bucket": bucket,
                "field": field,
                "raw_amount": raw,
                "sign": sign,
                "amount": cfs_amt,
                "role": role,
                "nature": category,
                "certainty": "FACT",
                "source": "normalized",
            }
        )
        nature.add(category)

    company_specific = _company_specific_from_period(period)
    for item in company_specific:
        if item.get("include_in_sum") and item.get("amount") is not None:
            components.append(
                {
                    "bucket": "company_specific_cfs_adjustments",
                    "field": item.get("tag_or_source") or item.get("label"),
                    "raw_amount": item["amount"],
                    "sign": 1,
                    "amount": item["amount"],
                    "role": "company_specific",
                    "nature": "company_specific",
                    "certainty": "FACT",
                    "source": "company_specific_cfs_adjustments",
                    "label": item.get("label"),
                }
            )
            nature.add("company_specific")

    # Subcomponents (informational; not double-counted into sum)
    wc_subcomponents = []
    for sub_field, label in (
        ("change_in_receivables_cf", "receivables"),
        ("change_in_inventory_cf", "inventory"),
        ("change_in_payables_cf", "payables"),
    ):
        v = _num(f, sub_field)
        if v is not None:
            wc_subcomponents.append({"field": sub_field, "label": label, "amount_raw_xbrl": v})

    status: str
    reconstructed: float | None = None
    residual: float | None = None
    interpretation: list[str] = []

    if ni_cfs is None or ocf is None:
        status = "UNRESOLVED"
        data_problems.append("cannot_build: need net_income_cfs_basis and operating_cash_flow")
        interpretation.append("automation/data_problem")
    else:
        reconstructed = ni_cfs + sum(c["amount"] for c in components)
        residual = ocf - reconstructed
        if _money_equal(residual, 0.0):
            status = "RECONCILED"
        elif components:
            status = "PARTIALLY_RECONCILED"
            if data_problems:
                interpretation.append("automation/data_problem")
            if abs(residual) > _MONEY_EPS:
                interpretation.append("unresolved evidence")
        else:
            status = "PARTIALLY_RECONCILED"
            interpretation.append("automation/data_problem")
            data_problems.append("no_cfs_adjustment_components_mapped")

    # Nature / interpretation categories (descriptive — not pass/fail)
    for c in components:
        n = c["nature"]
        if n not in interpretation:
            interpretation.append(n)
    if status == "RECONCILED":
        # OCF < NI alone is not a cash-quality concern when CFS reconciles
        interpretation = [x for x in interpretation if x != "unresolved evidence"]
        if not interpretation:
            interpretation.append("accounting/non_cash")
    elif status == "UNRESOLVED":
        if "automation/data_problem" not in interpretation:
            interpretation.append("automation/data_problem")

    # Key-line missing flag (WC aggregate often material)
    key_lines_missing = buckets.get("net_change_in_operating_assets_liabilities") is None and status != "UNRESOLVED"
    if key_lines_missing and status == "RECONCILED":
        pass  # residual 0 already proves adequacy
    elif key_lines_missing and status == "PARTIALLY_RECONCILED":
        data_problems.append("key_line_missing:net_change_in_operating_assets_liabilities")

    uncertain: list[str] = []
    if status == "UNRESOLVED":
        uncertain.append("Cannot build official CFS reconciliation — data/mapping incomplete")
    elif status == "PARTIALLY_RECONCILED":
        if residual is not None and abs(residual) > _MONEY_EPS:
            uncertain.append(
                f"CFS reconstructed OCF residual={residual} (reported_OCF - reconstructed) — "
                "incomplete mapping or unmapped company lines; automation/data_problem "
                "until residual clears — not automatic cash-quality concern"
            )
        for dp in data_problems:
            if dp.startswith("missing:"):
                uncertain.append(f"Missing CFS component mapping: {dp}")
    # RECONCILED → do NOT keep unexplained-residual exception

    gap_ocf_minus_ni = (ocf - ni_cfs) if (ocf is not None and ni_cfs is not None) else None

    return {
        "period_key": pk,
        "version_id": period.get("version_id"),
        "status": status,
        "reported_ocf": ocf,
        "net_income_cfs_basis": ni_cfs,
        "net_income_basis": ni_basis,
        "net_income_basis_field": ni_field,
        "net_income_attributable": ni_attr,
        "net_income_consolidated": ni_consol,
        "gap_ocf_minus_ni_cfs_basis": gap_ocf_minus_ni,
        "buckets": buckets,
        "components": components,
        "company_specific_cfs_adjustments": company_specific,
        "wc_subcomponents": wc_subcomponents,
        "reconstructed_ocf": reconstructed,
        "unexplained_residual": residual,
        "nature_tags": sorted(nature),
        "interpretation_categories": interpretation,
        "data_problems": data_problems,
        "null_reasons": null_reasons,
        "factual_vs_uncertain": {
            "factual_components": [c.get("bucket") for c in components],
            "uncertain": uncertain,
        },
        "notes": (
            "Official CFS reconciliation: reconstructed_OCF = net_income_cfs_basis + sum(adjustments). "
            "unexplained_residual = reported_OCF - reconstructed_OCF. "
            "Arithmetic is deterministic. Missing mapping → automation/data_problem, "
            "not automatic cash-quality concern. OCF<NI alone ≠ poor cash quality when RECONCILED."
        ),
    }
