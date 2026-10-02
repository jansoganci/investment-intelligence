"""Deterministic Stage 3 cash-generation metrics — no pass/fail numbers, no LLM arithmetic."""
from __future__ import annotations

from typing import Any

from ..models import CalcResult
from .cfs_bridge import assemble_cfs_reconciliation


def _num(fields: dict, key: str) -> float | None:
    v = fields.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None



def _is_fy_period_row(r: dict[str, Any]) -> bool:
    """True when row is an annual FY period (cumulative window membership)."""
    pt = r.get("period_type")
    if pt == "FY":
        return True
    if pt in {"Q", "YTD"}:
        return False
    pk = r.get("period_key") or ""
    return bool(pk.startswith("FY") and str(pk[2:]).isdigit())


def _period_sort_key(doc: dict[str, Any]) -> tuple:
    """Prefer FY; then period_key ascending for chronological trends."""
    return (0 if doc.get("period_type") == "FY" else 1, doc.get("period_key") or "")


def _capex_conflict_reason(period: dict[str, Any]) -> str | None:
    """
    CapEx taxonomy / mapping conflict → FCF must be null (architecture + SPEC).
    Detect via field_uncertainty, lineage notes, or explicit period flag.
    """
    if period.get("capex_conflict") is True:
        return str(period.get("capex_conflict_reason") or "explicit capex_conflict flag")
    fu = period.get("field_uncertainty") or {}
    capex_u = fu.get("capex")
    if isinstance(capex_u, str):
        low = capex_u.lower()
        if any(tok in low for tok in ("conflict", "ambiguous", "multiple tags", "disagree")):
            return capex_u
    for lin in period.get("lineage") or []:
        if lin.get("field") != "capex":
            continue
        notes = (lin.get("notes") or "") + " " + str(lin.get("source_ref") or "")
        low = notes.lower()
        if lin.get("uncertain") and any(
            tok in low for tok in ("conflict", "ambiguous", "multiple tags", "disagree")
        ):
            return lin.get("notes") or "capex lineage uncertain with conflict/ambiguity"
    return None



# Bridge component roles (descriptive; not pass/fail). Signs follow common NI→OCF exhibit:
# non-cash addbacks typically help explain OCF > NI; equity-method income in NI often
# does not fully cash-settle into OCF (structural accounting gap).
_BRIDGE_SPECS: list[tuple[str, str, str]] = [
    # field, role, nature_tag
    ("depreciation_amortization", "non_cash_addback", "accounting"),
    ("sbc_expense", "non_cash_addback", "accounting"),
    ("deferred_tax_expense_benefit", "deferred_tax", "accounting"),
    ("equity_method_income", "in_ni_often_not_full_cash", "structural"),
    ("equity_method_income_net_of_dividends", "cf_equity_method_adjustment", "structural"),
    ("change_in_receivables_cf", "wc_cf_line", "wc"),
    ("change_in_inventory_cf", "wc_cf_line", "wc"),
    ("change_in_payables_cf", "wc_cf_line", "wc"),
]


