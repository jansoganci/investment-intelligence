"""Stage 3 question spine → evidence pack + process outcome.

Outcomes ONLY: PROCEED | CONDITIONAL | REVIEW_REQUIRED | TOO_HARD.
No numeric thresholds. No colors. Stage 3 does NOT mechanically terminate later stages.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ids import utc_now
from ..models import (
    CalcResult,
    QuestionAnswer,
    Stage3ProcessOutcome,
    Stage3Report,
    Stage3SemanticReview,
)
from .calc import compute_stage3_metrics
from .questions import MUST_QUESTIONS, SHOULD_QUESTIONS, STAGE3_OUTCOMES
from .semantic import (
    attach_bridge_semantic_explanations,
    load_stage3_semantic_from_fixture,
    placeholder_stage3_semantic,
)


def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _must_map() -> dict[str, str]:
    return {qid: q for qid, q in MUST_QUESTIONS}


def evaluate_stage3(
    ticker: str,
    periods: list[dict[str, Any]],
    *,
    gate0_class: str = "operating",
    sources: list[str] | None = None,
    semantic: Stage3SemanticReview | None = None,
    semantic_notes_path: Path | None = None,
    thesis_summary: str | None = None,
    unresolved_major_conflict: bool = False,
) -> Stage3Report:
    """
    Evaluate Stage 3 Cash Generation from Normalized CURRENT periods + semantic review.

    FI / non-operating Gate 0 → refuse with TOO_HARD (HARD OUT OF SCOPE).
    Serious cash issues → REVIEW_REQUIRED + carry_forward_concerns.
    terminates_later_stages is always False.
    """
    ticker = ticker.upper()
    sources = sources or []
    must_q = _must_map()

    if semantic is None:
        if semantic_notes_path:
            semantic = load_stage3_semantic_from_fixture(semantic_notes_path)
        else:
            semantic = placeholder_stage3_semantic()

    periods_sorted = sorted(
        periods,
        key=lambda d: (0 if d.get("period_type") == "FY" else 1, d.get("period_key") or ""),
    )

    carry: list[str] = []
    gaps: list[str] = []
    warnings: list[str] = []
    why: list[str] = []
    answers: list[QuestionAnswer] = []

    def ans(
        qid: str,
        status: str,
        summary: str,
        evidence: list[str] | None = None,
        *,
        must: bool = True,
    ) -> None:
        if must:
            qtext = must_q[qid]
        else:
            qtext = next(q for i, q in SHOULD_QUESTIONS if i == qid)
        answers.append(
            QuestionAnswer(
                question_id=qid,
                question=qtext,
                status=status,  # type: ignore[arg-type]
                answer_summary=summary,
                evidence=evidence or [],
                must=must,
            )
        )

    # --- FI HARD OUT OF SCOPE ---
    if gate0_class != "operating":
        reason = (
            f"Gate 0 class is '{gate0_class}' — Financial Institutions / non-operating "
            "are HARD OUT OF SCOPE for Stage 3 OpCo cash logic; refuse"
        )
        ans("S3-M1", "blocked", reason, [])
        ans("S3-M2", "blocked", reason, [])
        ans("S3-M3", "blocked", "Maintenance CapEx UNKNOWN (stage refused)", [])
        ans("S3-M4", "blocked", reason, [])
        ans("S3-M5", "blocked", reason, [])
        ans("S3-M6", "blocked", reason, [])
        ans("S3-M7", "blocked", reason, [])
        ans(
            "S3-M8",
            "answered",
            f"process_outcome=TOO_HARD; {reason}",
            ["TOO_HARD"],
        )
        for qid, qtext in SHOULD_QUESTIONS:
            answers.append(
                QuestionAnswer(
                    question_id=qid,
                    question=qtext,
                    status="blocked",
                    answer_summary="Stage 3 refused — Gate 0 ≠ operating",
                    evidence=[],
                    must=False,
                )
            )
        return Stage3Report(
            ticker=ticker,
            date=utc_now(),
            periods_used=[],
            sources=sources,
            process_outcome="TOO_HARD",
            why_bullets=[reason],
            carry_forward_concerns=[reason],
            cash_conversion_bullets=[],
            working_capital_bullets=[],
            capex_bullets=["Maintenance CapEx: UNKNOWN (stage refused)"],
            cash_quality_warnings=[],
            what_is_strong=[],
            what_can_break=[],
            monitors=[],
            missing_ambiguous=[reason],
            question_answers=answers,
            calc=CalcResult(),
            semantic=semantic,
            terminates_later_stages=False,
            refuse_reason=reason,
        )

    calc = compute_stage3_metrics(periods_sorted)
    m = calc.metrics
    # Attach filing explanations to OCF–NI / CFS bridges (no arithmetic)
    if m.get("ocf_ni_bridges"):
        m["ocf_ni_bridges"] = [
            attach_bridge_semantic_explanations(b, semantic) for b in m["ocf_ni_bridges"]
        ]
        m["latest_ocf_ni_bridge"] = m["ocf_ni_bridges"][-1]
    if m.get("cfs_reconciliations"):
        m["cfs_reconciliations"] = [
            attach_bridge_semantic_explanations(b, semantic) for b in m["cfs_reconciliations"]
        ]
        m["latest_cfs_reconciliation"] = m["cfs_reconciliations"][-1]

    periods_used = [
        {"period_key": p.get("period_key", ""), "version_id": p.get("version_id", "")}
        for p in periods_sorted
    ]

    if not periods_sorted:
        gaps.append("No Normalized CURRENT periods available")
    if unresolved_major_conflict:
        gaps.append("Unresolved major Normalized conflict")
        carry.append("Unresolved Normalized conflict — cash figures may be unreliable")

    # --- S3-M1 OCF vs NI ---
    series = m.get("ocf_vs_ni_series") or []
    usable = [r for r in series if r.get("ocf") is not None and r.get("ni") is not None]
    if len(usable) >= 2:
        gaps_desc = "; ".join(
            f"{r['period_key']}: OCF {_fmt(r['ocf'])} vs NI {_fmt(r['ni'])} "
            f"(Δ {_fmt(r.get('ocf_minus_ni'))})"
            for r in usable
        )
        cum = m.get("cumulative_ocf_minus_ni")
        cfs = m.get("latest_cfs_reconciliation") or {}
        bridge = m.get("latest_ocf_ni_bridge") or {}
        cfs_bits = []
        for c in (cfs.get("components") or [])[:10]:
            cfs_bits.append(
                f"{c.get('bucket')}={_fmt(c.get('amount'))} ({c.get('nature')})"
            )
        cfs_status = cfs.get("status") or "UNRESOLVED"
        interp = ",".join(cfs.get("interpretation_categories") or [])
        bridge_summary = (
            f" Official CFS reconciliation: status={cfs_status}; "
            f"NI_cfs_basis={_fmt(cfs.get('net_income_cfs_basis'))} "
            f"({cfs.get('net_income_basis')}); "
            f"reconstructed_OCF={_fmt(cfs.get('reconstructed_ocf'))}; "
            f"residual={_fmt(cfs.get('unexplained_residual'))}; "
            f"components=[{'; '.join(cfs_bits)}]; interpretation={interp}; "
            f"semantic_hits={len(cfs.get('semantic_explanations') or [])}"
        )
        if cfs_status != "RECONCILED":
            # Legacy proxy context only when CFS not fully tied
            natures = ",".join(bridge.get("nature_tags") or [])
            bridge_summary += (
                f" Legacy proxy residual={_fmt(bridge.get('residual_after_proxy'))} "
                f"nature={natures}"
            )
        ans(
            "S3-M1",
            "answered",
            f"Multi-period OCF vs NI available ({len(usable)} periods). "
            f"Cumulative OCF−NI={_fmt(cum)}. {gaps_desc}.{bridge_summary}",
            [
                f"n_periods={len(usable)}",
                f"cumulative_ocf_to_ni={m.get('cumulative_ocf_to_ni')}",
                f"cfs_status={cfs_status}",
            ],
        )
        why.append(f"Multi-period earnings→cash: cumulative OCF−NI={_fmt(cum)} (descriptive)")
        why.append(
            f"Official CFS reconciliation: status={cfs_status}; "
            f"residual={_fmt(cfs.get('unexplained_residual'))}; "
            f"interpretation={interp or 'n/a'}"
        )
        if cfs_status == "RECONCILED":
            why.append(
                "OCF<NI alone is not a cash-quality concern — official CFS reconciles (residual 0)"
            )
        elif cfs.get("data_problems"):
            why.append(
                "CFS mapping/ingestion gaps classified as automation/data_problem "
                "(not automatic cash-quality concern)"
            )
    elif len(usable) == 1:
        ans(
            "S3-M1",
            "partial",
            f"Only one period with OCF+NI ({usable[0]['period_key']}) — multi-period thin",
            [],
        )
        gaps.append("S3-M1 single-period only")
    else:
        ans("S3-M1", "missing", "OCF and/or NI missing across periods", [])
        gaps.append("S3-M1 incomplete")

    # --- S3-M2 FCF ---
    latest_lin = m.get("latest_fcf_lineage") or {}
    if m.get("latest_capex_conflict"):
        ans(
            "S3-M2",
            "partial",
            f"CapEx conflict — FCF null. Reason: {latest_lin.get('reason')}",
            [str(latest_lin)],
        )
        gaps.append("S3-M2 CapEx conflict")
        carry.append(f"CapEx conflict — FCF untrustworthy: {latest_lin.get('reason')}")
        warnings.append("CapEx classification conflict — do not trust FCF until resolved")
    elif m.get("latest_fcf") is not None:
        trend = m.get("fcf_trend_direction")
        ans(
            "S3-M2",
            "answered",
            f"FCF={_fmt(m.get('latest_fcf'))} via OCF−CapEx "
            f"(OCF={_fmt(latest_lin.get('ocf'))}, CapEx={_fmt(latest_lin.get('capex'))}); "
            f"trend={trend}",
            [str(latest_lin)],
        )
        why.append(f"Latest FCF (OCF−CapEx)={_fmt(m.get('latest_fcf'))}; trend={trend}")
    else:
        ans(
            "S3-M2",
            "missing",
            calc.null_reasons.get(
                f"fcf:{m.get('latest_period_key')}", "FCF not computable"
            ),
            [],
        )
        gaps.append("S3-M2 FCF incomplete")

    # --- S3-M3 Owner earnings / maintenance ---
    maint = semantic.maintenance_capex_status
    if maint == "DISCLOSED_WITH_EVIDENCE" and semantic.maintenance_capex_evidence:
        ans(
            "S3-M3",
            "answered",
            f"Maintenance CapEx DISCLOSED_WITH_EVIDENCE: {semantic.maintenance_capex_evidence}"
            + (
                f" (amount={_fmt(semantic.maintenance_capex_amount)})"
                if semantic.maintenance_capex_amount is not None
                else " (qualitative; amount not taken as invented)"
            ),
            [semantic.maintenance_capex_evidence],
        )
    else:
        ans(
            "S3-M3",
            "answered",
            "Owner-earnings posture: maintenance CapEx UNKNOWN — refuse false precision "
            "(no mechanical D&A=maintenance)",
            ["maintenance_capex_status=UNKNOWN"],
        )
        why.append("Maintenance CapEx UNKNOWN — no false OE precision")

    # --- S3-M4 WC ---
    wc = m.get("wc_deltas") or []
    cfs = m.get("latest_cfs_reconciliation") or {}
    cfs_wc = (cfs.get("buckets") or {}).get("net_change_in_operating_assets_liabilities")
    if wc:
        last = wc[-1]
        parts = [
            f"ΔAR={_fmt(last.get('delta_receivables'))}",
            f"ΔInv={_fmt(last.get('delta_inventory'))}",
            f"ΔAP={_fmt(last.get('delta_accounts_payable'))}",
            f"ΔDR={_fmt(last.get('delta_deferred_revenue_total'))}",
            f"ΔRev={_fmt(last.get('delta_revenue'))}",
        ]
        if cfs_wc is not None:
            parts.append(f"CFS_net_change_op_assets_liab={_fmt(cfs_wc)}")
        for sub in cfs.get("wc_subcomponents") or []:
            parts.append(f"CF_{sub.get('label')}={_fmt(sub.get('amount_raw_xbrl'))}")
        missing_ap = last.get("delta_accounts_payable") is None
        status = "partial" if missing_ap and cfs_wc is None else "answered"
        summary = (
            "WC deltas (converter/sponge/trap is model-aware judgment): " + "; ".join(parts)
        )
        if missing_ap:
            summary += " — accounts_payable null (AP leg incomplete)"
            if cfs_wc is None:
                gaps.append("S3-M4 accounts_payable null")
        ans("S3-M4", status, summary, parts)
    else:
        ans("S3-M4", "partial", calc.null_reasons.get("wc_deltas", "WC deltas unavailable"), [])
        gaps.append("S3-M4 WC incomplete")

    # --- S3-M5 Distortions ---
    distortion_bits: list[str] = []
    for r in m.get("acquisitions_cash_series") or []:
        if r.get("amount") is not None:
            distortion_bits.append(f"acquisitions_cash {r['period_key']}={_fmt(r['amount'])}")
    for r in m.get("asset_sales_series") or []:
        if r.get("amount") is not None:
            distortion_bits.append(f"asset_sales {r['period_key']}={_fmt(r['amount'])}")
    if m.get("sbc_context", {}).get("sbc_expense") is not None:
        distortion_bits.append(f"SBC={_fmt(m['sbc_context']['sbc_expense'])} (optics context)")
    for fnd in semantic.findings:
        if fnd.escalate_to_human or fnd.materiality_judgment in {"material", "unclear"}:
            distortion_bits.append(
                f"semantic:{fnd.topic} judgment={fnd.materiality_judgment} "
                f"escalate={fnd.escalate_to_human}"
            )
            if fnd.escalate_to_human:
                warnings.append(
                    f"{fnd.topic}: {fnd.materiality_reason} (cite={fnd.citation})"
                )
                if fnd.materiality_judgment == "material":
                    carry.append(f"Material cash distortion concern: {fnd.topic} — {fnd.materiality_reason}")
    for note_attr, label in (
        ("factoring_or_supplier_finance_notes", "factoring/supplier finance"),
        ("acquisitions_notes", "acquisitions"),
        ("asset_sales_notes", "asset sales"),
        ("restructuring_notes", "restructuring"),
        ("capitalized_costs_notes", "capitalized costs"),
        ("unusual_cash_notes", "unusual cash"),
        ("wc_distortion_notes", "WC distortion"),
    ):
        val = getattr(semantic, note_attr, None)
        if val:
            distortion_bits.append(f"{label}: {val}")
            warnings.append(f"{label}: {val}")

    if distortion_bits:
        has_amt = any(
            r.get("amount") is not None
            for r in list(m.get("acquisitions_cash_series") or [])
            + list(m.get("asset_sales_series") or [])
        )
        ans(
            "S3-M5",
            "answered" if (semantic.filled or has_amt) else "partial",
            "Distortion scan: " + "; ".join(distortion_bits[:12]),
            distortion_bits[:12],
        )
    else:
        ans(
            "S3-M5",
            "partial" if not semantic.filled else "answered",
            "No Normalized acquisition/asset-sale amounts and no semantic distortion hits "
            "(materiality-triggered warnings only — not universal KPIs)",
            [],
        )
        if not semantic.filled:
            gaps.append("S3-M5 semantic pending")

    # --- S3-M6 Thesis coherence ---
    if thesis_summary:
        ans(
            "S3-M6",
            "partial",
            f"Cash evidence available for thesis check; human coherence vs Gate 1–2. "
            f"Thesis snippet: {thesis_summary[:240]}",
            ["human judgment — no auto falsify threshold"],
        )
    else:
        ans(
            "S3-M6",
            "partial",
            "Thesis summary not supplied — cash pack ready; coherence judgment pending human",
            [],
        )
        gaps.append("S3-M6 thesis link pending")

    # --- S3-M7 Sustainability ---
    sust_bits = [
        f"fcf_trend={m.get('fcf_trend_direction')}",
        f"capex_trend={m.get('capex_trend_direction')}",
        f"capex/DA={m.get('latest_capex_to_da')}",
        m.get("prefer_ge_3_fy_note") or "",
    ]
    if m.get("latest_capex_conflict"):
        sust_bits.append("CapEx conflict undermines sustainability read")
    ans(
        "S3-M7",
        "partial",
        "Sustainability context (descriptive): " + "; ".join(x for x in sust_bits if x),
        sust_bits,
    )
    why.append(
        f"CapEx trend={m.get('capex_trend_direction')}; "
        "sustainability is judgment — watch CapEx holiday / WC release / one-timers"
    )

    # SHOULD
    for qid, qtext in SHOULD_QUESTIONS:
        note = None
        status = "partial"
        if qid == "S3-S3":
            latest = (m.get("per_period") or [{}])[-1] if m.get("per_period") else {}
            if latest.get("deferred_revenue_current") is not None or latest.get(
                "deferred_revenue_noncurrent"
            ) is not None:
                note = (
                    f"Deferred rev current={_fmt(latest.get('deferred_revenue_current'))}; "
                    f"noncurrent={_fmt(latest.get('deferred_revenue_noncurrent'))}"
                )
                status = "answered"
            else:
                note = "Deferred revenue fields null in Normalized"
        elif qid == "S3-S5":
            note = (
                "Controllable levers (defer CapEx / cut buybacks-dividends) are Stage 2 bridge — "
                "not valued here"
            )
            status = "partial"
        else:
            note = "Not assessed in dry-run / heuristic path (SHOULD gap = monitor, not kill)"
        answers.append(
            QuestionAnswer(
                question_id=qid,
                question=qtext,
                status=status,  # type: ignore[arg-type]
                answer_summary=note or "",
                evidence=[],
                must=False,
            )
        )

    # --- Process outcome (no mechanical later-stage kill) ---
    process_outcome: Stage3ProcessOutcome
    must_missing = [a for a in answers if a.must and a.status == "missing"]
    material_escalations = [
        f for f in semantic.findings if f.escalate_to_human and f.materiality_judgment == "material"
    ]
    serious = bool(material_escalations) or m.get("latest_capex_conflict")
    cfs_latest = m.get("latest_cfs_reconciliation") or {}
    if cfs_latest.get("status") == "PARTIALLY_RECONCILED":
        monitors_note = (
            "CFS PARTIALLY_RECONCILED — treat residual as automation/data_problem until mapping completes; "
            "not automatic cash-quality concern"
        )
        if monitors_note not in gaps:
            gaps.append(monitors_note)
    # RECONCILED residual must NOT become a cash-quality carry-forward

    if not periods_sorted:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — no Normalized periods"]
        carry.append("Stage 3 TOO_HARD: no periods")
    elif unresolved_major_conflict and not usable:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — conflict and missing cash spine"]
    elif serious or (must_missing and any(a.question_id in {"S3-M1", "S3-M2"} for a in must_missing)):
        process_outcome = "REVIEW_REQUIRED"
        if serious:
            why.append("Material/ambiguous cash-generation issues require human review")
        if must_missing:
            why.append(f"Key MUST incomplete: {[a.question_id for a in must_missing]}")
        for f in material_escalations:
            carry.append(f"REVIEW: {f.topic} — {f.materiality_reason}")
    elif gaps or not semantic.filled or any(a.status == "partial" for a in answers if a.must):
        process_outcome = "CONDITIONAL"
        why.append("Continue with monitors — gaps or partial MUST answers remain")
        for g in gaps:
            if g not in carry:
                carry.append(f"Monitor/gap: {g}")
    else:
        process_outcome = "PROCEED"
        why.append("MUST answered honestly; cash pack coherent enough to continue with evidence")

    assert process_outcome in STAGE3_OUTCOMES

    # S3-M8
    ans(
        "S3-M8",
        "answered",
        f"process_outcome={process_outcome}; carry_forward={len(carry)} items; "
        "Stage 3 does not alone mechanically terminate later stages",
        [process_outcome, f"terminates_later_stages=False"],
    )

    # Evidence sections for report template
    cash_conv = [
        f"OCF vs NI series: {m.get('ocf_vs_ni_series')}",
        f"Latest FCF={_fmt(m.get('latest_fcf'))} lineage={m.get('latest_fcf_lineage')}",
        f"Owner-earnings: maintenance CapEx={semantic.maintenance_capex_status}",
        f"Cumulative OCF−NI={_fmt(m.get('cumulative_ocf_minus_ni'))}; "
        f"cumulative FCF−NI={_fmt(m.get('cumulative_fcf_minus_ni'))}",
        f"FCF trend={m.get('fcf_trend_direction')}",
        f"Latest OCF−NI bridge: {m.get('latest_ocf_ni_bridge')}",
        f"Official CFS reconciliation: {m.get('latest_cfs_reconciliation')}",
    ]
    wc_bullets = []
    for d in wc[-2:] if wc else []:
        wc_bullets.append(
            f"{d.get('from_period')}→{d.get('to_period')}: "
            f"ΔAR={_fmt(d.get('delta_receivables'))}, "
            f"ΔInv={_fmt(d.get('delta_inventory'))}, "
            f"ΔAP={_fmt(d.get('delta_accounts_payable'))}, "
            f"ΔDR={_fmt(d.get('delta_deferred_revenue_total'))}"
        )
    if not wc_bullets:
        wc_bullets.append("WC deltas unavailable or single period")

    capex_bullets = [
        f"Reported CapEx latest={_fmt(m.get('latest_capex'))}",
        f"CapEx/D&A={m.get('latest_capex_to_da')}",
        f"CapEx trend={m.get('capex_trend_direction')} (delta={_fmt(m.get('capex_trend_delta'))})",
        f"Maintenance CapEx: {semantic.maintenance_capex_status}"
        + (
            f" — {semantic.maintenance_capex_evidence}"
            if semantic.maintenance_capex_status == "DISCLOSED_WITH_EVIDENCE"
            else " (UNKNOWN unless disclosed evidence)"
        ),
        "Returns on reinvestment → Stage 6 (do not judge ROIC here)",
    ]
    if m.get("latest_capex_conflict"):
        capex_bullets.append(f"CapEx conflict: {latest_lin.get('reason')}")

    strong = []
    if m.get("latest_fcf") is not None and (m.get("latest_fcf") or 0) > 0:
        strong.append("Latest calculated FCF positive (descriptive — not a pass bar)")
    if len(usable) >= 2:
        strong.append("Multi-period OCF/NI series present")
    if semantic.maintenance_capex_status == "UNKNOWN":
        strong.append("Honest UNKNOWN maintenance CapEx (no false OE precision)")

    breaks = [
        "Persistent earnings without cash and no credible model reason",
        "CapEx holiday or WC release mistaken for franchise cash power",
        "Hidden factoring / supplier finance / roll-up optics",
        "Cash reality that strains or falsifies the Gate 2 engine",
    ]

    monitors = []
    if semantic.maintenance_capex_status == "UNKNOWN":
        monitors.append("Watch for any note disclosure of maintenance vs growth CapEx")
    if any(
        (r.get("delta_accounts_payable") is None)
        for r in wc
    ) or not wc:
        monitors.append("Obtain clean accounts_payable (and deferred revenue if prepaid model)")
    if not semantic.filled:
        monitors.append("Complete Notes/MD&A cash-generation semantic review")
    if m.get("n_periods", 0) < 3:
        monitors.append("Prefer ≥3 FY when available (operational — not a fail bar)")
    for g in gaps:
        if g not in monitors:
            monitors.append(g)

    missing = list(gaps)
    for k, v in list(calc.null_reasons.items())[:20]:
        missing.append(f"calc null: {k}: {v}")

    return Stage3Report(
        ticker=ticker,
        date=utc_now(),
        periods_used=periods_used,
        sources=sources,
        process_outcome=process_outcome,
        why_bullets=why[:8],
        carry_forward_concerns=carry,
        cash_conversion_bullets=cash_conv,
        working_capital_bullets=wc_bullets,
        capex_bullets=capex_bullets,
        cash_quality_warnings=warnings,
        what_is_strong=strong,
        what_can_break=breaks,
        monitors=monitors,
        missing_ambiguous=missing,
        question_answers=answers,
        calc=calc,
        semantic=semantic,
        terminates_later_stages=False,
        refuse_reason=None,
    )
