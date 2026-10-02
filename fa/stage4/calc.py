"""Deterministic Stage 4 growth exhibits — no pass/fail numbers, no LLM arithmetic.

Descriptive YoY / CAGR / per-share / share-count / decomposition arithmetic only.
No invented quality thresholds. NC* bands NOT LOCKED — never used here.
"""
from __future__ import annotations

from typing import Any

from ..models import CalcResult, GrowthDecomposition


def _num(fields: dict, key: str) -> float | None:
    v = fields.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _period_sort_key(doc: dict[str, Any]) -> tuple:
    return (0 if doc.get("period_type") == "FY" else 1, doc.get("period_key") or "")



def period_duration_days(doc: dict[str, Any] | None) -> int | None:
    """SD-W4-C2: duration from period_start/end or persisted duration_days. No synthesis."""
    if not doc:
        return None
    if doc.get("duration_days") is not None:
        try:
            return int(doc["duration_days"])
        except (TypeError, ValueError):
            pass
    from datetime import date

    s, e = doc.get("period_start"), doc.get("period_end")
    if not s or not e:
        return None
    try:
        # Inclusive calendar span (retail 53-week years land ~371)
        return (
            date.fromisoformat(str(e)[:10]) - date.fromisoformat(str(s)[:10])
        ).days + 1
    except ValueError:
        return None


def is_fifty_three_week_duration(days: int | None) -> bool:
    """Honesty label band for ~53-week FY (typically 368–375 inclusive days)."""
    return days is not None and 368 <= days <= 375


def annotate_duration(doc: dict[str, Any] | None) -> dict[str, Any]:
    """Consumer-facing duration honesty (reported values unchanged)."""
    dur = period_duration_days(doc)
    return {
        "duration_days": dur,
        "fifty_three_week": is_fifty_three_week_duration(dur),
        "period_start": (doc or {}).get("period_start"),
        "period_end": (doc or {}).get("period_end"),
    }


def yoy_change(curr: float | None, prev: float | None) -> dict[str, Any]:
    """Absolute and fractional YoY change. Null when inputs missing or prev==0."""
    if curr is None or prev is None:
        return {
            "absolute": None,
            "fraction": None,
            "null_reason": "UNKNOWN" if curr is None or prev is None else None,
        }
    absolute = curr - prev
    if prev == 0:
        return {
            "absolute": absolute,
            "fraction": None,
            "null_reason": "BASE_ZERO",
        }
    return {"absolute": absolute, "fraction": absolute / prev, "null_reason": None}


def cagr(start: float | None, end: float | None, n_years: int) -> dict[str, Any]:
    """Multi-year CAGR. Descriptive only — not a hurdle."""
    if start is None or end is None or n_years <= 0:
        return {"cagr": None, "null_reason": "UNKNOWN", "n_years": n_years}
    if start <= 0 or end <= 0:
        return {"cagr": None, "null_reason": "NON_POSITIVE_BASE", "n_years": n_years}
    return {
        "cagr": (end / start) ** (1.0 / n_years) - 1.0,
        "null_reason": None,
        "n_years": n_years,
        "start": start,
        "end": end,
    }


def per_share(numerator: float | None, shares: float | None) -> dict[str, Any]:
    if numerator is None or shares is None:
        return {"value": None, "null_reason": "UNKNOWN"}
    if shares == 0:
        return {"value": None, "null_reason": "SHARES_ZERO"}
    return {"value": numerator / shares, "null_reason": None}


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


