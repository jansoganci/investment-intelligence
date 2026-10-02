"""Stage 6 question spine → evidence pack + process outcome.

Outcomes ONLY: PROCEED | CONDITIONAL | REVIEW_REQUIRED | TOO_HARD.
No mechanical label-count → outcome. No numeric ROIC/ROIIC/WACC bands. No colors.
Stage 6 does NOT mechanically terminate later stages. IOM ≠ ROIIC.
D10 may elevate REVIEW_REQUIRED + S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ids import utc_now
from ..models import (
    ArchetypeAdaptation,
    CalcResult,
    DualROICView,
    IncrementalROICWindow,
    QuestionAnswer,
    Stage6ProcessOutcome,
    Stage6Report,
    Stage6SemanticReview,
)
from .archetype import adapt_from_stage4, dual_view_mandatory_for
from .benchmark import assess_runway, label_benchmarks, _tag_false_positives
from .calc import compute_stage6_metrics
from .questions import MUST_QUESTIONS, SHOULD_QUESTIONS, STAGE6_OUTCOMES, STAGE7_HANDOFF_FLAGS
from .semantic import (
    load_stage6_semantic_from_fixture,
    placeholder_stage6_semantic,
    semantic_text_blob,
)


def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        fv = float(v)
        if abs(fv) < 1:
            return f"{fv:.4f}"
        if abs(fv) < 100:
            return f"{fv:.2f}"
        return f"{fv:,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _must_map() -> dict[str, str]:
    return {qid: q for qid, q in MUST_QUESTIONS}


def _thesis_coherence_capital(
    thesis_summary: str | None,
    thesis_capital: str | None,
    archetype: ArchetypeAdaptation | None,
    calc_metrics: dict[str, Any],
) -> str:
    """Heuristic supports/strains/falsifies on capital destination — no auto kill."""
    if not thesis_summary and not thesis_capital:
        return "unknown"
    if archetype and archetype.classification_path == "REVIEW_REQUIRED":
        return "strains"
    blob = f"{thesis_summary or ''} {thesis_capital or ''}".lower()
    dual = calc_metrics.get("dual_roic") or {}
    conflict = any(
        tok in blob
        for tok in (
            "capital destroyed",
            "value destructive reinvestment",
            "no reinvestment capacity ever",
            "thesis broken",
        )
    )
    if conflict:
        return "falsifies"
    if dual.get("roic_inclusive") is not None and "reinvest" in blob:
        return "supports"
    if thesis_summary:
        return "supports"
    return "unknown"


def _d10_persistent_destruction(
    windows: list[dict[str, Any]],
    *,
    semantic: Stage6SemanticReview | None,
    fp_tags: list[dict[str, Any]],
) -> bool:
    """
    Qualitative D10 path — no numeric ROIC/WACC threshold.
    Elevate when primary multi-year incremental is negative with material positive ΔIC
    AND not clearly investment-phase (FP-R12).
    """
    primary = next((w for w in windows if w.get("window_id") == "cumulative_3y"), None)
    if primary is None:
        return False
    if primary.get("meaning_class") in {"not_meaningful", "unknown"}:
        return False
    roiic = primary.get("incremental_roic")
    delta_ic = primary.get("delta_ic")
    if roiic is None or delta_ic is None:
        return False
    # Large capital deployed (positive ΔIC) with negative incremental returns
    if delta_ic > 0 and roiic < 0:
        # Investment-phase counterexample
        if semantic and semantic.investment_phase_notes:
            return False
        if any(t.get("id") == "FP-R12" for t in fp_tags):
            return False
        return True
    return False


def evaluate_stage6(
    ticker: str,
    periods: list[dict[str, Any]],
    *,
    gate0_class: str = "operating",
    sources: list[str] | None = None,
    semantic: Stage6SemanticReview | None = None,
    semantic_notes_path: Path | None = None,
    thesis_summary: str | None = None,
    thesis_capital: str | None = None,
    business_notes: str | None = None,
    stage4_archetype: dict[str, Any] | ArchetypeAdaptation | None = None,
    unresolved_major_conflict: bool = False,
    extend_full_cycle: bool = False,
    peer_notes: str | None = None,
    force_primary: str | None = None,
) -> Stage6Report:
    """
    Evaluate Stage 6 ROIC / Reinvestment.
    FI / non-operating Gate 0 → TOO_HARD refuse.
    terminates_later_stages always False. No Stage 7 conclusions.
    """
    ticker = ticker.upper()
    sources = sources or []
    must_q = _must_map()

    if semantic is None:
        if semantic_notes_path:
            semantic = load_stage6_semantic_from_fixture(semantic_notes_path)
        else:
            semantic = placeholder_stage6_semantic()

    periods_sorted = sorted(
        periods,
        key=lambda d: (0 if d.get("period_type") == "FY" else 1, d.get("period_key") or ""),
    )

    carry: list[str] = []
    gaps: list[str] = []
    why: list[str] = []
    answers: list[QuestionAnswer] = []
    monitors: list[str] = []
    s7_flags: list[str] = []

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

    if gate0_class != "operating":
        reason = (
            f"Gate 0 class is '{gate0_class}' — Financial Institutions / non-operating "
            "are HARD OUT OF SCOPE for Stage 6 OpCo ROIC logic; refuse"
        )
        for qid in [f"S6-M{i}" for i in range(1, 8)]:
            ans(qid, "blocked", reason, [])
        ans("S6-M8", "answered", f"process_outcome=TOO_HARD; {reason}", ["TOO_HARD"])
        for qid, qtext in SHOULD_QUESTIONS:
            answers.append(
                QuestionAnswer(
                    question_id=qid,
                    question=qtext,
                    status="blocked",
                    answer_summary="Stage 6 refused — Gate 0 ≠ operating",
                    evidence=[],
                    must=False,
                )
            )
        return Stage6Report(
            ticker=ticker,
            date=utc_now(),
            periods_used=[],
            sources=sources,
            process_outcome="TOO_HARD",
            why_bullets=[reason],
            carry_forward_concerns=[reason],
            dual_roic_bullets=[],
            incremental_roic_bullets=[],
            reinvestment_composition_bullets=[],
            runway_bullets=[],
            capex_productivity_bullets=[],
            wc_mechanism_bullets=[],
            false_positive_tags=[],
            benchmark_results=[],
            archetype=None,
            dual_roic=None,
            incremental_roic_windows=[],
            runway_label="not_applicable",
            stage7_handoff_flags=[],
            what_is_strong=[],
            what_can_break=[],
            monitors=[],
            missing_ambiguous=[reason],
            question_answers=answers,
            calc=CalcResult(),
            semantic=semantic,
            terminates_later_stages=False,
            refuse_reason=reason,
            thesis_coherence="unknown",
        )

    # Provisional archetype for dual-mandatory before calc
    sem_blob_pre = semantic_text_blob(semantic)
    archetype_pre = adapt_from_stage4(
        stage4_archetype,
        thesis_summary=thesis_summary,
        business_notes=business_notes,
        semantic_text=sem_blob_pre,
        force_primary=force_primary,
    )
    dual_mandatory = dual_view_mandatory_for(
        archetype_pre.primary_archetype, archetype_pre.secondary_traits
    )
    semantic_distortion = bool(
        semantic
        and (
            semantic.distortion_notes
            or semantic.impairment_notes
            or semantic.lease_accounting_notes
            or any(
                f.topic in {"accounting_distortion", "impairment", "lease_asc842"}
                for f in semantic.findings
            )
        )
    )

    sem_blob_c1 = semantic_text_blob(semantic) if semantic is not None else ""
    calc = compute_stage6_metrics(
        periods_sorted,
        extend_full_cycle=extend_full_cycle,
        dual_view_mandatory=dual_mandatory,
        semantic_distortion=semantic_distortion,
        semantic_texts=[sem_blob_c1] if sem_blob_c1 else None,
    )
    m = calc.metrics
    periods_used = [
        {"period_key": p.get("period_key") or "", "version_id": p.get("version_id") or ""}
        for p in periods_sorted
        if p.get("period_type") == "FY"
    ][-5:]

    archetype = adapt_from_stage4(
        stage4_archetype,
        thesis_summary=thesis_summary,
        business_notes=business_notes,
        semantic_text=sem_blob_pre,
        calc_hints=m,
        force_primary=force_primary,
    )

    thesis_coh = _thesis_coherence_capital(
        thesis_summary, thesis_capital, archetype, m
    )
    fp_tags = _tag_false_positives(
        calc_metrics=m, semantic=semantic, archetype=archetype
    )
    runway_label, runway_why = assess_runway(
        semantic=semantic, archetype=archetype, calc_metrics=m
    )
    bench = label_benchmarks(
        calc_metrics=m,
        archetype=archetype,
        semantic=semantic,
        fp_tags=fp_tags,
        thesis_coherence=thesis_coh,
        runway_label=runway_label,
        peer_notes=peer_notes,
    )

    dual_raw = m.get("dual_roic") or {}
    windows_raw = m.get("incremental_roic_windows") or []
    reinv = m.get("reinvestment_composition") or {}
    wc = m.get("wc_metrics") or {}
    latest = m.get("latest_capital") or {}

    # Sync maint status from semantic
    if semantic and semantic.maint_capex_status:
        reinv["maint_capex_status"] = semantic.maint_capex_status
        reinv["maint_growth_split"] = (
            "disclosed_partial"
            if semantic.maint_capex_status == "DISCLOSED_WITH_EVIDENCE"
            else "UNKNOWN"
        )

    # --- S6-M1 Dual ROIC ---
    if dual_raw.get("roic_inclusive") is not None or dual_raw.get("nopat") is not None:
        ans(
            "S6-M1",
            "answered",
            (
                f"Inclusive ROIC={_fmt(dual_raw.get('roic_inclusive'))}; "
                f"tangible={_fmt(dual_raw.get('roic_tangible'))}; "
                f"NOPAT={_fmt(dual_raw.get('nopat'))} "
                f"(tax_source={dual_raw.get('tax_rate_source')}); "
                f"avg_IC_method={dual_raw.get('average_ic_method')}; "
                f"dual_emitted={dual_raw.get('dual_view_emitted')}; "
                f"mandatory={dual_raw.get('dual_view_mandatory')}; "
                f"nibol_incomplete={dual_raw.get('nibol_incomplete')}"
            ),
            [str(dual_raw.get("definition_labels"))],
        )
        why.append(
            f"ROIC inclusive={_fmt(dual_raw.get('roic_inclusive'))} "
            f"(descriptive; no universal hurdle); dual={dual_raw.get('dual_view_emitted')}"
        )
    elif m.get("n_fy", 0) == 0:
        ans("S6-M1", "missing", "No FY periods with capital inputs", [])
        gaps.append("S6-M1 no FY capital spine")
    else:
        ans(
            "S6-M1",
            "partial",
            f"FY present (n_fy={m.get('n_fy')}) but ROIC incomplete",
            [str(calc.null_reasons)],
        )
        gaps.append("S6-M1 ROIC incomplete")

    # --- S6-M2 Incremental ---
    ans(
        "S6-M2",
        "answered" if windows_raw else "partial",
        (
            f"Incremental ROIC windows={len(windows_raw)}; "
            f"classes={[w.get('meaning_class') for w in windows_raw]}; "
            "descriptive only — no numeric ROIIC hurdle; ≠ Stage 5 IOM"
        ),
        [str(w)[:200] for w in windows_raw[:3]] or ["insufficient periods"],
    )

    # --- S6-M3 Reinvestment + runway ---
    ans(
        "S6-M3",
        "answered",
        (
            f"Composition: capex={_fmt(reinv.get('organic_capex'))}; "
            f"acq={_fmt(reinv.get('business_acquisitions_cash'))}; "
            f"div={_fmt(reinv.get('dividends_paid'))}; "
            f"buybacks={_fmt(reinv.get('share_repurchases'))}; "
            f"maint_split={reinv.get('maint_growth_split')}; "
            f"runway={runway_label}"
        ),
        runway_why,
    )
    why.append(f"Runway label={runway_label} (evidence, not outcome)")

    # --- S6-M4 CapEx / WC ---
    ans(
        "S6-M4",
        "partial"
        if latest.get("capex") is None and wc.get("latest_wc_proxy") is None
        else "answered",
        (
            f"CapEx={_fmt(latest.get('capex'))}; CapEx/D&A={_fmt(latest.get('capex_to_da'))}; "
            f"maint_status={reinv.get('maint_capex_status')}; "
            f"WC_proxy={_fmt(wc.get('latest_wc_proxy'))}; "
            "evidence notes only — no scores; no forced maint CapEx"
        ),
        [],
    )
    if reinv.get("maint_capex_status") in {"UNKNOWN", "NOT_DISCLOSED"}:
        monitors.append("Maint CapEx UNKNOWN — not disclosed; no forced invention")

    # --- S6-M5 FP ---
    ans(
        "S6-M5",
        "answered",
        f"FP-R tags={[t['id'] for t in fp_tags]} (evidence, not auto-fail; no FP score)",
        [t.get("why", "") for t in fp_tags[:5]],
    )

    # --- S6-M6 RC ---
    ans(
        "S6-M6",
        "answered",
        f"RC labels={{ {', '.join(f'{b.dimension_id}={b.label}' for b in bench)} }} — Benchmark ≠ hard gate",
        [f"{b.dimension_id}:{b.why[:120]}" for b in bench[:4]],
    )

    # --- S6-M7 Thesis ---
    ans(
        "S6-M7",
        "partial" if thesis_coh == "unknown" else "answered",
        (
            f"Thesis capital coherence={thesis_coh}; PRIMARY={archetype.primary_archetype}; "
            f"snippet={(thesis_summary or thesis_capital or '')[:200]}"
        ),
        [archetype.why],
    )
    if thesis_coh in {"strains", "falsifies"}:
        carry.append(f"Thesis capital coherence={thesis_coh}")
        s7_flags.append("S6_H7_THESIS_CAPITAL_DESTINATION_TENSION")

    # SHOULD
    for qid, qtext in SHOULD_QUESTIONS:
        status = "partial"
        note = "SHOULD gap = monitor, not kill"
        if qid == "S6-S1":
            flag = dual_raw.get("financing_check_flag")
            note = (
                f"Financing-check gap={_fmt(dual_raw.get('financing_check_gap'))}; "
                f"flag={flag}"
            )
            status = "answered" if flag is not None else "partial"
            if flag == "SOURCE_CONFLICT":
                carry.append("IC financing-check SOURCE_CONFLICT — escalate")
                monitors.append("Resolve IC financing-check gap before trusting ROIC level")
        elif qid == "S6-S2":
            if semantic and semantic.lease_accounting_notes:
                note = f"Lease/ASC842: {semantic.lease_accounting_notes[:200]}"
                status = "answered"
            else:
                note = "No ASC 842 splice notes — monitor if lease adoption year in window"
        elif qid == "S6-S3":
            # Dual-view conflict handoff whenever both views emitted with material spread
            # (not A7-only) — prevents hiding ex-GW optics on capital-light / network names.
            if dual_raw.get("dual_view_emitted") and (
                dual_raw.get("roic_inclusive") is not None
                and dual_raw.get("roic_tangible") is not None
            ):
                ri, rt = dual_raw["roic_inclusive"], dual_raw["roic_tangible"]
                if rt > 0 and ri < 0.5 * rt:
                    s7_flags.append("S6_H7_DUAL_VIEW_CONFLICT")
                    if (
                        archetype.primary_archetype == "A7"
                        or dual_raw.get("dual_view_mandatory")
                    ):
                        s7_flags.append("S6_H7_ACQ_RETURN_OPACITY")
            if archetype.primary_archetype == "A7" or dual_raw.get("dual_view_mandatory"):
                note = (
                    f"A7 dual spine: inclusive={_fmt(dual_raw.get('roic_inclusive'))}; "
                    f"tangible={_fmt(dual_raw.get('roic_tangible'))}; "
                    "tangible ≠ M&A success"
                )
                status = "answered"
            else:
                note = "Non-A7 — dual view only if GW/intangibles material"
                status = "answered"
        elif qid == "S6-S4":
            note = (
                f"Distributions separate: div={_fmt(reinv.get('dividends_paid'))}; "
                f"buybacks={_fmt(reinv.get('share_repurchases'))}"
            )
            status = (
                "answered"
                if reinv.get("dividends_paid") is not None
                or reinv.get("share_repurchases") is not None
                else "partial"
            )
        elif qid == "S6-S5":
            note = (
                f"Investment-phase notes={bool(semantic and semantic.investment_phase_notes)}; "
                "D10 path uses qualitative multi-year incremental + capital deployed"
            )
            status = "answered"
        answers.append(
            QuestionAnswer(
                question_id=qid,
                question=qtext,
                status=status,  # type: ignore[arg-type]
                answer_summary=note,
                evidence=[],
                must=False,
            )
        )

    # CapEx opacity handoff
    if latest.get("capex") is None and not (
        semantic and (semantic.maint_growth_capex_notes or any(
            f.topic == "capex_productivity" for f in semantic.findings
        ))
    ):
        if archetype.primary_archetype in {"A4", "A5", "A8", "A9"}:
            s7_flags.append("S6_H7_CAPEX_PRODUCTIVITY_OPAQUE")

    if not semantic.filled:
        s7_flags.append("S6_H7_DISCLOSURE_QUALITY_CAPITAL")

    # D10 path
    d10 = _d10_persistent_destruction(windows_raw, semantic=semantic, fp_tags=fp_tags)
    if d10:
        s7_flags.append("S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST")
        carry.append(
            "D10: multi-year incremental negative with material capital deployed — "
            "REVIEW_REQUIRED + Stage 7 flag (no numeric threshold; non-terminating)"
        )

    # Deduplicate flags; only emit known catalogue
    s7_flags = [f for f in dict.fromkeys(s7_flags) if f in STAGE7_HANDOFF_FLAGS]

    # --- Process outcome ---
    process_outcome: Stage6ProcessOutcome
    material_fps = [t for t in fp_tags if t.get("severity") == "material"]
    material_escalations = [
        f
        for f in semantic.findings
        if f.escalate_to_human and f.materiality_judgment == "material"
    ]
    usable = [
        p
        for p in periods_sorted
        if (p.get("fields") or {}).get("operating_income") is not None
        and (p.get("fields") or {}).get("total_assets") is not None
    ]

    if not periods_sorted or not usable:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — no Normalized OP + total_assets spine"]
        carry.append("Stage 6 TOO_HARD: no capital spine")
    elif unresolved_major_conflict and not usable:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — conflict and missing capital spine"]
    elif d10 or thesis_coh == "falsifies" or (
        archetype.classification_path == "REVIEW_REQUIRED"
        and archetype.confidence in {"LOW", "UNKNOWN"}
    ):
        process_outcome = "REVIEW_REQUIRED"
        why.append(
            "D10 elevation and/or thesis falsification / archetype ambiguity — "
            "carry-forward REVIEW (non-terminating)"
        )
    elif material_fps or material_escalations or thesis_coh == "strains" or (
        "S6_H7_DUAL_VIEW_CONFLICT" in s7_flags
    ):
        process_outcome = "REVIEW_REQUIRED"
        why.append(
            "Material FP / dual-view conflict / semantic escalation / thesis strain — "
            "human exception queue (labels are evidence; not a count formula)"
        )
        for t in material_fps:
            carry.append(f"FP {t['id']}: {t.get('why')}")
    elif gaps or not semantic.filled or any(
        a.status == "partial" for a in answers if a.must and a.question_id != "S6-M8"
    ):
        process_outcome = "CONDITIONAL"
        why.append("Usable package with named monitors — gaps or partial MUST remain")
        for g in gaps:
            monitors.append(g)
            if g not in carry:
                carry.append(f"Monitor/gap: {g}")
    else:
        process_outcome = "PROCEED"
        why.append(
            "MUST answered honestly; capital pack coherent; no material unresolved FP; "
            "continue with evidence (Stage 6 non-terminating by default)"
        )

    assert process_outcome in STAGE6_OUTCOMES

    ans(
        "S6-M8",
        "answered",
        (
            f"process_outcome={process_outcome}; carry_forward={len(carry)} items; "
            f"S6_H7={s7_flags}; d10_elevated={d10}; "
            "Stage 6 does not alone mechanically terminate later stages; "
            "no label-count→outcome; no numeric ROIC/ROIIC/WACC bands"
        ),
        [process_outcome, "terminates_later_stages=False"],
    )

    # Dashboard bullets
    dual_bullets = [
        f"PRIMARY inclusive ROIC={_fmt(dual_raw.get('roic_inclusive'))}",
        f"Companion tangible ROIC={_fmt(dual_raw.get('roic_tangible'))}",
        f"NOPAT={_fmt(dual_raw.get('nopat'))}; tax_rate={_fmt(dual_raw.get('tax_rate'))} "
        f"(source={dual_raw.get('tax_rate_source')})",
        f"IC inclusive={_fmt(dual_raw.get('ic_inclusive'))}; "
        f"IC tangible={_fmt(dual_raw.get('ic_tangible'))}; "
        f"avg method={dual_raw.get('average_ic_method')}",
        f"GW={_fmt(dual_raw.get('goodwill'))}; intangibles={_fmt(dual_raw.get('intangibles'))}",
        f"dual_emitted={dual_raw.get('dual_view_emitted')}; "
        f"mandatory={dual_raw.get('dual_view_mandatory')}; "
        f"tangible≠M&A success={dual_raw.get('tangible_ne_ma_success')}",
        f"nibol_incomplete={dual_raw.get('nibol_incomplete')}; "
        f"financing_flag={dual_raw.get('financing_check_flag')}",
        f"defs={dual_raw.get('definition_labels')}",
    ]
    incr_bullets = []
    for w in windows_raw:
        incr_bullets.append(
            f"{w.get('window_id')}: ROIIC={_fmt(w.get('incremental_roic'))}; "
            f"class={w.get('meaning_class')}; ΔNOPAT={_fmt(w.get('delta_nopat'))}; "
            f"ΔIC={_fmt(w.get('delta_ic'))}; cause={w.get('cause_tag')}; "
            f"flags={w.get('honesty_flags')}"
        )
    if not incr_bullets:
        incr_bullets.append("No incremental ROIC window — UNKNOWN / insufficient periods")

    reinv_bullets = [
        f"organic_capex={_fmt(reinv.get('organic_capex'))}",
        f"maint/growth split={reinv.get('maint_growth_split')} "
        f"(status={reinv.get('maint_capex_status')})",
        f"WC Δ={_fmt(reinv.get('wc_delta'))}",
        f"acquisitions_cash={_fmt(reinv.get('business_acquisitions_cash'))}",
        f"dividends={_fmt(reinv.get('dividends_paid'))} (separate)",
        f"buybacks={_fmt(reinv.get('share_repurchases'))} (separate)",
        reinv.get("note") or "",
    ]
    runway_bullets = [
        f"runway_label={runway_label}",
        *runway_why,
        f"semantic runway: {(semantic.runway_notes or '')[:200] if semantic else ''}",
    ]
    capex_bullets = [
        f"CapEx={_fmt(latest.get('capex'))}; D&A={_fmt(latest.get('depreciation_amortization'))}; "
        f"CapEx/D&A={_fmt(latest.get('capex_to_da'))}",
        "Evidence notes only — not a CapEx productivity score; not CapEx/sales tile",
    ]
    if semantic and semantic.maint_growth_capex_notes:
        capex_bullets.append(f"Semantic CapEx: {semantic.maint_growth_capex_notes[:240]}")
    wc_bullets = [
        f"WC proxy={_fmt(wc.get('latest_wc_proxy'))}; ΔWC={_fmt(wc.get('delta_wc'))}",
        f"deferred_rev_current={_fmt(wc.get('deferred_revenue_current'))}",
        wc.get("note") or "Never auto-reward negative WC = good",
    ]

    strong = []
    if dual_raw.get("dual_view_emitted"):
        strong.append("Dual ROIC view emitted (inclusive primary + tangible companion)")
    if m.get("n_fy", 0) >= 3:
        strong.append("Multi-period capital exhibit present (≥3 FY)")
    if semantic.filled:
        strong.append("Filing-backed capital semantic filled")
    if archetype.classification_path == "AUTOMATED":
        strong.append(f"Archetype automated/reused: {archetype.primary_archetype}")

    breaks = [
        "Peak-cycle ROIC sold as franchise (FP-R1)",
        "Hidden dual-view conflict / ex-GW-only headline (FP-R3)",
        "ΔIC≈0 incremental explosion misread as quality (FP-R7)",
        "Investment-phase vs persistent destruction ambiguity (FP-R12 / D10)",
        "Impairment-improved ROIC optics (FP-R6)",
        "Forced maint CapEx invention (forbidden)",
        "Confusing Stage 5 IOM with Stage 6 ROIIC",
    ]

    for g in gaps:
        if g not in monitors:
            monitors.append(g)
    if not semantic.filled:
        monitors.append("Complete Notes/MD&A capital semantic review")
    if (m.get("history_flags") or {}).get("history_thin"):
        monitors.append("Prefer ≥3 FY when available (descriptive — not a fail bar)")

    missing = list(gaps)
    for k, v in list(calc.null_reasons.items())[:25]:
        missing.append(f"calc null: {k}: {v}")

    why.extend(
        [f"{b.dimension_id}={b.label}: {b.why[:160]}" for b in bench if b.dimension_id.startswith("RC")][:4]
    )

    dual_obj = DualROICView(
        period_key=dual_raw.get("period_key"),
        nopat=dual_raw.get("nopat"),
        nopat_null=dual_raw.get("nopat_null"),
        tax_rate=dual_raw.get("tax_rate"),
        tax_rate_source=dual_raw.get("tax_rate_source"),
        ic_inclusive=dual_raw.get("ic_inclusive"),
        ic_tangible=dual_raw.get("ic_tangible"),
        average_ic_inclusive=dual_raw.get("average_ic_inclusive"),
        average_ic_tangible=dual_raw.get("average_ic_tangible"),
        average_ic_method=dual_raw.get("average_ic_method"),
        roic_inclusive=dual_raw.get("roic_inclusive"),
        roic_tangible=dual_raw.get("roic_tangible"),
        dual_view_emitted=bool(dual_raw.get("dual_view_emitted")),
        dual_view_mandatory=bool(dual_raw.get("dual_view_mandatory")),
        tangible_ne_ma_success=True,
        definition_labels=dual_raw.get("definition_labels") or {},
        nibol_incomplete=bool(dual_raw.get("nibol_incomplete")),
        financing_check_gap=dual_raw.get("financing_check_gap"),
        financing_check_flag=dual_raw.get("financing_check_flag"),
    ) if dual_raw else None

    incr_windows = [
        IncrementalROICWindow(**{k: w.get(k) for k in IncrementalROICWindow.__dataclass_fields__})
        if isinstance(w, dict)
        else w
        for w in windows_raw
    ]

    return Stage6Report(
        ticker=ticker,
        date=utc_now(),
        periods_used=periods_used,
        sources=sources,
        process_outcome=process_outcome,
        why_bullets=why[:12],
        carry_forward_concerns=carry,
        dual_roic_bullets=dual_bullets,
        incremental_roic_bullets=incr_bullets,
        reinvestment_composition_bullets=reinv_bullets,
        runway_bullets=runway_bullets,
        capex_productivity_bullets=capex_bullets,
        wc_mechanism_bullets=wc_bullets,
        false_positive_tags=fp_tags,
        benchmark_results=bench,
        archetype=archetype,
        dual_roic=dual_obj,
        incremental_roic_windows=incr_windows,
        runway_label=runway_label,
        stage7_handoff_flags=s7_flags,
        what_is_strong=strong,
        what_can_break=breaks,
        monitors=monitors,
        missing_ambiguous=missing,
        question_answers=answers,
        calc=calc,
        semantic=semantic,
        terminates_later_stages=False,
        refuse_reason=None,
        thesis_coherence=thesis_coh,
        d10_elevated=d10,
    )
