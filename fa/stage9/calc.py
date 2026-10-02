"""Deterministic Stage 9 helpers — concentration descriptors, cycle class soft hints.

No pass/fail bands, no numeric risk gates, no averaged external-risk score,
no industry warehouse, no Stage 5/6/8 recompute.
"""
from __future__ import annotations

from typing import Any

from ..models import CalcResult
from .questions import CONCENTRATION_LABELS, CYCLE_POSITION_CLASSES


def _num(fields: dict, key: str) -> float | None:
    v = fields.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _select_fy(
    periods: list[dict[str, Any]],
    *,
    prefer_fy: int = 5,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fy = sorted(
        [p for p in periods if p.get("period_type") == "FY"],
        key=lambda d: d.get("period_key") or "",
    )
    fy_sel = fy[-prefer_fy:] if fy else []
    flags = {
        "fy_available": len(fy),
        "fy_used": len(fy_sel),
        "history_thin": len(fy) < 3,
        "prefer_ge_3_fy": len(fy) >= 3,
    }
    return fy_sel, flags


def descriptive_concentration_label(
    *,
    disclosed_pct: float | None = None,
    semantic_extreme: bool = False,
    semantic_high: bool = False,
    semantic_moderate: bool = False,
    opaque: bool = False,
) -> str:
    """Descriptive label only — thresholds NOT LOCKED; never auto-fail.

    Prefer semantic cues; disclosed_pct is optional context when company discloses
    a top-customer / geo share (still not a gate).
    """
    if opaque and disclosed_pct is None and not (semantic_extreme or semantic_high or semantic_moderate):
        return "unknown"
    if semantic_extreme:
        label = "extreme"
    elif semantic_high:
        label = "high"
    elif semantic_moderate:
        label = "moderate"
    elif disclosed_pct is None:
        label = "unknown"
    elif disclosed_pct >= 0.40:
        # RESEARCH_CANDIDATE packaging only — NOT a locked gate / auto-fail
        label = "extreme"
    elif disclosed_pct >= 0.20:
        label = "high"
    elif disclosed_pct >= 0.10:
        label = "moderate"
    else:
        label = "low"
    assert label in CONCENTRATION_LABELS
    return label


def soft_cycle_position_class(
    *,
    primary_archetype: str | None,
    s8_cycle_sensitive: bool = False,
    peak_language: bool = False,
    mid_cycle_honesty_flag: bool = False,
) -> str:
    """Descriptive cycle-position class — NOT a prediction; prepare ≠ predict."""
    if primary_archetype in {"A8", "A9"}:
        if peak_language:
            label = "late"
        elif mid_cycle_honesty_flag or s8_cycle_sensitive:
            label = "mid"
        else:
            label = "unknown"
    elif s8_cycle_sensitive or peak_language:
        label = "unknown"  # non-A8/A9: do not fake precision
    else:
        label = "unknown"
    assert label in CYCLE_POSITION_CLASSES
    return label


def compute_stage9_metrics(
    periods: list[dict[str, Any]],
    *,
    prefer_fy: int = 5,
    semantic_cues: dict[str, Any] | None = None,
    primary_archetype: str | None = None,
    s8_h9: list[str] | None = None,
) -> CalcResult:
    """Assemble deterministic helper metrics — exhibits only, no gates."""
    cues = semantic_cues or {}
    s8_h9 = s8_h9 or []
    fy_sel, hist = _select_fy(periods, prefer_fy=prefer_fy)

    # Optional disclosed fields if ever present on Normalized (usually absent)
    disclosed_customer = None
    disclosed_geo = None
    for p in reversed(fy_sel):
        fields = p.get("fields") or {}
        if disclosed_customer is None:
            disclosed_customer = _num(fields, "top_customer_revenue_pct") or _num(
                fields, "largest_customer_concentration_pct"
            )
        if disclosed_geo is None:
            disclosed_geo = _num(fields, "top_geo_revenue_pct")

    axes = {
        "customer": descriptive_concentration_label(
            disclosed_pct=disclosed_customer,
            semantic_extreme=bool(cues.get("customer_extreme")),
            semantic_high=bool(cues.get("customer_high")),
            semantic_moderate=bool(cues.get("customer_moderate")),
            opaque=bool(cues.get("customer_opaque", True)),
        ),
        "supplier": descriptive_concentration_label(
            semantic_extreme=bool(cues.get("supplier_extreme")),
            semantic_high=bool(cues.get("supplier_high")),
            semantic_moderate=bool(cues.get("supplier_moderate")),
            opaque=bool(cues.get("supplier_opaque", True)),
        ),
        "geo": descriptive_concentration_label(
            disclosed_pct=disclosed_geo,
            semantic_extreme=bool(cues.get("geo_extreme")),
            semantic_high=bool(cues.get("geo_high")),
            semantic_moderate=bool(cues.get("geo_moderate")),
            opaque=bool(cues.get("geo_opaque", True)),
        ),
        "product": descriptive_concentration_label(
            semantic_extreme=bool(cues.get("product_extreme")),
            semantic_high=bool(cues.get("product_high")),
            semantic_moderate=bool(cues.get("product_moderate")),
            opaque=bool(cues.get("product_opaque", True)),
        ),
        "distribution": descriptive_concentration_label(
            semantic_extreme=bool(cues.get("distribution_extreme")),
            semantic_high=bool(cues.get("distribution_high")),
            semantic_moderate=bool(cues.get("distribution_moderate")),
            opaque=bool(cues.get("distribution_opaque", True)),
        ),
    }

    cycle_class = soft_cycle_position_class(
        primary_archetype=primary_archetype,
        s8_cycle_sensitive="S8_H9_CYCLE_SENSITIVE_VALUATION" in s8_h9,
        peak_language=bool(cues.get("peak_cycle_language")),
        mid_cycle_honesty_flag=bool(cues.get("mid_cycle_honesty")),
    )

    null_reasons: dict[str, str] = {}
    if not fy_sel:
        null_reasons["fy_spine"] = "UNKNOWN"
    if all(v == "unknown" for v in axes.values()):
        null_reasons["concentration_structured"] = (
            "No disclosed concentration fields / weak semantic cues — labels=unknown "
            "(not a clean bill; deepen 10-K Risk Factors / Competition)"
        )

    metrics: dict[str, Any] = {
        "history": hist,
        "n_fy": hist["fy_used"],
        "concentration_axes": axes,
        "concentration_no_auto_fail": True,
        "concentration_thresholds_not_locked": True,
        "cycle_position_class": cycle_class,
        "cycle_position_is_not_prediction": True,
        "prepare_not_predict": True,
        "no_numeric_risk_gates": True,
        "no_averaged_external_risk_score": True,
        "no_industry_warehouse": True,
        "no_porter_score": True,
        "no_country_risk_engine": True,
        "no_stage5_pricing_power_redo": True,
        "no_stage1_thesis_restatement": True,
        "no_stage8_valuation_redo": True,
        "no_final_fa_synthesis": True,
        "er9_merged_into_er1_er7": True,
        "disclosed_top_customer_pct": disclosed_customer,
        "disclosed_top_geo_pct": disclosed_geo,
        "s8_h9_soft_linked": list(s8_h9),
    }
    return CalcResult(metrics=metrics, null_reasons=null_reasons)


__all__ = [
    "compute_stage9_metrics",
    "descriptive_concentration_label",
    "soft_cycle_position_class",
]
