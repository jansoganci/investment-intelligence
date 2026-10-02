"""Deterministic Stage 7 cash-use / share / distribution / debt exhibits.

No pass/fail bands, no LLM arithmetic, no ROIC/ROIIC/WACC recompute.
Gross repurchase + net share change when data exist. No payout thresholds.
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


def _abs_or_none(v: float | None) -> float | None:
    if v is None:
        return None
    return abs(v)


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


def _year_cash_uses(fields: dict[str, Any]) -> dict[str, Any]:
    """One FY cash-use row — magnitudes for composition; signs preserved in raw."""
    capex = _num(fields, "capex")
    acq = _num(fields, "business_acquisitions_cash")
    div = _num(fields, "dividends_paid")
    buyback = _num(fields, "share_repurchases")
    issuance = _num(fields, "share_issuances")
    sbc = _num(fields, "sbc_expense")
    ocf = _num(fields, "operating_cash_flow")
    debt_iss = _num(fields, "debt_issuance")
    debt_rep = _num(fields, "debt_repayment")
    total_debt = _num(fields, "total_debt")
    ltd = _num(fields, "long_term_debt")
    shares = _num(fields, "shares_outstanding")
    shares_dil = _num(fields, "shares_diluted_weighted")
    shares_basic = _num(fields, "shares_basic_weighted")

    uses_mag = {
        "organic_capex": _abs_or_none(capex),
        "acquisitions": _abs_or_none(acq),
        "dividends": _abs_or_none(div),
        "share_repurchases": _abs_or_none(buyback),
    }
    known = [v for v in uses_mag.values() if v is not None]
    total_known = sum(known) if known else None
    composition_pct: dict[str, float | None] = {}
    for k, v in uses_mag.items():
        if v is None or total_known is None or total_known == 0:
            composition_pct[k] = None
        else:
            composition_pct[k] = v / total_known

    return {
        "capex_raw": capex,
        "business_acquisitions_cash_raw": acq,
        "dividends_paid_raw": div,
        "share_repurchases_raw": buyback,
        "share_issuances_raw": issuance,
        "sbc_expense": sbc,
        "operating_cash_flow": ocf,
        "debt_issuance_raw": debt_iss,
        "debt_repayment_raw": debt_rep,
        "total_debt": total_debt,
        "long_term_debt": ltd,
        "shares_outstanding": shares,
        "shares_diluted_weighted": shares_dil,
        "shares_basic_weighted": shares_basic,
        "uses_magnitude": uses_mag,
        "composition_pct": composition_pct,
        "total_known_uses": total_known,
    }


def _revealed_hierarchy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Infer revealed hierarchy from multi-year cash-use magnitudes — descriptive only."""
    totals = {
        "organic_capex": 0.0,
        "acquisitions": 0.0,
        "dividends": 0.0,
        "share_repurchases": 0.0,
    }
    counts = {k: 0 for k in totals}
    for r in rows:
        um = r.get("uses_magnitude") or {}
        for k in totals:
            v = um.get(k)
            if v is not None:
                totals[k] += v
                counts[k] += 1
    ordered = sorted(
        ((k, totals[k]) for k in totals if counts[k] > 0),
        key=lambda x: -x[1],
    )
    rank = [k for k, _ in ordered]
    dominant = rank[0] if rank else None
    return {
        "multi_year_totals": totals,
        "years_with_data": counts,
        "revealed_rank_desc": rank,
        "dominant_use": dominant,
        "no_fixed_universal_order": True,
    }