def _series(periods: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    out = []
    for p in periods:
        f = p.get("fields") or {}
        dur_meta = annotate_duration(p)
        out.append(
            {
                "period_key": p.get("period_key"),
                "version_id": p.get("version_id"),
                "value": _num(f, field),
                "duration_days": dur_meta["duration_days"],
                "fifty_three_week": dur_meta["fifty_three_week"],
            }
        )
    return out


def _yoy_series(series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """YoY with SD-W4-C2 duration honesty — no 53→52 normalize, no week-adjusted synthetics."""
    rows = []
    for i in range(1, len(series)):
        prev, curr = series[i - 1], series[i]
        ch = yoy_change(curr.get("value"), prev.get("value"))
        d0, d1 = prev.get("duration_days"), curr.get("duration_days")
        unequal = (
            d0 is not None
            and d1 is not None
            and abs(int(d0) - int(d1)) >= 5  # ≥5 calendar days (~1 week class)
        )
        row = {
            "from_period": prev.get("period_key"),
            "to_period": curr.get("period_key"),
            "from_value": prev.get("value"),
            "to_value": curr.get("value"),
            "from_duration_days": d0,
            "to_duration_days": d1,
            "unequal_duration": unequal,
            "from_fifty_three_week": bool(prev.get("fifty_three_week")),
            "to_fifty_three_week": bool(curr.get("fifty_three_week")),
            "duration_normalized": False,  # SD-W4-C2: never auto-normalize
            "week_adjusted_value": None,  # SD-W4-C2: never synthesize
            **ch,
        }
        if unequal:
            row["duration_honesty_flag"] = "UNEQUAL_DURATION_COMPARISON"
        rows.append(row)
    return rows


# Stage 4 owner-growth (BD4) prefers diluted weighted-average shares.
# Never mix: diluted WAD ≠ basic WAD ≠ period-end outstanding.
_SHARE_CONCEPT_PREFERENCE = (
    "shares_diluted_weighted",  # preferred for BD4
    "shares_basic_weighted",  # fallback only if diluted absent
    # period-end outstanding intentionally NOT used for BD4 trend/per-share
)

_SHARE_CONCEPT_LABEL = {
    "shares_diluted_weighted": "diluted_weighted_average",
    "shares_basic_weighted": "basic_weighted_average",
    "shares_outstanding": "period_end_outstanding",
}


def _share_field(fields: dict) -> tuple[float | None, str | None]:
    """Return (value, field_key) for BD4 owner-growth — prefer diluted WAD."""
    for key in _SHARE_CONCEPT_PREFERENCE:
        v = _num(fields, key)
        if v is not None:
            return v, key
    return None, None


def _share_concepts_present(fields: dict) -> dict[str, float | None]:
    return {k: _num(fields, k) for k in (
        "shares_diluted_weighted",
        "shares_basic_weighted",
        "shares_outstanding",
    )}


def assemble_decomposition_arithmetic(
    period: dict[str, Any],
    prior: dict[str, Any] | None,
) -> GrowthDecomposition:
    """
    Deterministic decomp arithmetic when structured Normalized inputs exist.
    Does NOT invent organic % — only uses disclosed optional fields.
    """
    f = period.get("fields") or {}
    pk = period.get("period_key") or ""
    rev = _num(f, "revenue")
    prior_rev = _num((prior or {}).get("fields") or {}, "revenue") if prior else None
    ch = yoy_change(rev, prior_rev)

    components: list[dict[str, Any]] = []
    organic = _num(f, "revenue_organic_growth_yoy")
    acquired = _num(f, "revenue_acquired_impact_yoy")
    cc = _num(f, "constant_currency_revenue_growth_yoy")
    volume = _num(f, "volume_metric")

    if organic is not None:
        components.append(
            {
                "dimension": "organic",
                "magnitude_note": f"disclosed organic YoY fraction={organic}",
                "value": organic,
                "evidence_tag": "FACT",
                "citation": "normalized:revenue_organic_growth_yoy",
            }
        )
    if acquired is not None:
        components.append(
            {
                "dimension": "acquisition",
                "magnitude_note": f"disclosed acquired impact YoY fraction={acquired}",
                "value": acquired,
                "evidence_tag": "FACT",
                "citation": "normalized:revenue_acquired_impact_yoy",
            }
        )
    if cc is not None and ch.get("fraction") is not None:
        # FX gap descriptive: reported − constant-currency when both present
        fx_gap = ch["fraction"] - cc
        components.append(
            {
                "dimension": "FX",
                "magnitude_note": (
                    f"reported_fraction={ch['fraction']}; constant_currency={cc}; "
                    f"implied_FX_gap={fx_gap}"
                ),
                "value": fx_gap,
                "evidence_tag": "FACT",
                "citation": "normalized:constant_currency_revenue_growth_yoy",
            }
        )
    if volume is not None:
        components.append(
            {
                "dimension": "volume",
                "magnitude_note": f"volume_metric={volume}; def={f.get('volume_metric_definition')}",
                "value": volume,
                "evidence_tag": "FACT",
                "citation": "normalized:volume_metric",
            }
        )

    ma_cash = _num(f, "business_acquisitions_cash")
    if ma_cash is not None and abs(ma_cash) > 0:
        components.append(
            {
                "dimension": "acquisition",
                "magnitude_note": f"business_acquisitions_cash={ma_cash} (cash clue, not revenue %)",
                "value": ma_cash,
                "evidence_tag": "FACT",
                "citation": "normalized:business_acquisitions_cash",
            }
        )

    unattr = None
    if not components:
        unattr = (
            "No disclosed organic/acquired/FX/volume Normalized fields — "
            "UNATTRIBUTED pending semantic MD&A; do not invent split"
        )
    org_acq = None
    if organic is not None or acquired is not None:
        org_acq = (
            f"organic={organic if organic is not None else 'UNKNOWN'}; "
            f"acquired={acquired if acquired is not None else 'UNKNOWN'}"
        )
    else:
        org_acq = "UNKNOWN — not disclosed in Normalized (semantic may add COMPANY_EXPLANATION)"

    return GrowthDecomposition(
        period_key=pk,
        reported_revenue_change=ch.get("absolute"),
        reported_revenue_change_pct=ch.get("fraction"),
        components=components,
        unattributed_or_unknown=unattr,
        organic_vs_acquired_summary=org_acq,
    )


def compute_stage4_metrics(
    periods: list[dict[str, Any]],
    *,
    extend_full_cycle: bool = False,
    stage3_fcf_by_period: dict[str, float] | None = None,
    semantic_texts: list[str] | None = None,
    explicit_comparability_breaks: list[dict[str, Any]] | None = None,
    disclosed_comparable_companion: list[dict[str, Any]] | None = None,
) -> CalcResult:
    """
    Build descriptive growth exhibits from Normalized CURRENT periods.
    LLM never calls this for invention — only code arithmetic.

    Wave 4 / SD-W4-C1: as-reported preserved; COMPARABILITY_BREAK labeled;
    disclosed comparable companion only when provided — never model-created recast.
    Wave 4 / SD-W4-C2: duration_days / unequal-duration honesty on YoY rows.
    """
    metrics: dict[str, Any] = {}
    null_reasons: dict[str, str] = {}

    all_fy = sorted(
        [p for p in periods if p.get("period_type") == "FY"],
        key=lambda d: d.get("period_key") or "",
    )
    fy, q, flags = _select_periods(
        periods, prefer_fy=5, prefer_q=8, extend_full_cycle=extend_full_cycle
    )
    flags["fy_available_total"] = len(all_fy)
    metrics["history_flags"] = flags
    if flags["history_thin"]:
        null_reasons["history_depth"] = (
            f"Only {flags['fy_available']} FY available (prefer ≥3 when available; "
            "descriptive — not a fail bar)"
        )

    rev_fy = _series(fy, "revenue")
    ni_fy = _series(fy, "net_income")
    # fallback attributable
    for i, p in enumerate(fy):
        if ni_fy[i]["value"] is None:
            ni_fy[i]["value"] = _num(p.get("fields") or {}, "net_income_attributable")
    eps_fy = _series(fy, "diluted_eps")
    sbc_fy = _series(fy, "sbc_expense")
    ma_fy = _series(fy, "business_acquisitions_cash")
    capex_fy = _series(fy, "capex")
    ocf_fy = _series(fy, "operating_cash_flow")

    metrics["revenue_fy_series"] = rev_fy
    metrics["net_income_fy_series"] = ni_fy
    metrics["diluted_eps_fy_series"] = eps_fy
    metrics["sbc_fy_series"] = sbc_fy
    metrics["ma_cash_fy_series"] = ma_fy
    metrics["capex_fy_series"] = capex_fy
    metrics["ocf_fy_series"] = ocf_fy

    metrics["revenue_yoy"] = _yoy_series(rev_fy)
    # SD-W4-C2: period-level duration exhibits for consumers (reported values unchanged)
    metrics["fy_duration_exhibits"] = [
        {
            "period_key": p.get("period_key"),
            **annotate_duration(p),
        }
        for p in fy
    ]
    metrics["unequal_duration_yoy_pairs"] = [
        {
            "from_period": r["from_period"],
            "to_period": r["to_period"],
            "from_duration_days": r.get("from_duration_days"),
            "to_duration_days": r.get("to_duration_days"),
        }
        for r in metrics["revenue_yoy"]
        if r.get("unequal_duration")
    ]

    # SD-W4-C1 dual-series honesty
    from ..comparability import (
        annotate_yoy_rows_with_breaks,
        attach_disclosed_comparable_companion,
        detect_comparability_breaks,
    )

    breaks = detect_comparability_breaks(
        periods,
        semantic_texts=semantic_texts,
        explicit_breaks=explicit_comparability_breaks,
    )
    if disclosed_comparable_companion:
        breaks = [
            attach_disclosed_comparable_companion(
                b, companion_series=disclosed_comparable_companion
            )
            for b in breaks
        ]
    metrics["comparability_breaks"] = breaks
    metrics["revenue_yoy"] = annotate_yoy_rows_with_breaks(
        metrics["revenue_yoy"], breaks
    )
    metrics["revenue_series_primary"] = "as_reported"
    metrics["comparable_companion_present"] = bool(
        disclosed_comparable_companion
    ) and any(b.get("comparable_companion") for b in breaks)
    # Never synthesize companion when not disclosed
    if not disclosed_comparable_companion:
        for b in breaks:
            b["comparable_companion"] = None
            b["model_reconstruction"] = False

    metrics["net_income_yoy"] = _yoy_series(ni_fy)
    metrics["diluted_eps_yoy"] = _yoy_series(eps_fy)

    # 3Y / 5Y CAGR from full FY history (display window remains ~5)
    rev_all = _series(all_fy, "revenue")
    if len(fy) >= 2 and rev_fy[0]["value"] is not None and rev_fy[-1]["value"] is not None:
        n = len(fy) - 1
        metrics["revenue_cagr_window"] = cagr(rev_fy[0]["value"], rev_fy[-1]["value"], n)
    else:
        metrics["revenue_cagr_window"] = cagr(
            rev_fy[0]["value"] if rev_fy else None,
            rev_fy[-1]["value"] if rev_fy else None,
            max(len(fy) - 1, 0),
        )
        if len(fy) < 4:
            null_reasons["revenue_cagr_3y5y"] = (
                "Fewer than 4 FY points for a 3Y CAGR exhibit; window CAGR still descriptive"
            )

    if len(rev_all) >= 6:
        metrics["revenue_cagr_5y"] = cagr(rev_all[-6]["value"], rev_all[-1]["value"], 5)
    else:
        metrics["revenue_cagr_5y"] = {
            "cagr": None,
            "null_reason": "INSUFFICIENT_FY_FOR_5Y",
            "n_years": 5,
        }
        null_reasons["revenue_cagr_5y"] = "Need 6 FY points for 5Y CAGR exhibit"

    if len(rev_all) >= 4:
        metrics["revenue_cagr_3y"] = cagr(rev_all[-4]["value"], rev_all[-1]["value"], 3)
    else:
        metrics["revenue_cagr_3y"] = {
            "cagr": None,
            "null_reason": "INSUFFICIENT_FY_FOR_3Y",
            "n_years": 3,
        }
        null_reasons["revenue_cagr_3y"] = "Need 4 FY points for 3Y CAGR exhibit"

    # Quarterly path
    rev_q = _series(q, "revenue")
    metrics["revenue_q_series"] = rev_q
    metrics["revenue_q_yoy"] = _yoy_series(rev_q)

    # Share-count trend + per-share economics (prefer diluted WAD; never mix concepts)
    share_rows: list[dict[str, Any]] = []
    per_share_rows: list[dict[str, Any]] = []
    concepts_used: list[str] = []
    for p in fy:
        f = p.get("fields") or {}
        sh, sh_key = _share_field(f)
        concepts = _share_concepts_present(f)
        rev = _num(f, "revenue")
        ni = _num(f, "net_income")
        if ni is None:
            ni = _num(f, "net_income_attributable")
        ocf = _num(f, "operating_cash_flow")
        capex = _num(f, "capex")
        fcf = None
        pk = p.get("period_key") or ""
        if stage3_fcf_by_period and pk in stage3_fcf_by_period:
            fcf = stage3_fcf_by_period[pk]
        elif ocf is not None and capex is not None:
            fcf = ocf - capex  # same Stage 3 formula when Stage 3 artifact absent

        if sh_key:
            concepts_used.append(sh_key)
        share_rows.append(
            {
                "period_key": pk,
                "shares": sh,
                "shares_field": sh_key,
                "shares_concept": _SHARE_CONCEPT_LABEL.get(sh_key) if sh_key else None,
                "concepts_present": concepts,
                "unit": "shares" if sh is not None else None,
                "null_reason": None if sh is not None else "NOT_DISCLOSED",
            }
        )
        if sh is None:
            # Prefer AUTOMATION_GAP only when mapping truly failed; else NOT_DISCLOSED
            null_reasons[f"shares:{pk}"] = (
                "NOT_DISCLOSED — no diluted/basic weighted-average shares in Normalized "
                "(period-end outstanding alone is not used for BD4)"
            )

        rps = per_share(rev, sh)
        nips = per_share(ni, sh)
        fcfps = per_share(fcf, sh)
        per_share_rows.append(
            {
                "period_key": pk,
                "revenue_per_share": rps,
                "ni_per_share": nips,
                "fcf_per_share": fcfps,
                "absolute_revenue": rev,
                "absolute_ni": ni,
                "absolute_fcf": fcf,
                "shares_concept_used": _SHARE_CONCEPT_LABEL.get(sh_key) if sh_key else None,
            }
        )

    metrics["share_count_trend"] = share_rows
    metrics["per_share_exhibit"] = per_share_rows
    preferred_concept = None
    for c in _SHARE_CONCEPT_PREFERENCE:
        if c in concepts_used:
            preferred_concept = c
            break
    metrics["share_concept_used_for_bd4"] = preferred_concept
    metrics["share_concept_label"] = _SHARE_CONCEPT_LABEL.get(preferred_concept) if preferred_concept else None
    metrics["share_concept_note"] = (
        "BD4 uses diluted weighted-average shares when available; "
        "basic WAD is fallback; period-end outstanding is stored separately and not mixed"
    )

    # Share Δ descriptive
    share_vals = [r["shares"] for r in share_rows if r["shares"] is not None]
    if len(share_vals) >= 2:
        metrics["share_count_delta"] = share_vals[-1] - share_vals[0]
        metrics["share_count_direction"] = (
            "down" if share_vals[-1] < share_vals[0] else (
                "up" if share_vals[-1] > share_vals[0] else "flat"
            )
        )
    else:
        metrics["share_count_delta"] = None
        metrics["share_count_direction"] = "UNKNOWN"
        null_reasons["share_count_trend"] = (
            "Insufficient share disclosures for trend "
            "(need ≥2 FY with diluted or basic weighted-average shares)"
        )

    # Absolute vs per-share growth (descriptive — not mechanical good/bad)
    abs_vs_ps: list[dict[str, Any]] = []
    for i in range(1, len(per_share_rows)):
        prev, curr = per_share_rows[i - 1], per_share_rows[i]
        row: dict[str, Any] = {
            "from_period": share_rows[i - 1]["period_key"],
            "to_period": share_rows[i]["period_key"],
        }
        for abs_key, ps_key, label in (
            ("absolute_revenue", "revenue_per_share", "revenue"),
            ("absolute_ni", "ni_per_share", "ni"),
            ("absolute_fcf", "fcf_per_share", "fcf"),
        ):
            a0, a1 = prev.get(abs_key), curr.get(abs_key)
            p0 = (prev.get(ps_key) or {}).get("value")
            p1 = (curr.get(ps_key) or {}).get("value")
            row[f"{label}_abs_yoy"] = yoy_change(a1, a0)
            row[f"{label}_ps_yoy"] = yoy_change(p1, p0)
        abs_vs_ps.append(row)
    metrics["absolute_vs_per_share_growth"] = abs_vs_ps

    # Historical consistency: sign of YoY revenue across window
    yoy = metrics["revenue_yoy"]
    signs = []
    for row in yoy:
        frac = row.get("fraction")
        if frac is None:
            continue
        signs.append("up" if frac > 0 else ("down" if frac < 0 else "flat"))
    metrics["revenue_yoy_sign_path"] = signs
    if signs:
        metrics["revenue_path_consistency"] = (
            "all_up" if all(s == "up" for s in signs) else (
                "all_down" if all(s == "down" for s in signs) else "mixed"
            )
        )
    else:
        metrics["revenue_path_consistency"] = "UNKNOWN"

    # Latest headline
    latest_yoy = yoy[-1] if yoy else None
    metrics["latest_revenue_yoy"] = latest_yoy
    metrics["latest_revenue"] = rev_fy[-1]["value"] if rev_fy else None
    metrics["latest_ni"] = ni_fy[-1]["value"] if ni_fy else None
    metrics["n_fy"] = len(fy)
    metrics["n_q"] = len(q)

    # Decompositions for consecutive FY pairs
    decomps: list[dict[str, Any]] = []
    for i in range(1, len(fy)):
        d = assemble_decomposition_arithmetic(fy[i], fy[i - 1])
        decomps.append(d.to_dict())
    metrics["decompositions"] = decomps

    # Per-share vs absolute honesty: when shares shrink and EPS rises faster than NI
    if len(ni_fy) >= 2 and len(eps_fy) >= 2:
        ni_ch = yoy_change(ni_fy[-1]["value"], ni_fy[-2]["value"])
        eps_ch = yoy_change(eps_fy[-1]["value"], eps_fy[-2]["value"])
        metrics["ni_vs_eps_yoy"] = {
            "ni_yoy": ni_ch,
            "eps_yoy": eps_ch,
            "note": (
                "EPS can outpace NI via share shrink — descriptive FP7 watch context; "
                "not a fail bar"
            ),
        }
    else:
        metrics["ni_vs_eps_yoy"] = None
        null_reasons["ni_vs_eps_yoy"] = "Need ≥2 FY with NI and diluted EPS"

    # Optional disclosed organic / FX / volume on latest
    if fy:
        lf = fy[-1].get("fields") or {}
        metrics["latest_optional_disclosed"] = {
            "revenue_organic_growth_yoy": _num(lf, "revenue_organic_growth_yoy"),
            "revenue_acquired_impact_yoy": _num(lf, "revenue_acquired_impact_yoy"),
            "constant_currency_revenue_growth_yoy": _num(
                lf, "constant_currency_revenue_growth_yoy"
            ),
            "volume_metric": _num(lf, "volume_metric"),
            "volume_metric_definition": lf.get("volume_metric_definition"),
            "same_store_sales_yoy": _num(lf, "same_store_sales_yoy"),
            "backlog_or_rpo": _num(lf, "backlog_or_rpo"),
            "geo_revenue_split": lf.get("geo_revenue_split"),
        }
        for k, v in list(metrics["latest_optional_disclosed"].items()):
            if v is None and k != "volume_metric_definition" and k != "geo_revenue_split":
                null_reasons[f"optional:{k}"] = "NOT_DISCLOSED"

    # Capital intensity pattern clue for BD9 (no ROIC)
    if fy:
        lf = fy[-1].get("fields") or {}
        capex = _num(lf, "capex")
        rev = _num(lf, "revenue")
        ma = _num(lf, "business_acquisitions_cash")
        metrics["capital_intensity_pattern"] = {
            "capex": capex,
            "revenue": rev,
            "capex_to_revenue": (capex / rev) if (capex is not None and rev and rev != 0) else None,
            "business_acquisitions_cash": ma,
            "note": "Pattern only — incremental returns → Stage 6; no ROIC here",
        }

    metrics["periods_fy_keys"] = [p.get("period_key") for p in fy]
    metrics["periods_q_keys"] = [p.get("period_key") for p in q]

    return CalcResult(metrics=metrics, null_reasons=null_reasons)
