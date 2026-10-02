"""Deterministic Stage 6 ROIC / IC / incremental exhibits — no pass/fail bands, no LLM arithmetic.

NOPAT = OP × (1 − t); IC = TA − cash − STI − clear non-op − NIBOL.
Dual ROIC: acquisition-inclusive PRIMARY + tangible companion.
Incremental = ΔNOPAT/ΔIC (≠ Stage 5 Incremental OM).
No numeric ROIC/ROIIC/WACC thresholds. No forced maint CapEx.
"""
from __future__ import annotations

from statistics import median
from typing import Any

from ..models import CalcResult, IncrementalROICWindow

# Arithmetic guard for ΔIC≈0 — not a ROIC/WACC hurdle
_DELTA_IC_NEAR_ZERO_REL = 0.01


def _num(fields: dict, key: str) -> float | None:
    v = fields.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _select_periods(
    periods: list[dict[str, Any]],
    *,
    prefer_fy: int = 5,
    prefer_q: int = 8,
    extend_full_cycle: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    from ..quarter_derivation import select_periods_prefer_contiguous

    fy = sorted(
        [p for p in periods if p.get("period_type") == "FY"],
        key=lambda d: d.get("period_key") or "",
    )
    q_all = sorted(
        [p for p in periods if p.get("period_type") == "Q"],
        key=lambda d: d.get("period_key") or "",
    )
    fy_limit = prefer_fy if not extend_full_cycle else max(prefer_fy, len(fy))
    fy_sel = fy[-fy_limit:] if fy else []
    if extend_full_cycle:
        q_sel = q_all
        contiguous_meta = {"policy": "extend_full_cycle", "contiguous": True}
    else:
        q_sel, contiguous_meta = select_periods_prefer_contiguous(
            q_all, prefer_q=prefer_q
        )
    flags = {
        "fy_available": len(fy),
        "q_available": len(q_all),
        "fy_used": len(fy_sel),
        "q_used": len(q_sel),
        "prefer_ge_3_fy": len(fy) >= 3,
        "history_thin": len(fy) < 3,
        "extend_full_cycle": extend_full_cycle,
        "quarter_policy": contiguous_meta.get("policy"),
        "quarters_contiguous": contiguous_meta.get("contiguous"),
    }
    return fy_sel, q_sel, flags


def sane_etr(pretax: float | None, tax: float | None) -> float | None:
    """ETR = tax/pretax only if pretax > 0 and ETR ∈ [0, 0.60]."""
    if pretax is None or tax is None:
        return None
    if pretax <= 0:
        return None
    etr = tax / pretax
    if etr < 0 or etr > 0.60:
        return None
    return etr


def resolve_tax_rate(
    fy_fields_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Fallback chain (LOCKED D1):
    (1) median sane ETR (≥2 years) → (2) single sane ETR → (3) statutory 21% labeled
    → (4) missing OP handled by caller → UNKNOWN.
    """
    etrs: list[float] = []
    for f in fy_fields_list:
        e = sane_etr(_num(f, "pretax_income"), _num(f, "income_tax"))
        if e is not None:
            etrs.append(e)
    if len(etrs) >= 2:
        return {
            "tax_rate": float(median(etrs)),
            "tax_rate_source": "median_sane_etr",
            "etr_pool_n": len(etrs),
            "etr_pool": etrs,
        }
    if len(etrs) == 1:
        return {
            "tax_rate": etrs[0],
            "tax_rate_source": "single_sane_etr",
            "etr_pool_n": 1,
            "etr_pool": etrs,
        }
    return {
        "tax_rate": 0.21,
        "tax_rate_source": "statutory_fallback",
        "etr_pool_n": 0,
        "etr_pool": [],
    }


def compute_nopat(
    operating_income: float | None,
    tax_rate: float | None,
    *,
    tax_rate_source: str | None = None,
) -> dict[str, Any]:
    """NOPAT = OP × (1 − t). Neg OP → NOPAT ≤ 0 labeled. Missing OP → UNKNOWN."""
    if operating_income is None:
        return {
            "nopat": None,
            "null_reason": "UNKNOWN",
            "tax_rate": tax_rate,
            "tax_rate_source": tax_rate_source,
            "definition": "op_x_(1_minus_t_norm)",
        }
    if tax_rate is None:
        return {
            "nopat": None,
            "null_reason": "UNKNOWN",
            "tax_rate": None,
            "tax_rate_source": tax_rate_source,
            "definition": "op_x_(1_minus_t_norm)",
        }
    nopat = operating_income * (1.0 - tax_rate)
    return {
        "nopat": nopat,
        "null_reason": None,
        "tax_rate": tax_rate,
        "tax_rate_source": tax_rate_source,
        "definition": "op_x_(1_minus_t_norm)",
        "operating_income": operating_income,
    }


def compute_nibol(fields: dict[str, Any]) -> dict[str, Any]:
    """
    NIBOL = clearly operating non-interest-bearing liabilities.
    Include: AP, deferred/unearned revenue (current+noncurrent), other clear when structured.
    Exclude: debt, lease liabilities (financing), ambiguous → unadjusted.
    Missing component ≠ zero → nibol_incomplete honesty.
    Wave2 A4: do NOT invent client-funds payable; flag incompleteness when
    client-related restricted / funds-held assets are present without a mapped payable.
    """
    components: dict[str, float | None] = {
        "accounts_payable": _num(fields, "accounts_payable"),
        "deferred_revenue_current": _num(fields, "deferred_revenue_current"),
        "deferred_revenue_noncurrent": _num(fields, "deferred_revenue_noncurrent"),
    }
    # Optional structured accrued operating (nullable; not in required contract)
    for opt in ("accrued_operating_expenses", "operating_accruals", "unearned_revenue"):
        if opt in fields and fields.get(opt) is not None:
            components[opt] = _num(fields, opt)
    # Optional client-funds payable ONLY when structured field present — never invent
    client_payable = None
    for opt in ("client_funds_payable", "funds_payable_to_customers", "customer_funds_liability"):
        if opt in fields and fields.get(opt) is not None:
            client_payable = _num(fields, opt)
            components[opt] = client_payable
            break

    present = {k: v for k, v in components.items() if v is not None}
    missing = [k for k, v in components.items() if v is None]
    # Core expected: AP and/or deferred revenue family
    core_expected = ["accounts_payable", "deferred_revenue_current"]
    core_missing = [k for k in core_expected if components.get(k) is None]
    nibol_incomplete = bool(core_missing)

    # Client-funds honesty (Wave2 A4-p2)
    funds_held = _num(fields, "funds_held_for_clients")
    restricted = _num(fields, "restricted_cash_amount")
    cash = _num(fields, "cash_and_equivalents")
    client_biz = fields.get("client_funds_business") is True
    client_asset_present = funds_held is not None or (
        restricted is not None and client_biz
    ) or (
        restricted is not None
        and cash is not None
        and restricted > cash + 1.0
    ) or (restricted is not None and cash is None)
    client_funds_incomplete = bool(client_asset_present and client_payable is None)
    if client_funds_incomplete:
        nibol_incomplete = True

    total = sum(present.values()) if present else None
    if total is None:
        return {
            "nibol": None,
            "components": components,
            "nibol_incomplete": True,
            "client_funds_incomplete": client_funds_incomplete,
            "missing": missing,
            "null_reason": "UNKNOWN",
            "note": "No qualifying NIBOL fields present — honest incompleteness",
        }
    note = (
        "Computed from available qualifying fields; "
        + ("nibol_incomplete=True (core missing)" if core_missing else "core present")
    )
    if client_funds_incomplete:
        note += (
            "; client_funds_incomplete=True (client/restricted funds asset present "
            "without mapped payable — payable not invented)"
        )
    return {
        "nibol": total,
        "components": components,
        "nibol_incomplete": nibol_incomplete,
        "client_funds_incomplete": client_funds_incomplete,
        "missing": missing,
        "null_reason": None,
        "note": note,
    }


def _client_funds_asset_for_ic(fields: dict[str, Any]) -> dict[str, Any]:
    """
    Wave2 A4: customer-related restricted / funds-held assets are not owner free cash.
    Exclude from IC when separable from cash_and_equivalents. Never invent payable.

    client_funds_business (mapper): FundsHeldForClients pattern → restricted cash is
    customer matched-book even when restricted < cash (INTU FY2026 class).
    Without that pattern, restricted ≤ cash is treated as of-which inside cash (DE).
    """
    funds_held = _num(fields, "funds_held_for_clients")
    restricted = _num(fields, "restricted_cash_amount")
    cash = _num(fields, "cash_and_equivalents")
    client_biz = fields.get("client_funds_business") is True
    if funds_held is not None:
        return {
            "client_funds_asset": funds_held,
            "client_funds_source": "funds_held_for_clients",
            "exclude_from_ic": funds_held,
        }
    if restricted is not None and client_biz:
        return {
            "client_funds_asset": restricted,
            "client_funds_source": "restricted_cash_amount_client_funds_business",
            "exclude_from_ic": restricted,
        }
    # Restricted exceeds cash → separate matched-book / client asset
    if restricted is not None and cash is not None and restricted > cash + 1.0:
        return {
            "client_funds_asset": restricted,
            "client_funds_source": "restricted_cash_amount_separate_from_cash",
            "exclude_from_ic": restricted,
        }
    if restricted is not None and cash is None:
        return {
            "client_funds_asset": restricted,
            "client_funds_source": "restricted_cash_amount_without_cash",
            "exclude_from_ic": restricted,
        }
    # Restricted already inside cash (cash ≥ restricted, no client-funds pattern)
    return {
        "client_funds_asset": funds_held,
        "client_funds_source": None,
        "exclude_from_ic": 0.0,
        "restricted_inside_cash": bool(restricted is not None and cash is not None),
    }


def compute_ic_inclusive(fields: dict[str, Any]) -> dict[str, Any]:
    """
    IC_inclusive = TA − cash − STI − client restricted funds − clear non-op − NIBOL.
    Goodwill/intangibles INCLUDED. Lease ROU inside TA when ASC 842. Lease liab ≠ NIBOL.
    Wave2 A4: exclude customer-related restricted funds; missing cash → IC UNKNOWN
    (do not treat missing cash as zero exclusion under exclude_cash policy).
    """
    ta = _num(fields, "total_assets")
    cash = _num(fields, "cash_and_equivalents")
    sti = _num(fields, "short_term_investments")
    # Clearly non-op financial when separable (optional; do not invent)
    non_op = _num(fields, "non_operating_financial_assets")
    if non_op is None:
        non_op = _num(fields, "long_term_marketable_securities")

    nibol_info = compute_nibol(fields)
    nibol = nibol_info.get("nibol")
    client_info = _client_funds_asset_for_ic(fields)
    client_ex = float(client_info.get("exclude_from_ic") or 0.0)

    cash_policy = (
        "exclude_cash_sti_and_client_restricted_funds"
        if client_ex > 0
        else "exclude_cash_and_sti"
    )

    if ta is None:
        return {
            "ic_inclusive": None,
            "null_reason": "UNKNOWN",
            "cash_policy": cash_policy,
            "nibol_info": nibol_info,
            "client_funds_info": client_info,
            "components": {
                "total_assets": ta,
                "cash_and_equivalents": cash,
                "short_term_investments": sti,
                "client_funds_excluded": client_ex,
                "non_op_financial": non_op,
                "nibol": nibol,
            },
        }

    # Decision Pass: cash policy inputs required — missing cash ≠ silent zero exclusion
    if cash is None:
        return {
            "ic_inclusive": None,
            "null_reason": "UNKNOWN",
            "cash_policy": cash_policy,
            "nibol_info": nibol_info,
            "client_funds_info": client_info,
            "components": {
                "total_assets": ta,
                "cash_and_equivalents": cash,
                "short_term_investments": sti,
                "client_funds_excluded": client_ex,
                "non_op_financial": non_op,
                "nibol": nibol,
            },
            "sti_missing_treated_as_zero": sti is None,
            "cash_missing_treated_as_zero": False,
            "cash_missing_blocks_ic": True,
        }

    cash_ex = cash
    sti_ex = sti if sti is not None else 0.0
    non_op_ex = non_op if non_op is not None else 0.0
    nibol_ex = nibol if nibol is not None else 0.0

    ic = ta - cash_ex - sti_ex - client_ex - non_op_ex - nibol_ex
    return {
        "ic_inclusive": ic,
        "null_reason": None,
        "cash_policy": cash_policy,
        "nibol_info": nibol_info,
        "client_funds_info": client_info,
        "components": {
            "total_assets": ta,
            "cash_and_equivalents": cash,
            "cash_excluded": cash_ex,
            "short_term_investments": sti,
            "sti_excluded": sti_ex,
            "client_funds_asset": client_info.get("client_funds_asset"),
            "client_funds_excluded": client_ex,
            "client_funds_source": client_info.get("client_funds_source"),
            "non_op_financial": non_op,
            "non_op_excluded": non_op_ex,
            "nibol": nibol,
            "nibol_excluded": nibol_ex,
            "goodwill_included": _num(fields, "goodwill"),
            "intangibles_included": _num(fields, "intangibles"),
        },
        "sti_missing_treated_as_zero": sti is None,
        "cash_missing_treated_as_zero": False,
        "client_funds_incomplete": bool(nibol_info.get("client_funds_incomplete")),
    }


def compute_ic_tangible(ic_inclusive: float | None, fields: dict[str, Any]) -> dict[str, Any]:
    """IC_ex = IC_inclusive − goodwill − intangibles (null→0). Companion only."""
    if ic_inclusive is None:
        return {"ic_tangible": None, "null_reason": "UNKNOWN"}
    gw = _num(fields, "goodwill") or 0.0
    intang = _num(fields, "intangibles") or 0.0
    return {
        "ic_tangible": ic_inclusive - gw - intang,
        "null_reason": None,
        "goodwill_subtracted": gw,
        "intangibles_subtracted": intang,
        "note": "tangible companion ≠ M&A success messaging",
    }


def average_ic(
    ic_begin: float | None,
    ic_end: float | None,
) -> dict[str, Any]:
    """Prefer (begin+end)/2; else begin/end with label."""
    if ic_begin is not None and ic_end is not None:
        return {
            "average_ic": (ic_begin + ic_end) / 2.0,
            "method": "begin_end_average",
        }
    if ic_end is not None:
        return {"average_ic": ic_end, "method": "end_only"}
    if ic_begin is not None:
        return {"average_ic": ic_begin, "method": "begin_only"}
    return {"average_ic": None, "method": "unavailable"}


def financing_check(fields: dict[str, Any], ic_inclusive: float | None) -> dict[str, Any]:
    """Secondary: equity + debt + lease liab − cash − STI ≈ IC. Material gap → flag."""
    if ic_inclusive is None:
        return {"gap": None, "flag": None, "approx": None}
    equity = _num(fields, "equity_parent")
    debt = _num(fields, "total_debt")
    if debt is None:
        std = _num(fields, "short_term_debt") or 0.0
        ltd = _num(fields, "long_term_debt") or 0.0
        cpltd = _num(fields, "current_portion_ltd") or 0.0
        debt = std + ltd + cpltd if (std or ltd or cpltd) else None
    lease_c = _num(fields, "lease_liability_current") or 0.0
    lease_nc = _num(fields, "lease_liability_noncurrent") or 0.0
    lease = lease_c + lease_nc
    cash = _num(fields, "cash_and_equivalents") or 0.0
    sti = _num(fields, "short_term_investments") or 0.0
    if equity is None or debt is None:
        return {
            "gap": None,
            "flag": "INCOMPLETE",
            "approx": None,
            "note": "Financing-side inputs incomplete — no force-fit",
        }
    approx = equity + debt + lease - cash - sti
    gap = approx - ic_inclusive
    # Material unexplained: relative gap > 25% of |IC| — escalate honesty, not a ROIC gate
    flag = None
    if ic_inclusive != 0 and abs(gap) / abs(ic_inclusive) > 0.25:
        flag = "SOURCE_CONFLICT"
    return {
        "gap": gap,
        "flag": flag,
        "approx": approx,
        "components": {
            "equity_parent": equity,
            "total_debt": debt,
            "lease_liabilities": lease,
            "cash": cash,
            "sti": sti,
        },
    }


def roic_ratio(nopat: float | None, avg_ic: float | None) -> dict[str, Any]:
    if nopat is None or avg_ic is None:
        return {"value": None, "null_reason": "UNKNOWN"}
    if avg_ic == 0:
        return {"value": None, "null_reason": "BASE_ZERO"}
    return {"value": nopat / avg_ic, "null_reason": None}


def _period_capital_row(
    p: dict[str, Any],
    tax_info: dict[str, Any],
) -> dict[str, Any]:
    f = p.get("fields") or {}
    oi = _num(f, "operating_income")
    nopat_info = compute_nopat(
        oi, tax_info.get("tax_rate"), tax_rate_source=tax_info.get("tax_rate_source")
    )
    ic_inc = compute_ic_inclusive(f)
    ic_tang = compute_ic_tangible(ic_inc.get("ic_inclusive"), f)
    gw = _num(f, "goodwill")
    intang = _num(f, "intangibles")
    fin = financing_check(f, ic_inc.get("ic_inclusive"))
    capex = _num(f, "capex")
    da = _num(f, "depreciation_amortization")
    acq = _num(f, "business_acquisitions_cash")
    div = _num(f, "dividends_paid")
    buyback = _num(f, "share_repurchases")
    inv = _num(f, "inventory")
    recv = _num(f, "receivables")
    ap = _num(f, "accounts_payable")
    # CapEx/D&A descriptive (not a score)
    capex_da = None
    capex_da_null = None
    if capex is not None and da is not None and da != 0:
        capex_da = abs(capex) / abs(da)
    elif capex is None or da is None:
        capex_da_null = "UNKNOWN"

    return {
        "period_key": p.get("period_key"),
        "version_id": p.get("version_id"),
        "period_type": p.get("period_type"),
        "derived": bool(
            p.get("derived") or (p.get("notes") and "DERIVED" in str(p.get("notes")))
        ),
        "operating_income": oi,
        "nopat": nopat_info.get("nopat"),
        "nopat_null": nopat_info.get("null_reason"),
        "tax_rate": nopat_info.get("tax_rate"),
        "tax_rate_source": nopat_info.get("tax_rate_source"),
        "ic_inclusive": ic_inc.get("ic_inclusive"),
        "ic_inclusive_null": ic_inc.get("null_reason"),
        "ic_tangible": ic_tang.get("ic_tangible"),
        "ic_tangible_null": ic_tang.get("null_reason"),
        "nibol_incomplete": (ic_inc.get("nibol_info") or {}).get("nibol_incomplete", True),
        "client_funds_incomplete": bool(
            (ic_inc.get("nibol_info") or {}).get("client_funds_incomplete")
            or ic_inc.get("client_funds_incomplete")
        ),
        "cash_policy": ic_inc.get("cash_policy"),
        "nibol": (ic_inc.get("nibol_info") or {}).get("nibol"),
        "goodwill": gw,
        "intangibles": intang,
        "has_gw_or_intangibles": bool((gw or 0) > 0 or (intang or 0) > 0),
        "financing_check": fin,
        "capex": capex,
        "depreciation_amortization": da,
        "capex_to_da": capex_da,
        "capex_to_da_null": capex_da_null,
        "business_acquisitions_cash": acq,
        "dividends_paid": div,
        "share_repurchases": buyback,
        "inventory": inv,
        "receivables": recv,
        "accounts_payable": ap,
        "deferred_revenue_current": _num(f, "deferred_revenue_current"),
        "deferred_revenue_noncurrent": _num(f, "deferred_revenue_noncurrent"),
        "ic_components": ic_inc.get("components"),
    }


def _classify_incremental(
    delta_nopat: float | None,
    delta_ic: float | None,
    *,
    window_id: str,
    honesty_flags: list[str] | None = None,
    cause_tag: str | None = None,
    semantic_distortion: bool = False,
    ic_base: float | None = None,
) -> IncrementalROICWindow:
    """Meaning classes; ΔIC≈0 → not_meaningful. No numeric ROIIC thresholds.

    Near-zero uses both ΔNOPAT-relative scale and optional IC-base scale so
    capital-light / tiny-ΔIC pathologies are not misread as excellent ROIIC.
    """
    flags = list(honesty_flags or [])
    if delta_nopat is None or delta_ic is None:
        return IncrementalROICWindow(
            window_id=window_id,
            delta_nopat=delta_nopat,
            delta_ic=delta_ic,
            incremental_roic=None,
            meaning_class="unknown",
            cause_tag=cause_tag or "missing_components",
            honesty_flags=flags,
            null_reason="UNKNOWN",
        )
    # Near-zero ΔIC guard (vs Δ components AND vs capital base when provided)
    scale = max(abs(delta_ic), abs(delta_nopat), 1.0)
    near_zero = abs(delta_ic) / scale < _DELTA_IC_NEAR_ZERO_REL or abs(delta_ic) == 0
    if (
        not near_zero
        and ic_base is not None
        and abs(ic_base) > 0
        and abs(delta_ic) / abs(ic_base) < _DELTA_IC_NEAR_ZERO_REL
    ):
        near_zero = True
        flags.append("delta_ic_tiny_vs_ic_base")
    if near_zero:
        return IncrementalROICWindow(
            window_id=window_id,
            delta_nopat=delta_nopat,
            delta_ic=delta_ic,
            incremental_roic=None,
            meaning_class="not_meaningful",
            cause_tag=cause_tag or "delta_ic_near_zero",
            honesty_flags=flags + ["delta_ic_near_zero"],
            null_reason="BASE_ZERO",
        )
    roiic = delta_nopat / delta_ic
    meaning = "structurally_informative"
    if semantic_distortion:
        meaning = "distorted"
        flags.append("semantic_distortion")
    # Impairment-dominated shrink (ΔIC < 0 with large magnitude relative) → honesty
    if delta_ic < 0 and "impairment" in (cause_tag or ""):
        meaning = "distorted"
        flags.append("impairment_dominated_shrink")
    # Capital released (ΔIC < 0) with rising NOPAT — ROIIC sign/optics not a
    # reinvestment-return measure; honesty class (not a hurdle).
    if delta_ic < 0 and delta_nopat > 0:
        flags.append("negative_delta_ic_capital_released")
        if meaning == "structurally_informative":
            meaning = "noisy"
    # Extreme ratio honesty (not a hurdle): |ROIIC| > 5 often one-off / perimeter
    if abs(roiic) > 5.0 and meaning == "structurally_informative":
        meaning = "noisy"
        flags.append("extreme_roiic_honesty_not_a_hurdle")
    return IncrementalROICWindow(
        window_id=window_id,
        delta_nopat=delta_nopat,
        delta_ic=delta_ic,
        incremental_roic=roiic,
        meaning_class=meaning,
        cause_tag=cause_tag,
        honesty_flags=flags,
        null_reason=None,
    )


def _build_incremental_windows(
    fy_rows: list[dict[str, Any]],
    *,
    semantic_distortion: bool = False,
) -> list[IncrementalROICWindow]:
    """1Y YoY + 3Y cumulative primary + 5Y confirmation."""
    windows: list[IncrementalROICWindow] = []
    usable = [
        r
        for r in fy_rows
        if r.get("nopat") is not None and r.get("ic_inclusive") is not None
    ]

    def _window(start: dict, end: dict, wid: str, cause: str) -> IncrementalROICWindow:
        flags = []
        if start.get("derived") or end.get("derived"):
            flags.append("derived_period_in_window")
        if start.get("nibol_incomplete") or end.get("nibol_incomplete"):
            flags.append("nibol_incomplete_in_window")
        # IC base = end inclusive IC (capital-light tiny-ΔIC vs large IC honesty)
        w = _classify_incremental(
            (end["nopat"] - start["nopat"]),
            (end["ic_inclusive"] - start["ic_inclusive"]),
            window_id=wid,
            honesty_flags=flags,
            cause_tag=cause,
            semantic_distortion=semantic_distortion,
            ic_base=end.get("ic_inclusive"),
        )
        w.from_period = start.get("period_key")
        w.to_period = end.get("period_key")
        return w

    if len(usable) >= 2:
        windows.append(
            _window(usable[-2], usable[-1], "yoy_1y", "yoy_reported")
        )
    if len(usable) >= 4:
        # 3Y cumulative: from usable[-4] to usable[-1] spans ~3 years of change
        windows.append(
            _window(usable[-4], usable[-1], "cumulative_3y", "multi_year_3y_primary")
        )
    if len(usable) >= 6:
        windows.append(
            _window(usable[-6], usable[-1], "cumulative_5y", "multi_year_5y_confirm")
        )
    elif len(usable) >= 5:
        windows.append(
            _window(usable[0], usable[-1], "cumulative_5y", "multi_year_5y_available_span")
        )
    return windows


def _wc_metrics(fy_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """WC mechanism notes inputs — never auto-reward negative WC.

    Wave2 A5/A6: missing inventory/receivables ≠ economic zero. Refuse coerced
    WC proxy when any core component is null; set wc_incomplete honesty flag.
    """
    if not fy_rows:
        return {"latest": None, "delta_wc": None, "null_reason": "UNKNOWN", "wc_incomplete": True}

    def _wc(row: dict) -> tuple[float | None, bool, list[str]]:
        inv = row.get("inventory")
        recv = row.get("receivables")
        ap = row.get("accounts_payable")
        missing = [
            k
            for k, v in (
                ("inventory", inv),
                ("receivables", recv),
                ("accounts_payable", ap),
            )
            if v is None
        ]
        if inv is None and recv is None and ap is None:
            return None, True, missing
        # null ≠ 0: any missing core component → incomplete; do not publish coerced proxy
        if missing:
            return None, True, missing
        return float(inv) + float(recv) - float(ap), False, []

    latest = fy_rows[-1]
    prior = fy_rows[-2] if len(fy_rows) >= 2 else None
    wc_l, inc_l, miss_l = _wc(latest)
    wc_p, inc_p, miss_p = _wc(prior) if prior else (None, False, [])
    delta = None
    if wc_l is not None and wc_p is not None:
        delta = wc_l - wc_p
    incomplete = bool(inc_l or inc_p)
    return {
        "latest_wc_proxy": wc_l,
        "prior_wc_proxy": wc_p,
        "delta_wc": delta,
        "wc_incomplete": incomplete,
        "wc_missing_components": miss_l,
        "deferred_revenue_current": latest.get("deferred_revenue_current"),
        "note": (
            "WC mechanism-first; never auto-reward negative WC = good; "
            "null inventory/receivables/AP ≠ 0 (wc_incomplete when any missing)"
        ),
        "null_reason": None if wc_l is not None else ("INCOMPLETE" if incomplete else "UNKNOWN"),
    }


def _reinvestment_composition(fy_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Composition view — no aggregate reinvestment-rate score required."""
    if not fy_rows:
        return {"null_reason": "UNKNOWN"}
    latest = fy_rows[-1]
    return {
        "organic_capex": latest.get("capex"),
        "maint_growth_split": "UNKNOWN",  # no forced maint CapEx
        "maint_capex_status": "UNKNOWN",
        "wc_delta": None,  # filled by caller from wc metrics
        "business_acquisitions_cash": latest.get("business_acquisitions_cash"),
        "dividends_paid": latest.get("dividends_paid"),
        "share_repurchases": latest.get("share_repurchases"),
        "note": (
            "Composition first; distributions separate from reinvestment; "
            "maint/growth CapEx UNKNOWN unless disclosed"
        ),
        "no_aggregate_rate_required": True,
        "no_forced_maint_capex": True,
    }


def compute_stage6_metrics(
    periods: list[dict[str, Any]],
    *,
    extend_full_cycle: bool = False,
    prefer_fy: int = 5,
    prefer_q: int = 8,
    dual_view_mandatory: bool = False,
    semantic_distortion: bool = False,
    semantic_texts: list[str] | None = None,
    explicit_comparability_breaks: list[dict[str, Any]] | None = None,
) -> CalcResult:
    """
    Build descriptive ROIC / IC / incremental / reinvestment exhibits.
    No numeric ROIC/ROIIC/WACC gates. Incremental ≠ Stage 5 IOM.
    """
    fy_sel, q_sel, flags = _select_periods(
        periods,
        prefer_fy=prefer_fy,
        prefer_q=prefer_q,
        extend_full_cycle=extend_full_cycle,
    )
    null_reasons: dict[str, str] = {}

    # Tax rate from all selected FY fields
    fy_fields = [p.get("fields") or {} for p in fy_sel]
    tax_info = resolve_tax_rate(fy_fields)

    fy_rows = [_period_capital_row(p, tax_info) for p in fy_sel]
    q_rows = [_period_capital_row(p, tax_info) for p in q_sel]

    for row in fy_rows:
        pk = row.get("period_key") or "?"
        if row.get("nopat") is None:
            null_reasons[f"nopat_{pk}"] = row.get("nopat_null") or "UNKNOWN"
        if row.get("ic_inclusive") is None:
            null_reasons[f"ic_{pk}"] = row.get("ic_inclusive_null") or "UNKNOWN"

    latest = fy_rows[-1] if fy_rows else None
    prior = fy_rows[-2] if len(fy_rows) >= 2 else None

    # Average IC for latest year
    dual: dict[str, Any] = {}
    if latest:
        avg_inc = average_ic(
            prior.get("ic_inclusive") if prior else None,
            latest.get("ic_inclusive"),
        )
        avg_tang = average_ic(
            prior.get("ic_tangible") if prior else None,
            latest.get("ic_tangible"),
        )
        roic_inc = roic_ratio(latest.get("nopat"), avg_inc.get("average_ic"))
        roic_tang = roic_ratio(latest.get("nopat"), avg_tang.get("average_ic"))
        emit_dual = bool(
            dual_view_mandatory
            or latest.get("has_gw_or_intangibles")
        )
        dual = {
            "period_key": latest.get("period_key"),
            "nopat": latest.get("nopat"),
            "nopat_null": latest.get("nopat_null"),
            "tax_rate": latest.get("tax_rate"),
            "tax_rate_source": latest.get("tax_rate_source"),
            "ic_inclusive": latest.get("ic_inclusive"),
            "ic_tangible": latest.get("ic_tangible"),
            "average_ic_inclusive": avg_inc.get("average_ic"),
            "average_ic_tangible": avg_tang.get("average_ic"),
            "average_ic_method": avg_inc.get("method"),
            "roic_inclusive": roic_inc.get("value"),
            "roic_inclusive_null": roic_inc.get("null_reason"),
            "roic_tangible": roic_tang.get("value"),
            "roic_tangible_null": roic_tang.get("null_reason"),
            "dual_view_emitted": emit_dual,
            "dual_view_mandatory": dual_view_mandatory,
            "tangible_ne_ma_success": True,
            "nibol_incomplete": latest.get("nibol_incomplete"),
            "client_funds_incomplete": latest.get("client_funds_incomplete"),
            "financing_check_gap": (latest.get("financing_check") or {}).get("gap"),
            "financing_check_flag": (latest.get("financing_check") or {}).get("flag"),
            "goodwill": latest.get("goodwill"),
            "intangibles": latest.get("intangibles"),
            "definition_labels": {
                "numerator": "NOPAT = operating_income × (1 − t_norm)",
                "tax_rate_source": latest.get("tax_rate_source"),
                "denominator_primary": "IC_inclusive = TA − cash − STI − clear non-op − NIBOL",
                "denominator_companion": "IC_tangible = IC_inclusive − GW − intangibles",
                "cash_policy": latest.get("cash_policy") or "exclude_cash_and_sti",
                "average_ic_method": avg_inc.get("method"),
                "primary_role": "acquisition_inclusive",
                "companion_role": "tangible_leaning",
            },
        }
        if roic_inc.get("value") is None:
            null_reasons["roic_inclusive"] = roic_inc.get("null_reason") or "UNKNOWN"
    else:
        null_reasons["dual_roic"] = "UNKNOWN"

    iom_windows = _build_incremental_windows(
        fy_rows, semantic_distortion=semantic_distortion
    )
    wc = _wc_metrics(fy_rows)
    reinv = _reinvestment_composition(fy_rows)
    reinv["wc_delta"] = wc.get("delta_wc")

    # IC bridge: period-to-period IC change contributors (descriptive)
    ic_bridge = None
    if latest and prior:
        ic_bridge = {
            "from": prior.get("period_key"),
            "to": latest.get("period_key"),
            "delta_ic_inclusive": (
                None
                if latest.get("ic_inclusive") is None or prior.get("ic_inclusive") is None
                else latest["ic_inclusive"] - prior["ic_inclusive"]
            ),
            "capex": latest.get("capex"),
            "acquisitions": latest.get("business_acquisitions_cash"),
            "delta_wc": wc.get("delta_wc"),
            "note": "Descriptive bridge; not a full roll-forward engine",
        }

    metrics: dict[str, Any] = {
        "history_flags": flags,
        "n_fy": len(fy_rows),
        "n_q": len(q_rows),
        "periods_fy_keys": [r.get("period_key") for r in fy_rows],
        "periods_q_keys": [r.get("period_key") for r in q_rows],
        "capital_fy_series": fy_rows,
        "capital_q_series": q_rows,
        "tax_info": tax_info,
        "dual_roic": dual,
        "incremental_roic_windows": [w.to_dict() for w in iom_windows],
        "reinvestment_composition": reinv,
        "wc_metrics": wc,
        "ic_bridge": ic_bridge,
        "latest_capital": latest,
        "prior_capital": prior,
        # Explicit non-goals / boundary markers
        "no_numeric_roic_thresholds": True,
        "no_wacc_hurdle": True,
        "no_forced_maint_capex": True,
        "incremental_roic_ne_iom": True,
        "iom_is_stage5_only": True,
    }

    if not fy_rows:
        null_reasons["capital_fy_series"] = "UNKNOWN"

    # SD-W4-C1: ROIC/ROIIC windows crossing breaks must know series (as-reported)
    from ..comparability import detect_comparability_breaks, window_crosses_break

    breaks = detect_comparability_breaks(
        periods,
        semantic_texts=semantic_texts,
        explicit_breaks=explicit_comparability_breaks,
    )
    metrics["comparability_breaks"] = breaks
    metrics["roic_series_primary"] = "as_reported"
    wins = metrics.get("incremental_roic_windows") or []
    annotated = []
    for w in wins:
        if not isinstance(w, dict):
            annotated.append(w)
            continue
        ww = dict(w)
        ww.setdefault("series", "as_reported")
        crossed = window_crosses_break(
            ww.get("from_period"),
            ww.get("to_period"),
            breaks,
        )
        if crossed:
            ww["comparability_break"] = True
            ww["honesty_flag"] = "COMPARABILITY_BREAK"
            ww["comparability_reason"] = crossed.get("reason")
            ww["series_note"] = (
                "as_reported window crosses COMPARABILITY_BREAK — "
                "not clean multi-year ROIC; no model-created recast"
            )
        annotated.append(ww)
    metrics["incremental_roic_windows"] = annotated

    return CalcResult(metrics=metrics, null_reasons=null_reasons)