def _share_trend(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Gross repurchase vs net share change — honesty exhibit; no yield gate."""
    series = []
    for r in rows:
        series.append(
            {
                "period_key": r.get("period_key"),
                "gross_repurchase": (r.get("uses_magnitude") or {}).get(
                    "share_repurchases"
                ),
                "share_issuances": _abs_or_none(r.get("share_issuances_raw")),
                "sbc_expense": r.get("sbc_expense"),
                "shares_outstanding": r.get("shares_outstanding"),
                "shares_diluted_weighted": r.get("shares_diluted_weighted"),
            }
        )
    net_share_change = None
    net_share_basis = None
    if len(series) >= 2:
        # Prefer period-end outstanding; fall back to diluted weighted
        first = next(
            (
                s
                for s in series
                if s.get("shares_outstanding") is not None
                or s.get("shares_diluted_weighted") is not None
            ),
            None,
        )
        last = next(
            (
                s
                for s in reversed(series)
                if s.get("shares_outstanding") is not None
                or s.get("shares_diluted_weighted") is not None
            ),
            None,
        )
        if first and last and first is not last:
            f_sh = first.get("shares_outstanding")
            l_sh = last.get("shares_outstanding")
            if f_sh is not None and l_sh is not None:
                net_share_change = l_sh - f_sh
                net_share_basis = "shares_outstanding"
            else:
                f_d = first.get("shares_diluted_weighted")
                l_d = last.get("shares_diluted_weighted")
                if f_d is not None and l_d is not None:
                    net_share_change = l_d - f_d
                    net_share_basis = "shares_diluted_weighted"

    gross_sum = sum(
        (s.get("gross_repurchase") or 0.0)
        for s in series
        if s.get("gross_repurchase") is not None
    )
    any_gross = any(s.get("gross_repurchase") is not None for s in series)
    sbc_sum = sum(
        (s.get("sbc_expense") or 0.0) for s in series if s.get("sbc_expense") is not None
    )
    any_sbc = any(s.get("sbc_expense") is not None for s in series)

    return {
        "series": series,
        "gross_repurchase_multi_year": gross_sum if any_gross else None,
        "sbc_expense_multi_year": sbc_sum if any_sbc else None,
        "net_share_change": net_share_change,
        "net_share_basis": net_share_basis,
        "gross_and_net_both_shown_when_available": True,
        "no_payout_threshold": True,
        "no_buyback_yield_gate": True,
    }


def _debt_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Debt level / change context for motive tagging — not Stage 2 solvency."""
    series = []
    for r in rows:
        series.append(
            {
                "period_key": r.get("period_key"),
                "total_debt": r.get("total_debt"),
                "long_term_debt": r.get("long_term_debt"),
                "debt_issuance": r.get("debt_issuance_raw"),
                "debt_repayment": r.get("debt_repayment_raw"),
                "acquisitions": (r.get("uses_magnitude") or {}).get("acquisitions"),
                "share_repurchases": (r.get("uses_magnitude") or {}).get(
                    "share_repurchases"
                ),
                "dividends": (r.get("uses_magnitude") or {}).get("dividends"),
            }
        )
    delta_debt = None
    if len(series) >= 2:
        first_d = next((s["total_debt"] for s in series if s["total_debt"] is not None), None)
        last_d = next(
            (s["total_debt"] for s in reversed(series) if s["total_debt"] is not None),
            None,
        )
        if first_d is not None and last_d is not None:
            delta_debt = last_d - first_d
    return {
        "series": series,
        "delta_total_debt": delta_debt,
        "no_solvency_retest": True,
        "stage2_owns_solvency": True,
    }


def _propose_debt_motives(debt: dict[str, Any], hierarchy: dict[str, Any]) -> list[str]:
    """Heuristic motive tags from co-movement — labels only; HITL on ambiguity."""
    tags: list[str] = []
    series = debt.get("series") or []
    delta = debt.get("delta_total_debt")
    acq_total = (hierarchy.get("multi_year_totals") or {}).get("acquisitions") or 0.0
    bb_total = (hierarchy.get("multi_year_totals") or {}).get("share_repurchases") or 0.0
    div_total = (hierarchy.get("multi_year_totals") or {}).get("dividends") or 0.0

    if delta is None and not any(
        s.get("debt_issuance") is not None or s.get("debt_repayment") is not None
        for s in series
    ):
        return ["unclear"]

    if delta is not None and delta > 0 and acq_total > 0 and acq_total >= bb_total:
        tags.append("deal_finance")
    if delta is not None and delta > 0 and (bb_total + div_total) > acq_total:
        tags.append("levered_distribution")
    if delta is not None and delta < 0:
        tags.append("fortress_build")
    if not tags:
        # Refi/ops when debt present but no clear co-movement
        if any(s.get("total_debt") for s in series):
            tags.append("refi_ops")
        else:
            tags.append("unclear")
    # Deduplicate preserve order
    return list(dict.fromkeys(tags))


# Material Stage 7 cash/share fields — carry Normalized lineage/uncertainty (no silent drop).
MATERIAL_STAGE7_FIELDS = (
    "capex",
    "share_repurchases",
    "sbc_expense",
    "dividends_paid",
    "shares_diluted_weighted",
    "shares_outstanding",
    "shares_basic_weighted",
    "business_acquisitions_cash",
    "operating_cash_flow",
    "debt_issuance",
    "debt_repayment",
    "total_debt",
    "long_term_debt",
)


def _period_row_provenance(period: dict[str, Any]) -> dict[str, Any]:
    """Structural provenance for one FY cash-use row (Normalized → Stage 7)."""
    fu = period.get("field_uncertainty") or {}
    unc = {
        k: fu[k]
        for k in MATERIAL_STAGE7_FIELDS
        if isinstance(fu, dict) and k in fu and fu[k]
    }
    field_lineage: dict[str, Any] = {}
    for entry in period.get("lineage") or []:
        if not isinstance(entry, dict):
            continue
        fld = entry.get("field")
        if fld not in MATERIAL_STAGE7_FIELDS:
            continue
        field_lineage[fld] = {
            "source_kind": entry.get("source_kind"),
            "source_ref": entry.get("source_ref"),
            "source_id": entry.get("source_id"),
            "uncertain": entry.get("uncertain"),
            "notes": entry.get("notes"),
            "value": entry.get("value"),
        }
    return {
        "accession": period.get("accession") or period.get("source_id"),
        "filed_at": period.get("filed_at"),
        "source_id": period.get("source_id"),
        "period_end": period.get("period_end"),
        "field_uncertainty": unc or None,
        "field_lineage": field_lineage or None,
    }


def _aggregate_material_uncertainty(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll up Normalized field_uncertainty across FY rows — do not present as clean FACT."""
    by_field: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        prov = r.get("provenance") or {}
        fu = prov.get("field_uncertainty") or {}
        if not isinstance(fu, dict):
            continue
        for k, note in fu.items():
            by_field.setdefault(k, []).append(
                {"period_key": r.get("period_key"), "note": note}
            )
    return {
        "fields_with_uncertainty": sorted(by_field.keys()),
        "by_field": by_field,
        "sbc_expense_uncertain": "sbc_expense" in by_field,
        "evidence_kind": "SYSTEM_INFERENCE",  # rollup label; underlying notes are Normalized
    }


def compute_stage7_metrics(
    periods: list[dict[str, Any]],
    *,
    prefer_fy: int = 5,
) -> CalcResult:
    """
    Deterministic Stage 7 exhibits from Normalized periods.
    Does NOT compute ROIC/ROIIC/WACC. Does NOT invent pay/governance DB.
    """
    null_reasons: dict[str, str] = {}
    fy_sel, hist_flags = _select_fy(periods, prefer_fy=prefer_fy)

    rows: list[dict[str, Any]] = []
    for p in fy_sel:
        fields = p.get("fields") or {}
        row = _year_cash_uses(fields)
        row["period_key"] = p.get("period_key")
        row["version_id"] = p.get("version_id")
        row["provenance"] = _period_row_provenance(p)
        rows.append(row)

    if not rows:
        null_reasons["cash_use_spine"] = "UNKNOWN"
        return CalcResult(
            metrics={
                "n_fy": 0,
                "history_flags": hist_flags,
                "cash_use_rows": [],
                "revealed_hierarchy": {
                    "revealed_rank_desc": [],
                    "dominant_use": None,
                    "no_fixed_universal_order": True,
                },
                "share_trend": {
                    "gross_and_net_both_shown_when_available": True,
                    "no_payout_threshold": True,
                },
                "debt_context": {"no_solvency_retest": True},
                "debt_motive_tags": ["unclear"],
                "no_roic_recompute": True,
                "no_wacc_recompute": True,
            },
            null_reasons=null_reasons,
        )

    hierarchy = _revealed_hierarchy(rows)
    share = _share_trend(rows)
    debt = _debt_context(rows)
    motives = _propose_debt_motives(debt, hierarchy)

    # Dividend presence for policy helper (semantic may override)
    div_years = sum(
        1
        for r in rows
        if (r.get("uses_magnitude") or {}).get("dividends") is not None
        and (r.get("uses_magnitude") or {}).get("dividends", 0) > 0
    )
    bb_years = sum(
        1
        for r in rows
        if (r.get("uses_magnitude") or {}).get("share_repurchases") is not None
        and (r.get("uses_magnitude") or {}).get("share_repurchases", 0) > 0
    )

    latest = rows[-1] if rows else {}
    if latest.get("shares_outstanding") is None and latest.get(
        "shares_diluted_weighted"
    ) is None:
        null_reasons["share_count"] = "NOT_DISCLOSED"
    if all((r.get("uses_magnitude") or {}).get("organic_capex") is None for r in rows):
        null_reasons["organic_capex"] = "NOT_DISCLOSED"

    metrics = {
        "n_fy": len(rows),
        "history_flags": hist_flags,
        "cash_use_rows": rows,
        "revealed_hierarchy": hierarchy,
        "share_trend": share,
        "debt_context": debt,
        "debt_motive_tags": motives,
        "dividend_years_positive": div_years,
        "buyback_years_positive": bb_years,
        "latest_period_key": latest.get("period_key"),
        "latest_uses": latest.get("uses_magnitude") or {},
        "latest_composition_pct": latest.get("composition_pct") or {},
        "no_roic_recompute": True,
        "no_roiic_recompute": True,
        "no_wacc_recompute": True,
        "no_payout_threshold": True,
        "no_fixed_capital_hierarchy": True,
        "distributions_combined_buybacks_and_dividends": True,
        "material_input_uncertainty": _aggregate_material_uncertainty(rows),
        "input_provenance": {
            "periods": [
                {
                    "period_key": r.get("period_key"),
                    "version_id": r.get("version_id"),
                    "accession": (r.get("provenance") or {}).get("accession"),
                    "filed_at": (r.get("provenance") or {}).get("filed_at"),
                    "period_end": (r.get("provenance") or {}).get("period_end"),
                }
                for r in rows
            ],
            "source_type": "Normalized",
            "evidence_kind": "FACT",
            "notes": (
                "Cash-use / share / SBC figures are FACT from Normalized fields "
                "(sec_companyfacts lineage). Aggregates and ranks are SYSTEM_INFERENCE. "
                "field_uncertainty from Normalized is preserved — never silently dropped."
            ),
        },
    }
    # Propagate SBC uncertainty onto share_trend for dashboard honesty
    miu = metrics["material_input_uncertainty"]
    if isinstance(share, dict):
        share = dict(share)
        share["sbc_expense_uncertain"] = bool(miu.get("sbc_expense_uncertain"))
        share["sbc_uncertainty_notes"] = (miu.get("by_field") or {}).get("sbc_expense") or []
        metrics["share_trend"] = share
    return CalcResult(metrics=metrics, null_reasons=null_reasons)