def assemble_ocf_ni_bridge(period: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic OCF–NI bridge from Normalized fields only.
    No invented amounts. Residual may remain — that is honest, not a failure bar.
    """
    f = period.get("fields") or {}
    pk = period.get("period_key") or ""
    ocf = _num(f, "operating_cash_flow")
    ni = _num(f, "net_income")
    if ni is None:
        ni = _num(f, "net_income_attributable")
    gap = (ocf - ni) if (ocf is not None and ni is not None) else None

    components: list[dict[str, Any]] = []
    nature: set[str] = set()
    for field, role, tag in _BRIDGE_SPECS:
        amt = _num(f, field)
        if amt is None:
            continue
        components.append(
            {
                "field": field,
                "amount": amt,
                "role": role,
                "nature": tag,
                "certainty": "FACT",
                "source": "normalized",
            }
        )
        nature.add(tag)

    # Rough explained proxy: sum of non-cash addbacks + deferred tax − equity income
    # (equity income is in NI but often not full cash). WC CF lines are signed as reported.
    # This is descriptive assembly — not a claim the residual must be zero.
    explained = 0.0
    explained_n = 0
    for c in components:
        role, amt = c["role"], c["amount"]
        if role == "non_cash_addback":
            explained += amt
            explained_n += 1
        elif role == "deferred_tax":
            explained += amt
            explained_n += 1
        elif role == "in_ni_often_not_full_cash":
            # Presence in NI without matching cash widens OCF−NI negatively
            explained -= amt
            explained_n += 1
        elif role == "cf_equity_method_adjustment":
            # CF statement adjustment already signed; expose but do not double-count vs income
            explained_n += 1
        elif role == "wc_cf_line":
            # XBRL IncreaseDecrease* is typically the BS increase; CF uses opposite.
            # Expose amount factually; do not auto-flip without issuer convention certainty.
            explained_n += 1

    residual = None
    if gap is not None and explained_n:
        # Only use addbacks + deferred tax − equity income for residual estimate
        residual = gap - explained

    unresolved: list[str] = []
    if gap is not None and components:
        if residual is not None and abs(residual) > 0:
            unresolved.append(
                "Residual after known Normalized bridge components remains — "
                "attach MD&A explanations; do not invent reconciling amounts"
            )
        if _num(f, "change_in_payables_cf") is None:
            unresolved.append(
                "change_in_payables_cf null (MAPPING_AMBIGUOUS or NOT_DISCLOSED) — "
                "WC CF payables leg incomplete"
            )
    elif gap is not None and not components:
        unresolved.append("No bridge helper fields mapped — gap unexplained from Normalized alone")
    elif gap is None:
        unresolved.append("Need operating_cash_flow and net_income for bridge")

    if "structural" in nature and gap is not None and gap < 0:
        nature.add("structural")
    if any(c["role"] == "wc_cf_line" for c in components):
        nature.add("wc")
    if any(c["role"] in {"non_cash_addback", "deferred_tax"} for c in components):
        nature.add("accounting")
    if unresolved:
        nature.add("unresolved")

    return {
        "period_key": pk,
        "version_id": period.get("version_id"),
        "ocf": ocf,
        "ni": ni,
        "gap_ocf_minus_ni": gap,
        "components": components,
        "explained_proxy": explained if explained_n else None,
        "residual_after_proxy": residual,
        "nature_tags": sorted(nature),
        "factual_vs_uncertain": {
            "factual_components": [c["field"] for c in components],
            "uncertain": unresolved,
        },
        "notes": (
            "Bridge is deterministic assembly from Normalized facts only. "
            "explained_proxy uses D&A+SBC+deferred_tax−equity_method_income; "
            "WC CF lines listed but not auto-signed into proxy. No invented amounts."
        ),
    }


def compute_stage3_metrics(periods: list[dict[str, Any]]) -> CalcResult:
    """
    Multi-period Stage 3 dashboard (SPEC §5.1) — descriptive only.
    FCF = OCF − CapEx when CapEx lineage is clean; else null + conflict reason.
    """
    metrics: dict[str, Any] = {}
    null_reasons: dict[str, str] = {}

    if not periods:
        null_reasons["periods"] = "no Normalized periods provided"
        return CalcResult(metrics=metrics, null_reasons=null_reasons)

    # Chronological (oldest → newest) for trends; keep FY preference grouping
    ordered = sorted(periods, key=_period_sort_key)
    # Within same type, period_key sorts FY2023 < FY2024 < FY2025

    per_period: list[dict[str, Any]] = []
    for doc in ordered:
        f = doc.get("fields") or {}
        pk = doc.get("period_key") or ""
        vid = doc.get("version_id") or ""
        ocf = _num(f, "operating_cash_flow")
        ni = _num(f, "net_income")
        if ni is None:
            ni = _num(f, "net_income_attributable")
        capex = _num(f, "capex")
        da = _num(f, "depreciation_amortization")
        sbc = _num(f, "sbc_expense")
        rev = _num(f, "revenue")
        conflict = _capex_conflict_reason(doc)

        row: dict[str, Any] = {
            "period_key": pk,
            "period_type": doc.get("period_type"),
            "version_id": vid,
            "operating_cash_flow": ocf,
            "net_income": ni,
            "capex": capex,
            "depreciation_amortization": da,
            "sbc_expense": sbc,
            "revenue": rev,
            "receivables": _num(f, "receivables"),
            "inventory": _num(f, "inventory"),
            "accounts_payable": _num(f, "accounts_payable"),
            "deferred_revenue_current": _num(f, "deferred_revenue_current"),
            "deferred_revenue_noncurrent": _num(f, "deferred_revenue_noncurrent"),
            "business_acquisitions_cash": _num(f, "business_acquisitions_cash"),
            "proceeds_from_asset_sales": _num(f, "proceeds_from_asset_sales"),
            "capex_conflict": conflict is not None,
            "capex_conflict_reason": conflict,
            "fcf": None,
            "fcf_lineage": None,
            "ocf_minus_ni": None,
            "capex_to_da": None,
        }

        if ocf is not None and ni is not None:
            row["ocf_minus_ni"] = ocf - ni
        else:
            null_reasons[f"ocf_vs_ni:{pk}"] = "need operating_cash_flow and net_income"

        if conflict:
            row["fcf"] = None
            row["fcf_lineage"] = {
                "formula": "OCF - CapEx",
                "status": "conflict",
                "reason": conflict,
                "ocf": ocf,
                "capex": capex,
            }
            null_reasons[f"fcf:{pk}"] = f"CapEx conflict — FCF null: {conflict}"
        elif ocf is not None and capex is not None:
            # CapEx on CF statement is typically cash outflow as positive PaymentsToAcquire*;
            # Normalized stores the reported magnitude; FCF = OCF − CapEx (architecture §8.2).
            fcf = ocf - capex
            row["fcf"] = fcf
            row["fcf_lineage"] = {
                "formula": "OCF - CapEx",
                "status": "ok",
                "ocf": ocf,
                "capex": capex,
                "fcf": fcf,
                "period_key": pk,
                "version_id": vid,
            }
        else:
            row["fcf"] = None
            row["fcf_lineage"] = {
                "formula": "OCF - CapEx",
                "status": "incomplete",
                "reason": "need operating_cash_flow and capex",
                "ocf": ocf,
                "capex": capex,
            }
            null_reasons[f"fcf:{pk}"] = "need operating_cash_flow and capex"

        if capex is not None and da is not None and da != 0:
            row["capex_to_da"] = capex / da
        elif capex is None or da is None:
            null_reasons[f"capex_to_da:{pk}"] = "need capex and depreciation_amortization"

        per_period.append(row)

    metrics["per_period"] = per_period
    metrics["period_keys"] = [r["period_key"] for r in per_period]

    # Latest period snapshot
    latest = per_period[-1]
    metrics["latest_period_key"] = latest["period_key"]
    metrics["latest_ocf"] = latest["operating_cash_flow"]
    metrics["latest_ni"] = latest["net_income"]
    metrics["latest_fcf"] = latest["fcf"]
    metrics["latest_fcf_lineage"] = latest["fcf_lineage"]
    metrics["latest_capex"] = latest["capex"]
    metrics["latest_da"] = latest["depreciation_amortization"]
    metrics["latest_sbc"] = latest["sbc_expense"]
    metrics["latest_capex_to_da"] = latest["capex_to_da"]
    metrics["latest_capex_conflict"] = latest["capex_conflict"]

    # OCF vs NI multi-period series
    metrics["ocf_vs_ni_series"] = [
        {
            "period_key": r["period_key"],
            "ocf": r["operating_cash_flow"],
            "ni": r["net_income"],
            "ocf_minus_ni": r["ocf_minus_ni"],
        }
        for r in per_period
    ]

    # FCF trend (list of values oldest→newest; nulls preserved)
    fcf_series = [{"period_key": r["period_key"], "fcf": r["fcf"]} for r in per_period]
    metrics["fcf_series"] = fcf_series
    fcf_vals = [r["fcf"] for r in per_period if r["fcf"] is not None]
    if len(fcf_vals) >= 2:
        metrics["fcf_trend_delta"] = fcf_vals[-1] - fcf_vals[0]
        metrics["fcf_trend_direction"] = (
            "up" if fcf_vals[-1] > fcf_vals[0] else ("down" if fcf_vals[-1] < fcf_vals[0] else "flat")
        )
    else:
        metrics["fcf_trend_delta"] = None
        metrics["fcf_trend_direction"] = None
        null_reasons["fcf_trend"] = "need ≥2 periods with clean FCF"

    # CapEx trend
    capex_vals = [(r["period_key"], r["capex"]) for r in per_period if r["capex"] is not None]
    metrics["capex_series"] = [{"period_key": r["period_key"], "capex": r["capex"]} for r in per_period]
    if len(capex_vals) >= 2:
        metrics["capex_trend_delta"] = capex_vals[-1][1] - capex_vals[0][1]
        metrics["capex_trend_direction"] = (
            "up"
            if capex_vals[-1][1] > capex_vals[0][1]
            else ("down" if capex_vals[-1][1] < capex_vals[0][1] else "flat")
        )
    else:
        metrics["capex_trend_delta"] = None
        metrics["capex_trend_direction"] = None
        null_reasons["capex_trend"] = "need ≥2 periods with capex"

    # Multi-year cumulative conversion — FY-only non-overlapping window (Plan §0).
    # Interim/YTD/Qn rows remain in per_period series for trend/latest but MUST NOT
    # enter cumulative totals (F-S3-CUM-01: no FY+quarter / YTD double-count).
    fy_rows = [r for r in per_period if _is_fy_period_row(r)]
    ocf_sum = 0.0
    ni_sum = 0.0
    fcf_sum = 0.0
    ocf_n = ni_n = fcf_n = 0
    cum_keys: list[str] = []
    for r in fy_rows:
        used = False
        if r["operating_cash_flow"] is not None:
            ocf_sum += r["operating_cash_flow"]
            ocf_n += 1
            used = True
        if r["net_income"] is not None:
            ni_sum += r["net_income"]
            ni_n += 1
            used = True
        if r["fcf"] is not None:
            fcf_sum += r["fcf"]
            fcf_n += 1
            used = True
        if used:
            cum_keys.append(r["period_key"])
    metrics["cumulative_basis"] = "FY_only_non_overlapping"
    metrics["cumulative_period_keys"] = cum_keys
    metrics["cumulative_n_fy"] = len({r["period_key"] for r in fy_rows})
    metrics["cumulative_ocf"] = ocf_sum if ocf_n else None
    metrics["cumulative_ni"] = ni_sum if ni_n else None
    metrics["cumulative_fcf"] = fcf_sum if fcf_n else None
    if ocf_n and ni_n:
        metrics["cumulative_ocf_minus_ni"] = ocf_sum - ni_sum
        # Ratio is descriptive evidence only — NOT a pass/fail threshold
        metrics["cumulative_ocf_to_ni"] = (ocf_sum / ni_sum) if ni_sum != 0 else None
    else:
        metrics["cumulative_ocf_minus_ni"] = None
        metrics["cumulative_ocf_to_ni"] = None
        null_reasons["cumulative_ocf_vs_ni"] = "need OCF and NI across FY periods"
    if fcf_n and ni_n:
        metrics["cumulative_fcf_minus_ni"] = fcf_sum - ni_sum
        metrics["cumulative_fcf_to_ni"] = (fcf_sum / ni_sum) if ni_sum != 0 else None
    else:
        metrics["cumulative_fcf_minus_ni"] = None
        metrics["cumulative_fcf_to_ni"] = None
        if not fcf_n:
            null_reasons["cumulative_fcf_vs_ni"] = "no clean FY FCF periods for cumulative conversion"

    # Working-capital deltas (BS consecutive periods)
    wc_deltas: list[dict[str, Any]] = []
    for i in range(1, len(per_period)):
        cur, prev = per_period[i], per_period[i - 1]
        delta: dict[str, Any] = {
            "from_period": prev["period_key"],
            "to_period": cur["period_key"],
        }
        for key in (
            "receivables",
            "inventory",
            "accounts_payable",
            "deferred_revenue_current",
            "deferred_revenue_noncurrent",
            "revenue",
        ):
            c, p = cur.get(key), prev.get(key)
            if c is not None and p is not None:
                delta[f"delta_{key}"] = c - p
            else:
                delta[f"delta_{key}"] = None
                if key != "revenue":
                    null_reasons[f"delta_{key}:{cur['period_key']}"] = (
                        f"need multi-period {key}"
                    )
        # Deferred revenue total delta when either side present
        def _dr_total(row: dict) -> float | None:
            a, b = row.get("deferred_revenue_current"), row.get("deferred_revenue_noncurrent")
            if a is None and b is None:
                return None
            return (a or 0.0) + (b or 0.0)

        cur_dr, prev_dr = _dr_total(cur), _dr_total(prev)
        if cur_dr is not None and prev_dr is not None:
            delta["delta_deferred_revenue_total"] = cur_dr - prev_dr
        else:
            delta["delta_deferred_revenue_total"] = None
        wc_deltas.append(delta)
    metrics["wc_deltas"] = wc_deltas
    if not wc_deltas:
        null_reasons["wc_deltas"] = "single period only — WC deltas not computable"

    # SBC context (latest + vs OCF/NI when present — descriptive)
    metrics["sbc_context"] = {
        "sbc_expense": latest["sbc_expense"],
        "vs_ocf": (
            latest["sbc_expense"] / latest["operating_cash_flow"]
            if latest["sbc_expense"] is not None
            and latest["operating_cash_flow"] not in (None, 0)
            else None
        ),
        "vs_ni": (
            latest["sbc_expense"] / latest["net_income"]
            if latest["sbc_expense"] is not None and latest["net_income"] not in (None, 0)
            else None
        ),
    }
    if latest["sbc_expense"] is None:
        null_reasons["sbc_context"] = "sbc_expense missing in Normalized"

    # Materiality-triggered raw fields (not KPIs — expose for semantic/evaluator)
    metrics["acquisitions_cash_series"] = [
        {"period_key": r["period_key"], "amount": r["business_acquisitions_cash"]}
        for r in per_period
    ]
    metrics["asset_sales_series"] = [
        {"period_key": r["period_key"], "amount": r["proceeds_from_asset_sales"]}
        for r in per_period
    ]

    metrics["n_periods"] = len(per_period)
    n_fy = sum(1 for r in per_period if _is_fy_period_row(r))
    metrics["n_fy_periods"] = n_fy
    metrics["prefer_ge_3_fy_note"] = (
        "operational preference ≥3 FY when available — not a threshold rule"
        if n_fy < 3
        else "≥3 FY periods present"
    )

    # OCF–NI automatic bridges (per period) — legacy descriptive proxy
    bridges = [assemble_ocf_ni_bridge(doc) for doc in ordered]
    metrics["ocf_ni_bridges"] = bridges
    metrics["latest_ocf_ni_bridge"] = bridges[-1] if bridges else None

    # Official CFS reconciliation (NI_cfs + adjustments → OCF)
    cfs_bridges = [assemble_cfs_reconciliation(doc) for doc in ordered]
    metrics["cfs_reconciliations"] = cfs_bridges
    metrics["latest_cfs_reconciliation"] = cfs_bridges[-1] if cfs_bridges else None
    # When a period's official CFS ties out, drop legacy unexplained-residual flags for that period
    for b, cfs in zip(bridges, cfs_bridges):
        b["cfs_reconciliation_status"] = cfs.get("status")
        b["cfs_unexplained_residual"] = cfs.get("unexplained_residual")
        if cfs.get("status") == "RECONCILED":
            b.setdefault("factual_vs_uncertain", {})["uncertain"] = [
                u
                for u in (b.get("factual_vs_uncertain") or {}).get("uncertain") or []
                if "Residual after known" not in u and "gap unexplained" not in u
            ]
            if "unresolved" in (b.get("nature_tags") or []):
                b["nature_tags"] = [t for t in b["nature_tags"] if t != "unresolved"]
    metrics["ocf_ni_bridges"] = bridges
    metrics["latest_ocf_ni_bridge"] = bridges[-1] if bridges else None

    return CalcResult(metrics=metrics, null_reasons=null_reasons)
