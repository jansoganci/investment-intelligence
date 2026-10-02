"""Deterministic Stage 8 bridge / share / debt / cash math — no LLM arithmetic.

EV/equity bridge; scenario plumbing helpers; dual-terminal CROSS-CHECK scaffolding.
Never average terminals. Never silent override.
No BUY/SELL. No universal thresholds.
"""
from __future__ import annotations

from typing import Any

from ..models import CalcResult


def _num(fields: dict, key: str) -> float | None:
    v = fields.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _select_fy(
    periods: list[dict[str, Any]], *, prefer_fy: int = 5
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fy = sorted(
        [p for p in periods if p.get("period_type") == "FY"],
        key=lambda d: d.get("period_key") or "",
    )
    sel = fy[-prefer_fy:] if fy else []
    flags = {
        "fy_available": len(fy),
        "fy_used": len(sel),
        "history_thin": len(fy) < 3,
        "prefer_fy": prefer_fy,
    }
    return sel, flags


def extract_cs_from_period(period: dict[str, Any] | None) -> dict[str, Any]:
    """Filing-period capital structure fields from a Normalized period."""
    if not period:
        return {
            "period_key": None,
            "period_end": None,
            "reporting_currency": None,
            "shares_diluted_weighted": None,
            "shares_outstanding": None,
            "cash_and_equivalents": None,
            "short_term_investments": None,
            "total_debt": None,
            "long_term_debt": None,
            "short_term_debt": None,
            "lease_liability_current": None,
            "lease_liability_noncurrent": None,
            "sbc_expense": None,
            "null_reasons": {"period": "No filing period available for CS"},
        }
    fields = period.get("fields") or {}
    nulls: dict[str, str] = {}
    out = {
        "period_key": period.get("period_key"),
        "period_end": period.get("period_end"),
        "filed_at": period.get("filed_at") or period.get("available_as_of"),
        "reporting_currency": period.get("reporting_currency") or "USD",
        "shares_diluted_weighted": _num(fields, "shares_diluted_weighted"),
        "shares_outstanding": _num(fields, "shares_outstanding"),
        "shares_basic_weighted": _num(fields, "shares_basic_weighted"),
        "cash_and_equivalents": _num(fields, "cash_and_equivalents"),
        "short_term_investments": _num(fields, "short_term_investments"),
        "total_debt": _num(fields, "total_debt"),
        "long_term_debt": _num(fields, "long_term_debt"),
        "short_term_debt": _num(fields, "short_term_debt"),
        "lease_liability_current": _num(fields, "lease_liability_current"),
        "lease_liability_noncurrent": _num(fields, "lease_liability_noncurrent"),
        "sbc_expense": _num(fields, "sbc_expense"),
        "equity_parent": _num(fields, "equity_parent"),
    }
    for k in (
        "shares_diluted_weighted",
        "shares_outstanding",
        "cash_and_equivalents",
        "total_debt",
    ):
        if out.get(k) is None:
            nulls[k] = f"Missing {k} in filing-period fields"
    out["null_reasons"] = nulls
    return out


def prefer_diluted_shares(cs: dict[str, Any]) -> tuple[float | None, str]:
    """Prefer diluted shares for market bridge; fall back with label."""
    dil = cs.get("shares_diluted_weighted")
    if dil is not None and dil > 0:
        return dil, "shares_diluted_weighted"
    out = cs.get("shares_outstanding")
    if out is not None and out > 0:
        return out, "shares_outstanding_fallback"
    basic = cs.get("shares_basic_weighted")
    if basic is not None and basic > 0:
        return basic, "shares_basic_weighted_fallback"
    return None, "shares_unavailable"


def build_ev_equity_bridge(
    *,
    share_price: float | None,
    cs: dict[str, Any],
    include_leases_in_debt: bool = False,
) -> dict[str, Any]:
    """
    Canonical bridge (Plan §4):
      equity_mkt_cap = price × diluted_shares
      EV = equity + gross debt [+ prefs/NCI if material] − cash [− STI if separable]
    Never invent missing inputs — null + reason.
    """
    nulls: dict[str, str] = {}
    shares, share_basis = prefer_diluted_shares(cs)
    if share_price is None:
        nulls["share_price"] = "Missing share_price"
    if shares is None:
        nulls["shares"] = "Missing diluted/outstanding shares"

    equity_mkt_cap = None
    if share_price is not None and shares is not None:
        equity_mkt_cap = float(share_price) * float(shares)

    debt = cs.get("total_debt")
    if debt is None:
        # Prefer components sum when total_debt null
        ltd = cs.get("long_term_debt") or 0.0
        std = cs.get("short_term_debt") or 0.0
        if cs.get("long_term_debt") is not None or cs.get("short_term_debt") is not None:
            debt = float(ltd) + float(std)
            nulls["total_debt"] = "total_debt null — used LT+ST components where present"
        else:
            nulls["total_debt"] = "Missing total_debt and components"

    lease_add = 0.0
    if include_leases_in_debt:
        lease_add = float(cs.get("lease_liability_current") or 0.0) + float(
            cs.get("lease_liability_noncurrent") or 0.0
        )

    cash = cs.get("cash_and_equivalents")
    if cash is None:
        nulls["cash_and_equivalents"] = "Missing cash_and_equivalents"

    sti = cs.get("short_term_investments")
    # Only subtract STI when honestly present (separable non-op) — do not invent
    sti_sub = float(sti) if sti is not None else 0.0

    ev = None
    if equity_mkt_cap is not None and debt is not None and cash is not None:
        ev = equity_mkt_cap + float(debt) + lease_add - float(cash) - sti_sub
    else:
        nulls["enterprise_value"] = "Cannot compute EV — missing equity/debt/cash inputs"

    net_debt = None
    if debt is not None and cash is not None:
        net_debt = float(debt) + lease_add - float(cash) - sti_sub

    return {
        "share_price": share_price,
        "shares_used": shares,
        "share_basis": share_basis,
        "equity_market_cap": equity_mkt_cap,
        "gross_debt": debt,
        "lease_add_to_debt": lease_add if include_leases_in_debt else 0.0,
        "leases_included_in_debt": include_leases_in_debt,
        "cash_and_equivalents": cash,
        "sti_subtracted": sti_sub if sti is not None else None,
        "prefs": None,  # not invent
        "nci": None,
        "net_debt": net_debt,
        "enterprise_value": ev,
        "equity_value_from_ev": (
            (ev - float(debt) - lease_add + float(cash) + sti_sub)
            if ev is not None and debt is not None and cash is not None
            else equity_mkt_cap
        ),
        "filing_period_key": cs.get("period_key"),
        "filing_period_end": cs.get("period_end"),
        "null_reasons": nulls,
        "bridge_formula": (
            "EV = price×diluted_shares + gross_debt[+leases] − cash[−STI] "
            "(prefs/NCI null unless material evidence)"
        ),
    }


def equity_iv_from_enterprise(
    enterprise_iv: float | None,
    *,
    gross_debt: float | None,
    cash: float | None,
    sti: float | None = None,
    lease_add: float = 0.0,
) -> float | None:
    """Enterprise IV → equity IV via same bridge (debt/cash)."""
    if enterprise_iv is None or gross_debt is None or cash is None:
        return None
    sti_v = float(sti or 0.0)
    return float(enterprise_iv) - float(gross_debt) - float(lease_add) + float(cash) + sti_v


def per_share(value: float | None, shares: float | None) -> float | None:
    if value is None or shares is None or shares <= 0:
        return None
    return float(value) / float(shares)


def fy_series(
    periods: list[dict[str, Any]], keys: list[str]
) -> list[dict[str, Any]]:
    rows = []
    for p in periods:
        fields = p.get("fields") or {}
        row: dict[str, Any] = {
            "period_key": p.get("period_key"),
            "period_end": p.get("period_end"),
        }
        for k in keys:
            row[k] = _num(fields, k)
        rows.append(row)
    return rows


def compute_stage8_bridge_metrics(
    periods: list[dict[str, Any]],
    *,
    share_price: float | None,
    prefer_fy: int = 5,
) -> CalcResult:
    """Deterministic CS extract + bridge scaffolding (price may be null)."""
    fy, flags = _select_fy(periods, prefer_fy=prefer_fy)
    latest = fy[-1] if fy else None
    cs = extract_cs_from_period(latest)
    bridge = build_ev_equity_bridge(share_price=share_price, cs=cs)

    # Dilution trajectory across window
    share_rows = fy_series(
        fy, ["shares_outstanding", "shares_diluted_weighted", "sbc_expense"]
    )
    first_sh = next(
        (
            r["shares_outstanding"]
            for r in share_rows
            if r.get("shares_outstanding") is not None
        ),
        None,
    )
    last_sh = next(
        (
            r["shares_outstanding"]
            for r in reversed(share_rows)
            if r.get("shares_outstanding") is not None
        ),
        None,
    )
    net_share_change = None
    if first_sh is not None and last_sh is not None:
        net_share_change = last_sh - first_sh
    sbc_sum = sum(r["sbc_expense"] for r in share_rows if r.get("sbc_expense") is not None)

    # Cash / OCF / acq series for normalization handoff
    cash_rows = fy_series(
        fy,
        [
            "operating_cash_flow",
            "capex",
            "business_acquisitions_cash",
            "net_income",
            "operating_income",
            "revenue",
            "sbc_expense",
            "free_cash_flow",
        ],
    )

    nulls = dict(bridge.get("null_reasons") or {})
    nulls.update(cs.get("null_reasons") or {})

    metrics = {
        "history_flags": flags,
        "periods_fy_keys": [p.get("period_key") for p in fy],
        "capital_structure": cs,
        "ev_equity_bridge": bridge,
        "share_trajectory": {
            "rows": share_rows,
            "net_share_change": net_share_change,
            "sbc_expense_multi_year": sbc_sum if sbc_sum else None,
            "sbc_never_ignore": True,
            "no_double_count_policy": (
                "preserve SBC in economics OR dilute shares for per-share IV; "
                "show both honesty exhibits when material"
            ),
        },
        "cash_fy_series": cash_rows,
        "no_method_average": True,
        "no_terminal_average": True,
        "no_buy_sell": True,
        "no_universal_mos_pct": True,
        "no_capm_engine": True,
    }
    return CalcResult(metrics=metrics, null_reasons=nulls)
