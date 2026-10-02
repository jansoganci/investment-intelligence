"""Stage 5 question spine → evidence pack + process outcome.

Outcomes ONLY: PROCEED | CONDITIONAL | REVIEW_REQUIRED | TOO_HARD.
Contextual (causal/materiality/thesis/durability/archetype/FP severity).
No mechanical label-count → outcome. No numeric GM/OP/IM bands. No colors.
Stage 5 does NOT mechanically terminate later stages. No BE9 ROIC.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ids import utc_now
from ..models import (
    ArchetypeAdaptation,
    CalcResult,
    IncrementalOMWindow,
    MarginDecomposition,
    QuestionAnswer,
    Stage5ProcessOutcome,
    Stage5Report,
    Stage5SemanticReview,
)
from .archetype import adapt_from_stage4
from .benchmark import (
    assess_durability,
    assess_pricing_power,
    label_benchmarks,
    _tag_false_positives,
)
from .calc import compute_stage5_metrics
from .questions import MUST_QUESTIONS, SHOULD_QUESTIONS, STAGE5_OUTCOMES
from .semantic import (
    load_stage5_semantic_from_fixture,
    placeholder_stage5_semantic,
    semantic_text_blob,
)


def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        fv = float(v)
        return f"{fv:.4f}" if abs(fv) < 10 else f"{fv:,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _must_map() -> dict[str, str]:
    return {qid: q for qid, q in MUST_QUESTIONS}


def _thesis_coherence(
    thesis_summary: str | None,
    thesis_margins: str | None,
    archetype: ArchetypeAdaptation | None,
    calc_metrics: dict[str, Any],
) -> str:
    """Heuristic supports/strains/falsifies — no auto kill."""
    if not thesis_summary and not thesis_margins:
        return "unknown"
    if archetype and archetype.classification_path == "REVIEW_REQUIRED":
        return "strains"
    primary = archetype.primary_archetype if archetype else "A11"
    blob = f"{thesis_summary or ''} {thesis_margins or ''}".lower()
    latest = calc_metrics.get("latest_margins") or {}
    if primary == "A1" and latest.get("operating_margin") is not None:
        return "supports"
    if primary == "A11" and "mixed" in (archetype.ambiguity_notes or "").lower():
        return "strains"
    conflict = any(
        tok in blob
        for tok in ("economics broken", "no moat", "structural margin collapse", "thesis broken")
    )
    if conflict:
        return "falsifies"
    return "supports" if thesis_summary else "unknown"


def evaluate_stage5(
    ticker: str,
    periods: list[dict[str, Any]],
    *,
    gate0_class: str = "operating",
    sources: list[str] | None = None,
    semantic: Stage5SemanticReview | None = None,
    semantic_notes_path: Path | None = None,
    thesis_summary: str | None = None,
    thesis_margins: str | None = None,
    business_notes: str | None = None,
    stage4_archetype: dict[str, Any] | ArchetypeAdaptation | None = None,
    unresolved_major_conflict: bool = False,
    extend_full_cycle: bool = False,
    peer_notes: str | None = None,
    force_primary: str | None = None,
) -> Stage5Report:
    """
    Evaluate Stage 5 Margins / Business Economics.
    FI / non-operating Gate 0 → TOO_HARD refuse.
    terminates_later_stages always False. No BE9 / no numeric bands.
    """
    ticker = ticker.upper()
    sources = sources or []
    must_q = _must_map()

    if semantic is None:
        if semantic_notes_path:
            semantic = load_stage5_semantic_from_fixture(semantic_notes_path)
        else:
            semantic = placeholder_stage5_semantic()

    periods_sorted = sorted(
        periods,
        key=lambda d: (0 if d.get("period_type") == "FY" else 1, d.get("period_key") or ""),
    )

    carry: list[str] = []
    gaps: list[str] = []
    why: list[str] = []
    answers: list[QuestionAnswer] = []
    monitors: list[str] = []

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
            "are HARD OUT OF SCOPE for Stage 5 OpCo economics logic; refuse"
        )
        for qid in [f"S5-M{i}" for i in range(1, 8)]:
            ans(qid, "blocked", reason, [])
        ans("S5-M8", "answered", f"process_outcome=TOO_HARD; {reason}", ["TOO_HARD"])
        for qid, qtext in SHOULD_QUESTIONS:
            answers.append(
                QuestionAnswer(
                    question_id=qid,
                    question=qtext,
                    status="blocked",
                    answer_summary="Stage 5 refused — Gate 0 ≠ operating",
                    evidence=[],
                    must=False,
                )
            )
        return Stage5Report(
            ticker=ticker,
            date=utc_now(),
            periods_used=[],
            sources=sources,
            process_outcome="TOO_HARD",
            why_bullets=[reason],
            carry_forward_concerns=[reason],
            margin_structure_bullets=[],
            decomposition_bullets=[],
            pricing_cost_bullets=[],
            incremental_om_bullets=[],
            durability_bullets=[],
            thesis_link_bullets=[],
            false_positive_tags=[],
            benchmark_results=[],
            context_tags=[],
            archetype=None,
            pricing_power=None,
            durability=None,
            decompositions=[],
            incremental_om_windows=[],
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

    calc = compute_stage5_metrics(
        periods_sorted,
        extend_full_cycle=extend_full_cycle,
    )
    m = calc.metrics
    periods_used = [
        {"period_key": p.get("period_key") or "", "version_id": p.get("version_id") or ""}
        for p in periods_sorted
        if p.get("period_type") == "FY"
    ][-5:]

    sem_blob = semantic_text_blob(semantic)
    archetype = adapt_from_stage4(
        stage4_archetype,
        thesis_summary=thesis_summary,
        business_notes=business_notes,
        semantic_text=sem_blob,
        calc_hints=m,
        force_primary=force_primary,
    )

    thesis_coh = _thesis_coherence(thesis_summary, thesis_margins, archetype, m)
    fp_tags = _tag_false_positives(
        calc_metrics=m, semantic=semantic, archetype=archetype
    )
    pricing = assess_pricing_power(
        semantic=semantic, archetype=archetype, thesis_summary=thesis_summary
    )
    durability = assess_durability(
        archetype=archetype,
        semantic=semantic,
        calc_metrics=m,
        thesis_summary=thesis_summary,
        fp_tags=fp_tags,
    )
    bench, context_tags = label_benchmarks(
        calc_metrics=m,
        archetype=archetype,
        semantic=semantic,
        pricing=pricing,
        durability=durability,
        fp_tags=fp_tags,
        thesis_coherence=thesis_coh,
        peer_notes=peer_notes,
    )

    latest = m.get("latest_margins") or {}

    # --- S5-M1 Margin structure ---
    if latest.get("gross_margin") is not None or latest.get("operating_margin") is not None:
        ans(
            "S5-M1",
            "answered",
            (
                f"Multi-period margins: n_fy={m.get('n_fy')}; n_q={m.get('n_q')}; "
                f"GM={_fmt(latest.get('gross_margin'))}; OP={_fmt(latest.get('operating_margin'))}; "
                f"opex_intensity={_fmt(latest.get('opex_intensity'))} "
                f"(def={latest.get('opex_intensity_definition')}); "
                f"gm_path={m.get('gm_path_consistency')}; op_path={m.get('op_path_consistency')}"
            ),
            [str(m.get("periods_fy_keys")), str(m.get("history_flags"))],
        )
        why.append(
            f"GM={_fmt(latest.get('gross_margin'))}; OP={_fmt(latest.get('operating_margin'))} "
            "(descriptive; no universal hurdle)"
        )
    elif m.get("n_fy", 0) == 0:
        ans("S5-M1", "missing", "No FY periods with margin inputs", [])
        gaps.append("S5-M1 no FY margin spine")
    else:
        ans(
            "S5-M1",
            "partial",
            f"FY present (n_fy={m.get('n_fy')}) but GM/OP incomplete",
            [str(m.get("margin_fy_series"))],
        )
        gaps.append("S5-M1 GM/OP incomplete")

    # --- S5-M2 Decomposition ---
    decomps_raw = m.get("decompositions") or []
    if decomps_raw or (
        semantic
        and (
            semantic.margin_bridge_notes
            or semantic.pricing_power_notes
            or semantic.input_cost_notes
        )
    ):
        # Enrich decomposition components from semantic (COMPANY_EXPLANATION)
        if decomps_raw and semantic:
            comps = []
            if semantic.pricing_power_notes:
                comps.append(
                    {
                        "dimension": "price",
                        "direction_magnitude_note": semantic.pricing_power_notes[:160],
                        "evidence_tag": "COMPANY_EXPLANATION",
                        "citation": "semantic.pricing_power_notes",
                    }
                )
            if semantic.input_cost_notes:
                comps.append(
                    {
                        "dimension": "input_cost",
                        "direction_magnitude_note": semantic.input_cost_notes[:160],
                        "evidence_tag": "COMPANY_EXPLANATION",
                        "citation": "semantic.input_cost_notes",
                    }
                )
            if semantic.margin_bridge_notes:
                comps.append(
                    {
                        "dimension": "mix",
                        "direction_magnitude_note": semantic.margin_bridge_notes[:160],
                        "evidence_tag": "COMPANY_EXPLANATION",
                        "citation": "semantic.margin_bridge_notes",
                    }
                )
            if semantic.ses_notes:
                comps.append(
                    {
                        "dimension": "scale_shared",
                        "direction_magnitude_note": semantic.ses_notes[:160],
                        "evidence_tag": "COMPANY_EXPLANATION",
                        "citation": "semantic.ses_notes",
                    }
                )
            if comps:
                decomps_raw[-1]["components"] = comps
                decomps_raw[-1]["unattributed_or_unknown"] = (
                    "Residual drivers not forced to 100%; honesty over completeness"
                )
                if semantic.ses_notes:
                    decomps_raw[-1]["ses_or_intentional_thin_margin"] = "yes"
                    decomps_raw[-1]["ses_why"] = semantic.ses_notes[:200]
        ans(
            "S5-M2",
            "answered" if (decomps_raw and decomps_raw[-1].get("components")) else "partial",
            (
                f"Decomposition objects={len(decomps_raw)}; "
                f"components={len((decomps_raw[-1] or {}).get('components') or []) if decomps_raw else 0}; "
                f"semantic_bridge={bool(semantic and semantic.margin_bridge_notes)}"
            ),
            [str(decomps_raw[-1]) if decomps_raw else "semantic only"],
        )
    else:
        ans(
            "S5-M2",
            "partial",
            "Driver decomposition UNKNOWN — not disclosed; no invention",
            ["UNATTRIBUTED"],
        )
        gaps.append("S5-M2 driver bridge UNKNOWN")

    # --- S5-M3 Pricing / cost ---
    ans(
        "S5-M3",
        "answered" if pricing.posture not in {"UNKNOWN"} or (
            semantic and semantic.cost_advantage_notes
        ) else "partial",
        (
            f"pricing_posture={pricing.posture}; "
            f"cost_notes={bool(semantic and semantic.cost_advantage_notes)}; "
            f"BE3/BE4 evidence-of-claim only (STRONG≠PROCEED; WEAK≠fail)"
        ),
        pricing.evidence[:3] + pricing.falsifiers[:2],
    )
    why.append(f"Pricing posture={pricing.posture} (not a grade)")

    # --- S5-M4 Incremental OM ---
    iom_raw = m.get("incremental_om_windows") or []
    ans(
        "S5-M4",
        "answered" if iom_raw else "partial",
        (
            f"Incremental OM windows={len(iom_raw)}; "
            f"latest={iom_raw[-1] if iom_raw else 'n/a'}; "
            "descriptive only — no numeric IOM hurdle; ≠ Stage 6 ROIC/ROIIC"
        ),
        [str(w)[:200] for w in iom_raw[:2]] or ["no Stage 6 ROIC in Stage 5"],
    )

    # --- S5-M5 Durability ---
    ans(
        "S5-M5",
        "answered",
        f"durability_confidence={durability.confidence}; {durability.summary}",
        durability.lenses_used + durability.falsifiers[:2],
    )
    why.append(f"Durability confidence={durability.confidence} (not a score)")

    # --- S5-M6 FP ---
    ans(
        "S5-M6",
        "answered",
        f"FP tags={[t['id'] for t in fp_tags]} (evidence, not auto-fail; no FP score)",
        [t.get("why", "") for t in fp_tags[:5]],
    )

    # --- S5-M7 Thesis ---
    ans(
        "S5-M7",
        "partial" if thesis_coh == "unknown" else "answered",
        (
            f"Thesis coherence={thesis_coh}; PRIMARY={archetype.primary_archetype}; "
            f"snippet={(thesis_summary or '')[:200]}"
        ),
        [archetype.why],
    )
    if thesis_coh in {"strains", "falsifies"}:
        carry.append(f"Thesis coherence={thesis_coh} — carry to final FA / Stage 6 packaging")

    # SHOULD
    for qid, qtext in SHOULD_QUESTIONS:
        status = "partial"
        note = "SHOULD gap = monitor, not kill"
        if qid == "S5-S1":
            if semantic and semantic.segment_margin_notes:
                note = f"Segment margins: {semantic.segment_margin_notes[:200]}"
                status = "answered"
            elif (m.get("optional_disclosed") or {}).get("segment_operating_margin"):
                note = "Normalized segment_operating_margin present (disclosed-only)"
                status = "answered"
            else:
                note = "Segment margin splits not disclosed — UNKNOWN"
        elif qid == "S5-S2":
            if semantic and semantic.unit_econ_notes:
                note = f"Unit econ clues: {semantic.unit_econ_notes[:200]}; capital bridge → Stage 6"
                status = "answered"
            else:
                note = "Unit economics / contribution not disclosed — handoff Stage 6 when relevant"
        elif qid == "S5-S3":
            sbc = (latest.get("sbc_aware") or {})
            note = (
                f"SBC-aware OP margin={sbc.get('op_plus_sbc_margin')}; "
                f"semantic_nongaap={bool(semantic and semantic.sbc_nongaap_notes)}"
            )
            status = (
                "answered"
                if sbc.get("op_plus_sbc_margin") is not None
                or (semantic and semantic.sbc_nongaap_notes)
                else "partial"
            )
        elif qid == "S5-S4":
            if semantic and semantic.input_cost_notes:
                note = f"Input/labor/FX: {semantic.input_cost_notes[:200]}"
                status = "answered"
            else:
                note = "Input/commodity/labor sensitivity disclosure thin — monitor"
        elif qid == "S5-S5":
            ses_ok = "SCALE_ECONOMIES_SHARED_OK" in context_tags
            note = (
                f"SES context_tag={ses_ok}; "
                "thin OP must not alone be BELOW_REFERENCE when SES evidence adequate"
            )
            status = "answered" if ses_ok or (semantic and semantic.ses_notes) else "partial"
        elif qid == "S5-S6":
            note = (
                f"Peer notes secondary only: {peer_notes[:160] if peer_notes else 'none'}; "
                "never peer-percentile primary"
            )
            status = "answered" if peer_notes else "partial"
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

    # --- Process outcome (contextual — FORBIDDEN: label counting) ---
    process_outcome: Stage5ProcessOutcome
    material_fps = [t for t in fp_tags if t.get("severity") == "material"]
    material_escalations = [
        f
        for f in semantic.findings
        if f.escalate_to_human and f.materiality_judgment == "material"
    ]
    usable = [
        p
        for p in periods_sorted
        if (p.get("fields") or {}).get("revenue") is not None
        and (
            (p.get("fields") or {}).get("operating_income") is not None
            or (p.get("fields") or {}).get("gross_profit") is not None
        )
    ]

    if not periods_sorted or not usable:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — no Normalized revenue + margin inputs"]
        carry.append("Stage 5 TOO_HARD: no margin spine")
    elif unresolved_major_conflict and not usable:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — conflict and missing economics spine"]
    elif (
        archetype.classification_path == "REVIEW_REQUIRED"
        and archetype.confidence in {"LOW", "UNKNOWN"}
    ) or thesis_coh == "falsifies":
        process_outcome = "REVIEW_REQUIRED"
        why.append(
            "Material archetype ambiguity and/or thesis falsification — "
            "carry-forward REVIEW (non-terminating)"
        )
        if archetype.ambiguity_notes:
            carry.append(f"Archetype: {archetype.ambiguity_notes}")
        if thesis_coh == "falsifies":
            carry.append("Thesis falsified by economics evidence — final FA must see this")
    elif material_fps or material_escalations or thesis_coh == "strains":
        process_outcome = "REVIEW_REQUIRED"
        why.append(
            "Material FP / semantic escalation / thesis strain — human exception queue "
            "(labels are evidence; not a count formula)"
        )
        for t in material_fps:
            carry.append(f"FP {t['id']}: {t.get('why')}")
        for f in material_escalations:
            carry.append(f"Semantic escalate: {f.topic} — {f.materiality_reason}")
    elif gaps or not semantic.filled or any(
        a.status == "partial" for a in answers if a.must and a.question_id != "S5-M8"
    ):
        process_outcome = "CONDITIONAL"
        why.append("Usable package with named monitors — gaps or partial MUST remain")
        for g in gaps:
            monitors.append(g)
            if g not in carry:
                carry.append(f"Monitor/gap: {g}")
        if "MATURE_FRANCHISE_ECONOMICS_OK" in context_tags:
            why.append(
                "MATURE_FRANCHISE_ECONOMICS_OK — modest franchise margins not alone penalized"
            )
        if "SCALE_ECONOMIES_SHARED_OK" in context_tags:
            why.append(
                "SCALE_ECONOMIES_SHARED_OK — thin OP not alone BELOW_REFERENCE (evidence required)"
            )
    else:
        process_outcome = "PROCEED"
        why.append(
            "MUST answered honestly; economics pack coherent; no material unresolved FP; "
            "continue with evidence (Stage 5 non-terminating by default)"
        )

    assert process_outcome in STAGE5_OUTCOMES

    if process_outcome == "CONDITIONAL":
        if any(a.question_id == "S5-M2" and a.status == "partial" for a in answers):
            if not any("decomposition" in x.lower() or "driver" in x.lower() for x in monitors):
                monitors.append(
                    "Monitor: margin driver decomposition remains thin (not invented)"
                )
        if pricing.posture == "UNKNOWN":
            monitors.append("Monitor: strengthen pricing-power / cost-advantage citations")
        if durability.confidence in {"LOW", "UNKNOWN"}:
            monitors.append("Monitor: strengthen durability falsifiers + multi-period evidence")
        if (m.get("history_flags") or {}).get("history_thin"):
            monitors.append("Prefer ≥3 FY when available (descriptive — not a fail bar)")
        carry.append("Economics concerns carry into Stage 6 (ROIC / CapEx returns) — not computed here")

    ans(
        "S5-M8",
        "answered",
        (
            f"process_outcome={process_outcome}; carry_forward={len(carry)} items; "
            "Stage 5 does not alone mechanically terminate later stages; "
            "no label-count→outcome; no numeric GM/OP/IM bands; no BE9 ROIC"
        ),
        [process_outcome, "terminates_later_stages=False"],
    )

    margin_bullets = [
        f"FY series keys: {m.get('periods_fy_keys')}",
        f"Q series keys: {m.get('periods_q_keys')}",
        f"Latest GM={_fmt(latest.get('gross_margin'))}; OP={_fmt(latest.get('operating_margin'))}",
        f"ΔGM YoY={_fmt(m.get('delta_gm_yoy'))}; ΔOP YoY={_fmt(m.get('delta_op_yoy'))}",
        f"Path GM={m.get('gm_path_consistency')}; OP={m.get('op_path_consistency')}",
        f"History flags={m.get('history_flags')}",
    ]
    decomp_bullets = []
    for d in decomps_raw[-2:]:
        decomp_bullets.append(
            f"{d.get('period_key')}: GM={d.get('reported_gross_margin')}; "
            f"OP={d.get('reported_operating_margin')}; "
            f"components={len(d.get('components') or [])}; "
            f"unattr={d.get('unattributed_or_unknown')}; "
            f"SES={d.get('ses_or_intentional_thin_margin')}"
        )
    if semantic and semantic.margin_bridge_notes:
        decomp_bullets.append(f"Semantic bridge: {semantic.margin_bridge_notes[:240]}")
    if not decomp_bullets:
        decomp_bullets.append("No structured decomposition — UNKNOWN honest")

    pricing_cost = [
        f"pricing_posture={pricing.posture}",
        pricing.why,
        *[f"EVIDENCE: {e}" for e in pricing.evidence[:3]],
        *[f"FALSIFIER: {f}" for f in pricing.falsifiers[:3]],
    ]
    if semantic and semantic.cost_advantage_notes:
        pricing_cost.append(f"Cost/scale: {semantic.cost_advantage_notes[:240]}")

    iom_bullets = []
    for w in iom_raw:
        iom_bullets.append(
            f"{w.get('window_id')}: IOM={w.get('incremental_om')}; "
            f"class={w.get('posture_class')}; cause={w.get('cause_tag')}; "
            f"flags={w.get('honesty_flags')}; handoff={w.get('stage6_handoff')}"
        )
    if not iom_bullets:
        iom_bullets.append("No incremental OM window — UNKNOWN / insufficient periods")

    dur_bullets = [
        durability.summary,
        f"confidence={durability.confidence}",
        f"lenses={durability.lenses_used}",
        f"falsifiers={durability.falsifiers}",
        f"thesis_link={durability.thesis_link}",
    ]
    thesis_bullets = [
        f"coherence={thesis_coh}",
        f"PRIMARY={archetype.primary_archetype} ({archetype.primary_label})",
        f"traits={archetype.secondary_traits}",
        f"drivers={[d.get('id') for d in archetype.model_specific_drivers]}",
        f"model_slot={archetype.model_slot} status={archetype.model_slot_status}",
        f"classification_path={archetype.classification_path}",
        f"margins thesis: {(thesis_margins or '')[:240]}",
    ]

    strong = []
    if "MATURE_FRANCHISE_ECONOMICS_OK" in context_tags:
        strong.append("Mature franchise economics context — modest margins eligible for PASS/context tag")
    if "SCALE_ECONOMIES_SHARED_OK" in context_tags:
        strong.append("SES context tag — thin OP not alone punished")
    if m.get("n_fy", 0) >= 2:
        strong.append("Multi-period margin exhibit present")
    if semantic.filled:
        strong.append("Filing-backed economics semantic filled")
    if archetype.classification_path == "AUTOMATED":
        strong.append(f"Archetype automated/reused: {archetype.primary_archetype}")

    breaks = [
        "Peak / windfall margins sold as franchise",
        "CapEx holiday / deferred opex inflating OP",
        "SBC-blind or heavy non-GAAP optics",
        "Thesis/category mismatch (CHALLENGE_ARCHETYPE)",
        "Negative incremental OM misread without cause tag",
        "Accounting / PPA / mix theatre without persistence",
    ]

    for g in gaps:
        if g not in monitors:
            monitors.append(g)
    if not semantic.filled:
        monitors.append("Complete Notes/MD&A economics semantic review")
    if (m.get("history_flags") or {}).get("history_thin"):
        monitors.append("Prefer ≥3 FY when available (descriptive — not a fail bar)")

    missing = list(gaps)
    for k, v in list(calc.null_reasons.items())[:25]:
        missing.append(f"calc null: {k}: {v}")

    why.extend(
        [f"{b.dimension_id}={b.label}: {b.why[:160]}" for b in bench if b.dimension_id.startswith("BE")][:4]
    )

    decomps = [
        MarginDecomposition(**d) if isinstance(d, dict) else d for d in decomps_raw
    ]
    iom_windows = [
        IncrementalOMWindow(**w) if isinstance(w, dict) else w for w in iom_raw
    ]

    return Stage5Report(
        ticker=ticker,
        date=utc_now(),
        periods_used=periods_used,
        sources=sources,
        process_outcome=process_outcome,
        why_bullets=why[:12],
        carry_forward_concerns=carry,
        margin_structure_bullets=margin_bullets,
        decomposition_bullets=decomp_bullets,
        pricing_cost_bullets=pricing_cost,
        incremental_om_bullets=iom_bullets,
        durability_bullets=dur_bullets,
        thesis_link_bullets=thesis_bullets,
        false_positive_tags=fp_tags,
        benchmark_results=bench,
        context_tags=context_tags,
        archetype=archetype,
        pricing_power=pricing,
        durability=durability,
        decompositions=decomps,
        incremental_om_windows=iom_windows,
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
        model_specific_slot=archetype.model_slot,
        model_specific_slot_note=(
            f"status={archetype.model_slot_status}; optional one slot only (Plan §0.J)"
        ),
    )
