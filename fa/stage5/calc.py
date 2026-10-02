"""Deterministic Stage 5 margin exhibits — no pass/fail bands, no LLM arithmetic.

Descriptive GM/OP/cost ratios + incremental OM (ΔOP/ΔRev) only.
Numeric GM/OP/IM bands RESEARCH CANDIDATE / NOT LOCKED — never used as gates.
Incremental OM ≠ Stage 6 ROIC / ROIIC.
"""
from __future__ import annotations

from typing import Any

from ..models import CalcResult, IncrementalOMWindow, MarginDecomposition


def _num(fields: dict, key: str) -> float | None:
    v = fields.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def margin_ratio(numerator: float | None, denominator: float | None) -> dict[str, Any]:
    """Descriptive margin ratio. Null when inputs missing or denom==0. Not a hurdle."""
    if numerator is None or denominator is None:
        return {"value": None, "null_reason": "UNKNOWN"}
    if denominator == 0:
        return {"value": None, "null_reason": "BASE_ZERO"}
    return {"value": numerator / denominator, "null_reason": None}


def _select_periods(
    periods: list[dict[str, Any]],
    *,
    prefer_fy: int = 5,
    prefer_q: int = 8,
    extend_full_cycle: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Default ~5 FY + ~8 contiguous economic Q; extend flag for cyclicals."""
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
        "incomplete_cycle_flag": extend_full_cycle and len(fy) < 5,
        "quarter_policy": contiguous_meta.get("policy"),
        "quarters_contiguous": contiguous_meta.get("contiguous"),
    }
    return fy_sel, q_sel, flags


def _period_margins(p: dict[str, Any]) -> dict[str, Any]:
    f = p.get("fields") or {}
    rev = _num(f, "revenue")
    gp = _num(f, "gross_profit")
    cor = _num(f, "cost_of_revenue")
    oi = _num(f, "operating_income")
    sbc = _num(f, "sbc_expense")
    da = _num(f, "depreciation_amortization")

    # Prefer disclosed gross_profit; else derive from rev - cor when both present
    if gp is None and rev is not None and cor is not None:
        gp = rev - cor
        gp_source = "derived_rev_minus_cor"
    else:
        gp_source = "disclosed" if gp is not None else "missing"

    gm = margin_ratio(gp, rev)
    op = margin_ratio(oi, rev)
    # Opex intensity proxy: (rev - oi - cor) / rev when inputs exist — definition-labeled
    opex_intensity: dict[str, Any]
    if rev is not None and oi is not None and cor is not None and rev != 0:
        # remaining after COGS and OP ≈ operating expenses (ex-COGS) approximation
        opex_approx = rev - cor - oi
        opex_intensity = {
            "value": opex_approx / rev,
            "null_reason": None,
            "definition": "approx_(rev_minus_cor_minus_oi)_over_rev",
        }
    elif rev is not None and oi is not None and rev != 0:
        opex_intensity = {
            "value": 1.0 - (oi / rev),
            "null_reason": None,
            "definition": "approx_1_minus_op_margin_when_cor_absent",
        }
    else:
        opex_intensity = {
            "value": None,
            "null_reason": "UNKNOWN",
            "definition": "unavailable",
        }

    # SBC-aware OP (descriptive SHOULD) — OP after adding back SBC only when both present
    sbc_aware: dict[str, Any]
    if oi is not None and sbc is not None and rev is not None and rev != 0:
        sbc_aware = {
            "op_plus_sbc": oi + sbc,
            "op_plus_sbc_margin": (oi + sbc) / rev,
            "null_reason": None,
            "note": "descriptive add-back; not a non-GAAP endorsement",
        }
    else:
        sbc_aware = {"op_plus_sbc": None, "op_plus_sbc_margin": None, "null_reason": "UNKNOWN"}

    # Optional disclosed Stage 5 Normalized
    take_rate = _num(f, "take_rate")
    contrib = _num(f, "contribution_margin")
    iom_disc = _num(f, "incremental_operating_margin_disclosed")
    seg = f.get("segment_operating_margin")

    return {
        "period_key": p.get("period_key"),
        "version_id": p.get("version_id"),
        "period_type": p.get("period_type"),
        "derived": bool(p.get("derived") or (p.get("notes") and "DERIVED" in str(p.get("notes")))),
        "revenue": rev,
        "gross_profit": gp,
        "gross_profit_source": gp_source,
        "cost_of_revenue": cor,
        "operating_income": oi,
        "gross_margin": gm.get("value"),
        "gross_margin_null": gm.get("null_reason"),
        "operating_margin": op.get("value"),
        "operating_margin_null": op.get("null_reason"),
        "opex_intensity": opex_intensity.get("value"),
        "opex_intensity_definition": opex_intensity.get("definition"),
        "opex_intensity_null": opex_intensity.get("null_reason"),
        "sbc_expense": sbc,
        "sbc_aware": sbc_aware,
        "depreciation_amortization": da,
        "take_rate": take_rate,
        "contribution_margin": contrib,
        "incremental_operating_margin_disclosed": iom_disc,
        "segment_operating_margin": seg,
    }


def incremental_om(
    delta_op: float | None,
    delta_rev: float | None,
    *,
    window_id: str,
    from_period: str | None = None,
    to_period: str | None = None,
    honesty_flags: list[str] | None = None,
    cause_tag: str | None = None,
    posture_class: str = "reported",
) -> IncrementalOMWindow:
    """Descriptive ΔOP/ΔRev. No numeric hurdle. ≠ ROIIC."""
    flags = list(honesty_flags or [])
    if delta_op is None or delta_rev is None:
        return IncrementalOMWindow(
            window_id=window_id,
            from_period=from_period,
            to_period=to_period,
            delta_op=delta_op,
            delta_rev=delta_rev,
            incremental_om=None,
            posture_class="unknown",
            cause_tag=cause_tag,
            honesty_flags=flags,
            null_reason="UNKNOWN",
            stage6_handoff="Capital-return / ROIIC questions → Stage 6 (not computed here)",
        )
    if delta_rev == 0:
        return IncrementalOMWindow(
            window_id=window_id,
            from_period=from_period,
            to_period=to_period,
            delta_op=delta_op,
            delta_rev=delta_rev,
            incremental_om=None,
            posture_class="distorted" if posture_class == "reported" else posture_class,
            cause_tag=cause_tag or "zero_delta_rev",
            honesty_flags=flags + ["delta_rev_zero"],
            null_reason="BASE_ZERO",
            stage6_handoff="Capital-return / ROIIC questions → Stage 6 (not computed here)",
        )
    iom = delta_op / delta_rev
    # Honesty only: extreme |ΔOP/ΔRev| often one-off / perimeter / base-effect — NOT a numeric hurdle/gate
    if abs(iom) > 1.0 and posture_class == "reported":
        posture_class = "distorted"
        flags = flags + ["extreme_iom_honesty_not_a_hurdle"]
        cause_tag = (cause_tag or "") + "|extreme_delta_ratio_honesty"
    return IncrementalOMWindow(
        window_id=window_id,
        from_period=from_period,
        to_period=to_period,
        delta_op=delta_op,
        delta_rev=delta_rev,
        incremental_om=iom,
        posture_class=posture_class,
        cause_tag=cause_tag,
        honesty_flags=flags,
        null_reason=None,
        stage6_handoff="Capital-return / ROIIC questions → Stage 6 (not computed here)",
    )


def _build_incremental_windows(
    fy_rows: list[dict[str, Any]],
) -> list[IncrementalOMWindow]:
    """YoY latest FY + multi-year when perimeter looks stable enough descriptively."""
    windows: list[IncrementalOMWindow] = []
    usable = [r for r in fy_rows if r.get("revenue") is not None and r.get("operating_income") is not None]
    if len(usable) >= 2:
        prev, curr = usable[-2], usable[-1]
        flags = []
        if curr.get("derived") or prev.get("derived"):
            flags.append("derived_period_in_window")
        windows.append(
            incremental_om(
                (curr["operating_income"] - prev["operating_income"]),
                (curr["revenue"] - prev["revenue"]),
                window_id="yoy_latest_fy",
                from_period=prev.get("period_key"),
                to_period=curr.get("period_key"),
                honesty_flags=flags,
                cause_tag="yoy_reported",
                posture_class="reported",
            )
        )
    if len(usable) >= 4:
        start, end = usable[-4], usable[-1]
        flags = ["multi_year_window"]
        # Mark potentially distorted if OP sign flips or revenue collapses
        posture = "structurally_informative"
        if (start["operating_income"] < 0) != (end["operating_income"] < 0):
            posture = "distorted"
            flags.append("op_sign_flip")
        if start["revenue"] and end["revenue"] and end["revenue"] < 0.5 * start["revenue"]:
            posture = "distorted"
            flags.append("revenue_collapse")
        windows.append(
            incremental_om(
                (end["operating_income"] - start["operating_income"]),
                (end["revenue"] - start["revenue"]),
                window_id="multi_year_fy",
                from_period=start.get("period_key"),
                to_period=end.get("period_key"),
                honesty_flags=flags,
                cause_tag="multi_year_reported",
                posture_class=posture,
            )
        )
    return windows


def _path_consistency(values: list[float | None]) -> str:
    nums = [v for v in values if v is not None]
    if len(nums) < 2:
        return "UNKNOWN"
    ups = sum(1 for i in range(1, len(nums)) if nums[i] > nums[i - 1])
    downs = sum(1 for i in range(1, len(nums)) if nums[i] < nums[i - 1])
    if ups == len(nums) - 1:
        return "all_up"
    if downs == len(nums) - 1:
        return "all_down"
    if ups > downs:
        return "mostly_up"
    if downs > ups:
        return "mostly_down"
    return "mixed"


def compute_stage5_metrics(
    periods: list[dict[str, Any]],
    *,
    extend_full_cycle: bool = False,
    prefer_fy: int = 5,
    prefer_q: int = 8,
) -> CalcResult:
    """
    Build descriptive margin exhibits from Normalized fields.
    No GM/OP/IM band gates. No ROIC.
    """
    fy_sel, q_sel, flags = _select_periods(
        periods,
        prefer_fy=prefer_fy,
        prefer_q=prefer_q,
        extend_full_cycle=extend_full_cycle,
    )
    null_reasons: dict[str, str] = {}

    fy_rows = [_period_margins(p) for p in fy_sel]
    q_rows = [_period_margins(p) for p in q_sel]

    for row in fy_rows + q_rows:
        pk = row.get("period_key") or "?"
        if row.get("gross_margin") is None:
            null_reasons[f"gm_{pk}"] = row.get("gross_margin_null") or "UNKNOWN"
        if row.get("operating_margin") is None:
            null_reasons[f"op_{pk}"] = row.get("operating_margin_null") or "UNKNOWN"

    gm_fy = [r.get("gross_margin") for r in fy_rows]
    op_fy = [r.get("operating_margin") for r in fy_rows]
    latest = fy_rows[-1] if fy_rows else None
    prior = fy_rows[-2] if len(fy_rows) >= 2 else None

    delta_gm = None
    delta_op = None
    if latest and prior:
        if latest.get("gross_margin") is not None and prior.get("gross_margin") is not None:
            delta_gm = latest["gross_margin"] - prior["gross_margin"]
        if latest.get("operating_margin") is not None and prior.get("operating_margin") is not None:
            delta_op = latest["operating_margin"] - prior["operating_margin"]

    iom_windows = _build_incremental_windows(fy_rows)

    # Lightweight decomposition skeleton from numeric deltas (semantic fills drivers)
    decomps: list[dict[str, Any]] = []
    if latest:
        md = MarginDecomposition(
            period_key=latest.get("period_key") or "",
            reported_gross_margin=latest.get("gross_margin"),
            reported_operating_margin=latest.get("operating_margin"),
            delta_vs_prior_gm=delta_gm,
            delta_vs_prior_op=delta_op,
            components=[],
            unattributed_or_unknown=(
                "Driver attribution requires MD&A/Notes — left UNKNOWN until semantic"
            ),
            ses_or_intentional_thin_margin="unknown",
        )
        decomps.append(md.to_dict())

    # Optional disclosed fields presence
    optional_disclosed = {
        "take_rate": latest.get("take_rate") if latest else None,
        "contribution_margin": latest.get("contribution_margin") if latest else None,
        "incremental_operating_margin_disclosed": (
            latest.get("incremental_operating_margin_disclosed") if latest else None
        ),
        "segment_operating_margin": latest.get("segment_operating_margin") if latest else None,
    }

    metrics: dict[str, Any] = {
        "history_flags": flags,
        "n_fy": len(fy_rows),
        "n_q": len(q_rows),
        "periods_fy_keys": [r.get("period_key") for r in fy_rows],
        "periods_q_keys": [r.get("period_key") for r in q_rows],
        "margin_fy_series": fy_rows,
        "margin_q_series": q_rows,
        "gm_path_consistency": _path_consistency(gm_fy),
        "op_path_consistency": _path_consistency(op_fy),
        "latest_margins": latest,
        "prior_margins": prior,
        "delta_gm_yoy": delta_gm,
        "delta_op_yoy": delta_op,
        "incremental_om_windows": [w.to_dict() for w in iom_windows],
        "decompositions": decomps,
        "optional_disclosed": optional_disclosed,
        # Explicit non-goals markers for tests / report honesty
        "no_numeric_bands": True,
        "no_roic": True,
        "incremental_om_ne_roiic": True,
    }

    if not fy_rows:
        null_reasons["margin_fy_series"] = "UNKNOWN"
    if latest is None or latest.get("operating_margin") is None:
        null_reasons["latest_operating_margin"] = "UNKNOWN"
    if latest is None or latest.get("gross_margin") is None:
        null_reasons["latest_gross_margin"] = "UNKNOWN"

    return CalcResult(metrics=metrics, null_reasons=null_reasons)
