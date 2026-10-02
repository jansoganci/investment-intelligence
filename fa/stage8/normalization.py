"""Archetype-aware normalized base honesty — no aggressive normalization.

Expose normalization_uncertainty. Prefer Stage 3 cash truth.
A7: recurring M&A = reinvestment; organic vs acq exhibits; no free-organic acq growth.
A8/A9: mid-cycle notes (mandatory).
"""
from __future__ import annotations

from statistics import median
from typing import Any


def _finite(vals: list[float | None]) -> list[float]:
    return [float(v) for v in vals if v is not None]


def _median_or_none(vals: list[float]) -> float | None:
    return float(median(vals)) if vals else None


def build_normalized_base(
    cash_fy_series: list[dict[str, Any]],
    *,
    primary_archetype: str | None,
    secondary_traits: list[str] | None = None,
    s6_flags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Thin normalized base:
    - Prefer OCF median (cash-preferring) over adjusted EPS worship
    - FCF = OCF − CapEx when CapEx present; else OCF with uncertainty↑
    - A7: separate organic vs acquisition exhibits; acq capital = reinvestment
    - Never invent maint CapEx
    """
    traits = [t.lower() for t in (secondary_traits or [])]
    s6 = list(s6_flags or [])
    is_a7 = primary_archetype == "A7" or any(
        t in {"acquisitive", "serial_acquirer", "bolt_on", "m&a", "ma_heavy"} for t in traits
    )
    is_cyclical = primary_archetype in {"A8", "A9"}

    ocf_vals = _finite([r.get("operating_cash_flow") for r in cash_fy_series])
    capex_vals = _finite([r.get("capex") for r in cash_fy_series])
    acq_vals = _finite([r.get("business_acquisitions_cash") for r in cash_fy_series])
    ni_vals = _finite([r.get("net_income") for r in cash_fy_series])
    rev_vals = _finite([r.get("revenue") for r in cash_fy_series])
    sbc_vals = _finite([r.get("sbc_expense") for r in cash_fy_series])
    fcf_disclosed = _finite([r.get("free_cash_flow") for r in cash_fy_series])

    uncertainty_drivers: list[str] = []
    notes: list[str] = []

    ocf_base = _median_or_none(ocf_vals[-3:] if len(ocf_vals) >= 3 else ocf_vals)
    ni_base = _median_or_none(ni_vals[-3:] if len(ni_vals) >= 3 else ni_vals)
    latest_ocf = ocf_vals[-1] if ocf_vals else None
    latest_rev = rev_vals[-1] if rev_vals else None
    latest_acq = acq_vals[-1] if acq_vals else None

    # FCF construction
    fcf_rows = []
    for r in cash_fy_series:
        ocf = r.get("operating_cash_flow")
        capex = r.get("capex")
        disclosed = r.get("free_cash_flow")
        fcf = None
        method = None
        if disclosed is not None:
            fcf = float(disclosed)
            method = "disclosed_fcf"
        elif ocf is not None and capex is not None:
            fcf = float(ocf) - float(capex)
            method = "ocf_minus_capex"
        elif ocf is not None:
            fcf = float(ocf)
            method = "ocf_proxy_capex_unknown"
        fcf_rows.append(
            {
                "period_key": r.get("period_key"),
                "ocf": ocf,
                "capex": capex,
                "acq_cash": r.get("business_acquisitions_cash"),
                "fcf_like": fcf,
                "method": method,
            }
        )

    fcf_like_vals = _finite([r["fcf_like"] for r in fcf_rows if r.get("method") != "ocf_proxy_capex_unknown"])
    fcf_proxy_vals = _finite([r["fcf_like"] for r in fcf_rows])
    if fcf_like_vals:
        fcf_base = _median_or_none(fcf_like_vals[-3:] if len(fcf_like_vals) >= 3 else fcf_like_vals)
        fcf_method = "ocf_minus_capex_or_disclosed"
    elif fcf_proxy_vals:
        fcf_base = _median_or_none(fcf_proxy_vals[-3:] if len(fcf_proxy_vals) >= 3 else fcf_proxy_vals)
        fcf_method = "ocf_proxy_capex_unknown"
        uncertainty_drivers.append("capex_unknown_fcf_proxy")
        notes.append(
            "CapEx null/unknown across window — FCF proxy uses OCF; maint CapEx NOT invented; range widened"
        )
    else:
        fcf_base = None
        fcf_method = "unavailable"
        uncertainty_drivers.append("no_cash_base")

    if not capex_vals:
        uncertainty_drivers.append("capex_undisclosed")

    # Owner-earnings companion (thin): period-coherent OCF − CapEx (Wave 3 / A7).
    # Aggregation remains median-of-window; pairing must use same compatible fiscal periods.
    # Do NOT compute median(OCF) − median(CapEx) (silent cross-year mix).
    # If no compatible same-period pairs → expose missing/uncertain; do not substitute another year.
    oe_base = None
    oe_label = "NOT_APPLICABLE"
    oe_period_keys: list[str] = []
    paired_oe_vals: list[float] = []
    for r in cash_fy_series:
        ocf_r = r.get("operating_cash_flow")
        cap_r = r.get("capex")
        if ocf_r is not None and cap_r is not None:
            paired_oe_vals.append(float(ocf_r) - float(cap_r))
            pk = r.get("period_key")
            if pk:
                oe_period_keys.append(str(pk))
    if paired_oe_vals:
        use_vals = paired_oe_vals[-3:] if len(paired_oe_vals) >= 3 else paired_oe_vals
        use_keys = oe_period_keys[-3:] if len(oe_period_keys) >= 3 else oe_period_keys
        oe_base = _median_or_none(use_vals)
        oe_label = "ocf_minus_reported_capex_proxy_period_aligned"
        notes.append(
            "Owner-earnings companion = median of per-year (OCF−CapEx) over "
            f"{use_keys or 'aligned periods'} — period-coherent; no silent cross-year mix "
            "(not forced maint CapEx invention)"
        )
    elif not capex_vals:
        notes.append(
            "Owner-earnings companion NOT_APPLICABLE — CapEx/maint unknown; do not invent"
        )
        uncertainty_drivers.append("oe_no_compatible_ocf_capex_pair")
    else:
        notes.append(
            "Owner-earnings companion unavailable — no compatible same-period OCF+CapEx pairs; "
            "do not substitute another year"
        )
        uncertainty_drivers.append("oe_no_compatible_ocf_capex_pair")

    # A7 dual exhibits
    organic_exhibit: dict[str, Any] | None = None
    acq_exhibit: dict[str, Any] | None = None
    if is_a7:
        acq_median = _median_or_none(acq_vals[-3:] if len(acq_vals) >= 3 else acq_vals)
        acq_sum = sum(acq_vals) if acq_vals else None
        recurring_ma = bool(acq_vals) and len([v for v in acq_vals if v and v > 0]) >= 2
        organic_exhibit = {
            "label": "organic_cash_base",
            "ocf_base": ocf_base,
            "fcf_like_base": fcf_base,
            "note": (
                "Organic-preferring cash base for forward/reverse drivers — "
                "acquired growth is NOT free organic"
            ),
            "no_free_organic_acquired_growth": True,
        }
        acq_exhibit = {
            "label": "acquisition_reinvestment",
            "acq_cash_median": acq_median,
            "acq_cash_multi_year_sum": acq_sum,
            "recurring_ma_as_reinvestment": recurring_ma,
            "latest_acq_cash": latest_acq,
            "s6_flags_consumed": [f for f in s6 if f.startswith("S6_H7_")],
            "note": (
                "Recurring M&A = reinvestment capital (not deal-by-deal DCF). "
                "Include acquisition capital in reinvestment honesty; opacity → uncertainty↑"
            ),
            "no_deal_by_deal_dcf": True,
        }
        if "S6_H7_ACQ_RETURN_OPACITY" in s6:
            uncertainty_drivers.append("s6_acq_return_opacity")
            notes.append("S6_H7_ACQ_RETURN_OPACITY consumed — acquisition-return opacity widens valuation uncertainty")
        if "S6_H7_DUAL_VIEW_CONFLICT" in s6:
            uncertainty_drivers.append("s6_dual_view_conflict")
            notes.append("S6_H7_DUAL_VIEW_CONFLICT consumed — dual ROIC view conflict noted for A7 honesty")
        if recurring_ma:
            uncertainty_drivers.append("recurring_ma_opacity")
        notes.append("A7 dual organic/acq exhibits emitted; no free-organic acquired growth")

    if is_cyclical:
        notes.append(
            f"{primary_archetype} mid-cycle normalization mandatory — peak EPS capitalization = FP-V4 watch"
        )
        uncertainty_drivers.append("cyclical_mid_cycle_required")

    if sbc_vals:
        notes.append(
            f"SBC present (median≈{_median_or_none(sbc_vals):,.0f}) — never ignore as free non-cash (FP-V11)"
        )

    # Uncertainty label (qualitative)
    n_drivers = len(set(uncertainty_drivers))
    if fcf_base is None and ocf_base is None:
        norm_uncertainty = "extreme"
    elif n_drivers >= 4 or (is_a7 and "s6_acq_return_opacity" in uncertainty_drivers):
        norm_uncertainty = "high"
    elif n_drivers >= 2:
        norm_uncertainty = "moderate"
    elif n_drivers == 1:
        norm_uncertainty = "moderate"
    else:
        norm_uncertainty = "low"

    # Aggressive normalization forbidden — we only use medians of reported cash
    return {
        "primary_archetype": primary_archetype,
        "ocf_base": ocf_base,
        "fcf_like_base": fcf_base,
        "fcf_method": fcf_method,
        "ni_base": ni_base,
        "latest_ocf": latest_ocf,
        "latest_revenue": latest_rev,
        "owner_earnings_base": oe_base,
        "owner_earnings_label": oe_label,
        "owner_earnings_period_keys": oe_period_keys[-3:] if len(oe_period_keys) >= 3 else list(oe_period_keys),
        "owner_earnings_period_coherent": bool(paired_oe_vals),
        "fcf_rows": fcf_rows,
        "normalization_uncertainty": norm_uncertainty,
        "uncertainty_drivers": sorted(set(uncertainty_drivers)),
        "notes": notes,
        "a7_dual": is_a7,
        "organic_exhibit": organic_exhibit,
        "acq_exhibit": acq_exhibit,
        "mid_cycle_mandatory": is_cyclical,
        "no_aggressive_normalization": True,
        "prefer_cash_over_adjusted_eps": True,
        "sbc_honesty": bool(sbc_vals),
        # Consumers must not treat OCF proxy as FCFF when CapEx unknown
        "authoritative_fcff_eligible": fcf_method not in {
            "ocf_proxy_capex_unknown",
            "unavailable",
        },
        "base_incomplete": fcf_method == "ocf_proxy_capex_unknown",
    }
