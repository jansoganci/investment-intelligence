"""Deterministic ratios/trends; null + reason if dishonest / not computable."""
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


def _add(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    return (a or 0.0) + (b or 0.0)


def _flag_true(fields: dict, key: str) -> bool:
    """True only when Normalized explicitly sets the flag to True."""
    return fields.get(key) is True


def compute_stage2_metrics(
    current: dict[str, Any],
    prior: dict[str, Any] | None = None,
    prior_is: dict[str, Any] | None = None,
    prior_yoy: dict[str, Any] | None = None,
) -> CalcResult:
    """
    Deterministic Stage 2 metrics from Normalized CURRENT fields.
    High debt ratio alone never implies a process block — this module only computes.

    Wave 4 / SD-W4-C3: sequential prior-period growth is exposed as
    ``revenue_growth_qoq`` with explicit basis; ``revenue_growth`` remains an
    alias of that sequential figure (basis labeled — never silently redefined
    as YoY). ``revenue_growth_yoy`` is a companion when a valid prior-year
    period is supplied. Missing YoY does not create a Stage 2 gate.
    """
    f = current.get("fields") or {}
    metrics: dict[str, Any] = {}
    null_reasons: dict[str, str] = {}

    cash = _num(f, "cash_and_equivalents")
    sti = _num(f, "short_term_investments")
    cash_near = _add(cash, sti)
    metrics["cash"] = cash
    metrics["cash_plus_st_investments"] = cash_near
    if cash is None:
        null_reasons["cash"] = "cash_and_equivalents missing"

    restricted = _num(f, "restricted_cash_amount")
    metrics["restricted_cash_amount"] = restricted
    metrics["restricted_cash_flag"] = f.get("restricted_cash_flag")
    if cash is not None and restricted is not None:
        metrics["unrestricted_cash_proxy"] = cash - restricted
    else:
        metrics["unrestricted_cash_proxy"] = None
        if cash is None or restricted is None:
            null_reasons["unrestricted_cash_proxy"] = (
                "need cash_and_equivalents and restricted_cash_amount"
            )

    std = _num(f, "short_term_debt")
    ltd = _num(f, "long_term_debt")
    cpltd = _num(f, "current_portion_ltd")
    secured = _num(f, "secured_debt")
    total_debt_field = _num(f, "total_debt")
    # When True, short_term_debt already embeds current_portion_ltd — omit cpltd
    # from gross_debt and near_term to avoid double-count. Missing/False → sum
    # separate BS components (no max).
    std_includes_cpltd = _flag_true(f, "short_term_debt_includes_current_ltd")
    metrics["short_term_debt_includes_current_ltd"] = (
        True if std_includes_cpltd else (False if f.get("short_term_debt_includes_current_ltd") is False else None)
    )
    metrics["secured_debt"] = secured
    metrics["short_term_debt"] = std
    metrics["long_term_debt"] = ltd
    metrics["current_portion_ltd"] = cpltd

    # -------------------------------------------------------------------------
    # Gross interest-bearing debt (prefer components over total_debt field)
    # Wave2 A1: include secured/securitization; do not silently publish ST-only
    # as complete when LTD null with incompleteness evidence.
    #
    # If short_term_debt_includes_current_ltd is True:
    #   gross = ST + LTD(+secured); do NOT add cpltd
    # If flag False/missing:
    #   gross = ST + CPLTD + LTD + secured (each if present; sum, no max)
    # -------------------------------------------------------------------------
    secured_add = secured or 0.0

    if std_includes_cpltd:
        if std is not None or ltd is not None or secured is not None:
            metrics["gross_debt"] = (std or 0.0) + (ltd or 0.0) + secured_add
        elif total_debt_field is not None:
            metrics["gross_debt"] = total_debt_field
            null_reasons["gross_debt_components"] = "used total_debt field; components missing"
        else:
            metrics["gross_debt"] = None
            null_reasons["gross_debt"] = "short_term_debt/long_term_debt/secured_debt/total_debt missing"
    else:
        if std is not None or ltd is not None or cpltd is not None or secured is not None:
            metrics["gross_debt"] = (std or 0.0) + (cpltd or 0.0) + (ltd or 0.0) + secured_add
        elif total_debt_field is not None:
            metrics["gross_debt"] = total_debt_field
            null_reasons["gross_debt_components"] = "used total_debt field; components missing"
        else:
            metrics["gross_debt"] = None
            null_reasons["gross_debt"] = "short_term_debt/long_term_debt/secured_debt/total_debt missing"

    # Honesty: null LTD must not coerce to a *complete* gross_debt when other
    # interest-bearing components or incompleteness evidence exist (Wave2 A1).
    # Evidence: secured/securitization present, or total_debt field present, or
    # maturity buckets present while LTD null.
    incompleteness_evidence = (
        secured is not None
        or total_debt_field is not None
        or f.get("debt_maturity_buckets") is not None
    )
    other_debt_present = std is not None or cpltd is not None or secured is not None
    gross_debt_incomplete = bool(
        metrics.get("gross_debt") is not None
        and ltd is None
        and other_debt_present
        and incompleteness_evidence
    )
    metrics["gross_debt_incomplete"] = gross_debt_incomplete
    # OpCo vs Financial Services / captive split: cannot form honestly without
    # structured segment debt — do not invent dual numbers (Wave2 A1).
    opco_fs_split_unavailable = bool(
        gross_debt_incomplete and secured is not None
    )
    metrics["opco_fs_split_unavailable"] = opco_fs_split_unavailable
    metrics["debt_view_label"] = (
        "consolidated_interest_bearing_incomplete"
        if gross_debt_incomplete
        else ("consolidated_interest_bearing" if metrics.get("gross_debt") is not None else None)
    )
    if gross_debt_incomplete:
        null_reasons["gross_debt_incomplete"] = (
            "long_term_debt null while other interest-bearing components / "
            "securitization / total_debt / maturity evidence present — "
            "do not treat component sum as complete gross debt; "
            "OpCo vs FS dual view unavailable without structured segment tags "
            "(REVIEW / TOO_HARD rather than invent)"
        )
        # Keep component sum for exhibit transparency but mark not-complete.
        metrics["gross_debt_components_sum"] = metrics.get("gross_debt")

    lease_c = _num(f, "lease_liability_current")
    lease_nc = _num(f, "lease_liability_noncurrent")
    lease_total = _add(lease_c, lease_nc)
    metrics["lease_liability_total"] = lease_total
    if lease_total is None:
        null_reasons["lease_liability_total"] = "lease liabilities not disclosed in Normalized"

    if metrics["gross_debt"] is not None or lease_total is not None:
        metrics["lease_adjusted_contractual_debt"] = (metrics["gross_debt"] or 0.0) + (
            lease_total or 0.0
        )
    else:
        metrics["lease_adjusted_contractual_debt"] = None
        null_reasons["lease_adjusted_contractual_debt"] = "gross debt and leases both missing"

    # Net debt / net cash (surplus cash)
    if metrics["gross_debt"] is not None and cash_near is not None:
        net = metrics["gross_debt"] - cash_near
        metrics["net_debt"] = net
        metrics["net_cash"] = -net if net < 0 else None
    else:
        metrics["net_debt"] = None
        metrics["net_cash"] = None
        null_reasons["net_debt"] = "need gross_debt and cash(+STI)"

    # -------------------------------------------------------------------------
    # Near-term contractual obligations (Stage 2 proxy)
    #
    # Default (flag missing/False): sum all present among
    #   short_term_debt + current_portion_ltd + lease_liability_current
    #   (NO max — separate BS lines are additive, e.g. KO Loans/notes vs CPLTD).
    # If short_term_debt_includes_current_ltd is True:
    #   near_term = short_term_debt + lease_liability_current
    #   (ignore current_portion_ltd even if present — already inside ST debt).
    # Null + reason if all three components missing (or both ST+lease when flag True).
    # -------------------------------------------------------------------------
    near_term = None
    if std_includes_cpltd:
        nt_parts: list[float] = []
        if std is not None:
            nt_parts.append(std)
        if lease_c is not None:
            nt_parts.append(lease_c)
        if nt_parts:
            near_term = sum(nt_parts)
    else:
        nt_parts = []
        for val in (std, cpltd, lease_c):
            if val is not None:
                nt_parts.append(val)
        if nt_parts:
            near_term = sum(nt_parts)
    metrics["near_term_contractual_obligations"] = near_term
    if near_term is None:
        null_reasons["near_term_contractual_obligations"] = (
            "missing ST debt / current LTD / current leases"
        )

    if cash_near is not None and near_term is not None:
        metrics["cash_vs_near_term_obligations"] = cash_near - near_term
    else:
        metrics["cash_vs_near_term_obligations"] = None
        null_reasons["cash_vs_near_term_obligations"] = "need cash(+STI) and near-term obligations"

    tca = _num(f, "total_current_assets")
    tcl = _num(f, "total_current_liabilities")
    inv = _num(f, "inventory")
    if tca is not None and tcl is not None and tcl != 0:
        metrics["current_ratio"] = tca / tcl
    else:
        metrics["current_ratio"] = None
        null_reasons["current_ratio"] = "need total_current_assets and total_current_liabilities≠0"

    if tca is not None and inv is not None and tcl is not None and tcl != 0:
        metrics["quick_ratio"] = (tca - inv) / tcl
    else:
        metrics["quick_ratio"] = None
        null_reasons["quick_ratio"] = "need current assets, inventory, current liabilities"

    equity = _num(f, "equity_parent")
    assets = _num(f, "total_assets")
    debt_for_ratio = metrics.get("lease_adjusted_contractual_debt") or metrics.get("gross_debt")

    if debt_for_ratio is not None and equity is not None and equity != 0:
        metrics["debt_to_equity"] = debt_for_ratio / equity
    else:
        metrics["debt_to_equity"] = None
        null_reasons["debt_to_equity"] = "need debt and equity_parent≠0"

    if debt_for_ratio is not None and assets is not None and assets != 0:
        metrics["debt_to_assets"] = debt_for_ratio / assets
    else:
        metrics["debt_to_assets"] = None
        null_reasons["debt_to_assets"] = "need debt and total_assets≠0"

    gw = _num(f, "goodwill")
    intang = _num(f, "intangibles")
    soft = _add(gw, intang)
    metrics["goodwill_plus_intangibles"] = soft
    if soft is not None and equity is not None and equity != 0:
        metrics["gw_intangibles_share_of_equity"] = soft / equity
    else:
        metrics["gw_intangibles_share_of_equity"] = None
        null_reasons["gw_intangibles_share_of_equity"] = "need goodwill/intangibles and equity"

    if soft is not None and assets is not None and assets != 0:
        metrics["gw_intangibles_share_of_assets"] = soft / assets
    else:
        metrics["gw_intangibles_share_of_assets"] = None

    metrics["undrawn_facilities"] = f.get("undrawn_revolver_or_liquidity_facilities")
    if metrics["undrawn_facilities"] is None:
        null_reasons["undrawn_facilities"] = "often note-only; not in Normalized"

    buckets = f.get("debt_maturity_buckets")
    metrics["debt_maturity_buckets"] = buckets
    if not buckets:
        null_reasons["debt_maturity_buckets"] = "maturity buckets missing (often note/manual)"
    else:
        # aggregate if list/dict of year→amount
        try:
            if isinstance(buckets, dict):
                metrics["maturity_aggregation"] = {k: float(v) for k, v in buckets.items() if v is not None}
            elif isinstance(buckets, list):
                agg = {}
                for item in buckets:
                    if isinstance(item, dict):
                        agg[str(item.get("bucket") or item.get("year"))] = float(item.get("amount"))
                metrics["maturity_aggregation"] = agg
            else:
                metrics["maturity_aggregation"] = None
                null_reasons["maturity_aggregation"] = "unrecognized debt_maturity_buckets shape"
        except (TypeError, ValueError):
            metrics["maturity_aggregation"] = None
            null_reasons["maturity_aggregation"] = "could not parse maturity buckets"

    # Multi-period WC trends
    recv = _num(f, "receivables")
    metrics["receivables"] = recv
    metrics["inventory"] = inv
    if prior:
        pf = prior.get("fields") or {}
        prev_recv = _num(pf, "receivables")
        prev_inv = _num(pf, "inventory")
        if recv is not None and prev_recv is not None:
            metrics["delta_receivables"] = recv - prev_recv
        else:
            metrics["delta_receivables"] = None
            null_reasons["delta_receivables"] = "need multi-period receivables"
        if inv is not None and prev_inv is not None:
            metrics["delta_inventory"] = inv - prev_inv
        else:
            metrics["delta_inventory"] = None
            null_reasons["delta_inventory"] = "need multi-period inventory"

        # vs sales if revenue present
        # SD-W4-C3: sequential prior-period growth (QoQ when current/prior are
        # consecutive quarters; else sequential vs immediate prior period).
        rev = _num(f, "revenue")
        prev_rev = _num(pf, "revenue")
        if prior_is:
            prev_rev = _num(prior_is.get("fields") or pf, "revenue") or prev_rev
        if rev is not None and prev_rev is not None and prev_rev != 0:
            qoq = (rev - prev_rev) / abs(prev_rev)
            metrics["revenue_growth_qoq"] = qoq
            # Alias kept for backward compat — basis MUST be explicit (not YoY).
            metrics["revenue_growth"] = qoq
            metrics["revenue_growth_basis"] = "sequential_prior_period"
            metrics["revenue_growth_label"] = (
                "revenue_growth_qoq (sequential vs prior period; not FY YoY)"
            )
            metrics["revenue_growth_from_period"] = prior.get("period_key")
            metrics["revenue_growth_to_period"] = current.get("period_key")
        else:
            metrics["revenue_growth_qoq"] = None
            metrics["revenue_growth"] = None
            metrics["revenue_growth_basis"] = "sequential_prior_period"
            null_reasons["revenue_growth_qoq"] = "need current and prior revenue"
    else:
        metrics["delta_receivables"] = None
        metrics["delta_inventory"] = None
        metrics["revenue_growth_qoq"] = None
        metrics["revenue_growth"] = None
        metrics["revenue_growth_basis"] = "sequential_prior_period"
        null_reasons["wc_trends"] = "single period only — trends not computable"

    # SD-W4-C3 companion: YoY when valid prior-year period supplied (no gate if missing)
    yoy_doc = prior_yoy
    if yoy_doc is not None:
        yf = yoy_doc.get("fields") or {}
        rev_c = _num(f, "revenue")
        rev_y = _num(yf, "revenue")
        if rev_c is not None and rev_y is not None and rev_y != 0:
            metrics["revenue_growth_yoy"] = (rev_c - rev_y) / abs(rev_y)
            metrics["revenue_growth_yoy_basis"] = "same_shape_prior_year_period"
            metrics["revenue_growth_yoy_from_period"] = yoy_doc.get("period_key")
            metrics["revenue_growth_yoy_to_period"] = current.get("period_key")
        else:
            metrics["revenue_growth_yoy"] = None
            null_reasons["revenue_growth_yoy"] = "need current and prior-year revenue"
    else:
        metrics["revenue_growth_yoy"] = None
        # Honesty only — do NOT add Stage 2 process gate from missing YoY (SD-W4-C3)
        null_reasons["revenue_growth_yoy"] = "prior_year_period_not_available"

    return CalcResult(metrics=metrics, null_reasons=null_reasons)
