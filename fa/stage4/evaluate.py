"""Stage 4 question spine → evidence pack + process outcome.

Outcomes ONLY: PROCEED | CONDITIONAL | REVIEW_REQUIRED | TOO_HARD.
Contextual (causal/materiality/thesis/durability/archetype/unresolved/FP severity).
No mechanical label-count → outcome. No numeric thresholds. No colors.
Stage 4 does NOT mechanically terminate later stages. NC* NOT LOCKED.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ids import utc_now
from ..models import (
    ArchetypeAdaptation,
    CalcResult,
    GrowthDecomposition,
    QuestionAnswer,
    RunwayAssessment,
    Stage4ProcessOutcome,
    Stage4Report,
    Stage4SemanticReview,
)
from .archetype import propose_archetype
from .benchmark import assess_runway, label_benchmarks, _tag_false_positives
from .calc import compute_stage4_metrics
from .questions import MUST_QUESTIONS, SHOULD_QUESTIONS, STAGE4_OUTCOMES
from .semantic import (
    load_stage4_semantic_from_fixture,
    placeholder_stage4_semantic,
    semantic_text_blob,
)


def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):,.4f}" if abs(float(v)) < 10 else f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _must_map() -> dict[str, str]:
    return {qid: q for qid, q in MUST_QUESTIONS}


def _thesis_coherence(
    thesis_summary: str | None,
    thesis_runway: str | None,
    archetype: ArchetypeAdaptation | None,
    calc_metrics: dict[str, Any],
) -> str:
    """Heuristic supports/strains/falsifies — no auto kill."""
    if not thesis_summary and not thesis_runway:
        return "unknown"
    if archetype and archetype.classification_path == "REVIEW_REQUIRED":
        # Ambiguous archetype can strain thesis framing
        return "strains"
    primary = archetype.primary_archetype if archetype else "A11"
    blob = f"{thesis_summary or ''} {thesis_runway or ''}".lower()
    # Mature franchise + modest growth → supports
    latest = (calc_metrics.get("latest_revenue_yoy") or {}).get("fraction")
    if primary == "A1" and latest is not None:
        return "supports"
    if primary == "A11" and "mixed" in (archetype.ambiguity_notes or "").lower():
        return "strains"
    # Default: evidence available → supports unless clear conflict keywords
    conflict = any(
        tok in blob
        for tok in ("turnaround needed", "thesis broken", "no longer", "structural decline")
    )
    if conflict:
        return "falsifies"
    return "supports" if thesis_summary else "unknown"


def evaluate_stage4(
    ticker: str,
    periods: list[dict[str, Any]],
    *,
    gate0_class: str = "operating",
    sources: list[str] | None = None,
    semantic: Stage4SemanticReview | None = None,
    semantic_notes_path: Path | None = None,
    thesis_summary: str | None = None,
    thesis_runway: str | None = None,
    business_notes: str | None = None,
    unresolved_major_conflict: bool = False,
    extend_full_cycle: bool = False,
    stage3_fcf_by_period: dict[str, float] | None = None,
    peer_notes: str | None = None,
    force_primary: str | None = None,
) -> Stage4Report:
    """
    Evaluate Stage 4 Growth Quality / Runway.
    FI / non-operating Gate 0 → TOO_HARD refuse.
    terminates_later_stages always False.
    """
    ticker = ticker.upper()
    sources = sources or []
    must_q = _must_map()

    if semantic is None:
        if semantic_notes_path:
            semantic = load_stage4_semantic_from_fixture(semantic_notes_path)
        else:
            semantic = placeholder_stage4_semantic()

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
            "are HARD OUT OF SCOPE for Stage 4 OpCo growth logic; refuse"
        )
        for qid in [f"S4-M{i}" for i in range(1, 8)]:
            ans(qid, "blocked", reason, [])
        ans("S4-M8", "answered", f"process_outcome=TOO_HARD; {reason}", ["TOO_HARD"])
        for qid, qtext in SHOULD_QUESTIONS:
            answers.append(
                QuestionAnswer(
                    question_id=qid,
                    question=qtext,
                    status="blocked",
                    answer_summary="Stage 4 refused — Gate 0 ≠ operating",
                    evidence=[],
                    must=False,
                )
            )
        return Stage4Report(
            ticker=ticker,
            date=utc_now(),
            periods_used=[],
            sources=sources,
            process_outcome="TOO_HARD",
            why_bullets=[reason],
            carry_forward_concerns=[reason],
            growth_observed_bullets=[],
            decomposition_bullets=[],
            runway_bullets=[],
            thesis_link_bullets=[],
            false_positive_tags=[],
            benchmark_results=[],
            context_tags=[],
            archetype=None,
            runway=None,
            decompositions=[],
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

    sem_blob_early = semantic_text_blob(semantic) if semantic is not None else ""
    calc = compute_stage4_metrics(
        periods_sorted,
        extend_full_cycle=extend_full_cycle,
        stage3_fcf_by_period=stage3_fcf_by_period,
        semantic_texts=[sem_blob_early] if sem_blob_early else None,
    )
    m = calc.metrics
    periods_used = [
        {"period_key": p.get("period_key") or "", "version_id": p.get("version_id") or ""}
        for p in periods_sorted
        if p.get("period_type") == "FY"
    ][-5:]

    # Archetype
    sem_blob = semantic_text_blob(semantic)
    archetype = propose_archetype(
        thesis_summary=thesis_summary,
        business_notes=business_notes,
        semantic_text=sem_blob,
        calc_hints=m,
        force_primary=force_primary,
    )

    thesis_coh = _thesis_coherence(thesis_summary, thesis_runway, archetype, m)

    fp_tags = _tag_false_positives(
        calc_metrics=m, semantic=semantic, archetype=archetype
    )
    runway = assess_runway(
        archetype=archetype,
        semantic=semantic,
        thesis_runway=thesis_runway,
        calc_metrics=m,
    )
    bench, context_tags = label_benchmarks(
        calc_metrics=m,
        archetype=archetype,
        semantic=semantic,
        runway=runway,
        fp_tags=fp_tags,
        thesis_coherence=thesis_coh,
        peer_notes=peer_notes,
    )

    # --- S4-M1 Growth observed ---
    yoy = m.get("latest_revenue_yoy")
    if yoy and yoy.get("fraction") is not None:
        ans(
            "S4-M1",
            "answered",
            (
                f"Multi-period revenue path: n_fy={m.get('n_fy')}; "
                f"latest YoY abs={_fmt(yoy.get('absolute'))} frac={_fmt(yoy.get('fraction'))}; "
                f"consistency={m.get('revenue_path_consistency')}; "
                f"3Y CAGR={m.get('revenue_cagr_3y')}; 5Y CAGR={m.get('revenue_cagr_5y')}"
            ),
            [str(m.get("revenue_fy_series")), str(m.get("history_flags"))],
        )
        why.append(
            f"Revenue latest YoY frac={_fmt(yoy.get('fraction'))}; "
            f"path={m.get('revenue_path_consistency')} (descriptive)"
        )
    elif m.get("n_fy", 0) == 0:
        ans("S4-M1", "missing", "No FY revenue periods available", [])
        gaps.append("S4-M1 no FY revenue")
    else:
        ans(
            "S4-M1",
            "partial",
            f"Revenue series present (n_fy={m.get('n_fy')}) but YoY incomplete",
            [str(m.get("revenue_fy_series"))],
        )
        gaps.append("S4-M1 YoY incomplete")

    # --- S4-M2 Decomposition ---
    decomps_raw = m.get("decompositions") or []
    decomps = [GrowthDecomposition(**d) if isinstance(d, dict) else d for d in decomps_raw]
    if decomps_raw or (semantic and semantic.organic_acquired_notes):
        ans(
            "S4-M2",
            "answered" if decomps_raw else "partial",
            (
                f"Decomposition objects={len(decomps_raw)}; "
                f"latest={decomps_raw[-1] if decomps_raw else 'n/a'}; "
                f"semantic_organic={bool(semantic.organic_acquired_notes)}"
            ),
            [str(decomps_raw[-1]) if decomps_raw else "semantic only"],
        )
    else:
        ans(
            "S4-M2",
            "partial",
            "Organic vs acquired UNKNOWN — not disclosed; no invention",
            ["UNATTRIBUTED"],
        )
        gaps.append("S4-M2 organic bridge UNKNOWN")

    # --- S4-M3 VPM/FX ---
    if semantic and (
        semantic.volume_price_mix_notes or semantic.fx_notes or semantic.geography_product_notes
    ):
        ans(
            "S4-M3",
            "partial",
            (
                f"VPM={bool(semantic.volume_price_mix_notes)}; FX={bool(semantic.fx_notes)}; "
                f"geo/product={bool(semantic.geography_product_notes)} — "
                "complete attribution not required; honesty tagged"
            ),
            [
                semantic.volume_price_mix_notes or "",
                semantic.fx_notes or "",
            ],
        )
    else:
        ans(
            "S4-M3",
            "partial",
            "Volume/price/mix/FX disclosure thin — UNKNOWN components left honest",
            [],
        )
        gaps.append("S4-M3 VPM/FX thin")

    # --- S4-M4 Economic value posture (no ROIC) ---
    ans(
        "S4-M4",
        "partial",
        (
            f"Owner path: share_dir={m.get('share_count_direction')}; "
            f"NI vs EPS={m.get('ni_vs_eps_yoy')}; "
            f"capex pattern={m.get('capital_intensity_pattern')}; "
            "ROIC/incremental returns → Stage 6 (not computed here)"
        ),
        ["no Stage 6 ROIC in Stage 4"],
    )

    # --- S4-M5 Runway ---
    ans(
        "S4-M5",
        "answered",
        f"Runway confidence={runway.confidence}; {runway.summary}",
        runway.lenses_used + runway.fact_evidence[:2],
    )
    why.append(f"Runway confidence={runway.confidence} (not a score)")

    # --- S4-M6 Thesis ---
    ans(
        "S4-M6",
        "partial" if thesis_coh == "unknown" else "answered",
        (
            f"Thesis coherence={thesis_coh}; PRIMARY={archetype.primary_archetype}; "
            f"snippet={(thesis_summary or '')[:200]}"
        ),
        [archetype.why],
    )
    if thesis_coh in {"strains", "falsifies"}:
        carry.append(f"Thesis coherence={thesis_coh} — carry to final FA")

    # --- S4-M7 FP tags ---
    ans(
        "S4-M7",
        "answered",
        f"FP tags={[t['id'] for t in fp_tags]} (evidence, not auto-fail)",
        [t.get("why", "") for t in fp_tags[:5]],
    )

    # SHOULD
    for qid, qtext in SHOULD_QUESTIONS:
        status = "partial"
        note = "SHOULD gap = monitor, not kill"
        if qid == "S4-S3":
            note = (
                f"Dilution path: share_dir={m.get('share_count_direction')}; "
                f"SBC series present={bool(m.get('sbc_fy_series'))}"
            )
            status = "answered" if m.get("share_count_direction") != "UNKNOWN" else "partial"
        elif qid == "S4-S4":
            mature_ok = "MATURE_FRANCHISE_OK" in context_tags
            note = (
                f"Mature franchise context_tag={mature_ok}; "
                "low headline growth must not alone penalize mature compounder"
            )
            status = "answered" if mature_ok or archetype.primary_archetype == "A1" else "partial"
        elif qid == "S4-S5":
            note = "Unit economics / cohorts → Stage 5 (not stolen here)"
            status = "partial"
        elif qid == "S4-S6":
            if semantic and semantic.backlog_rpo_notes:
                note = f"Backlog/RPO semantic: {semantic.backlog_rpo_notes[:200]}"
                status = "answered"
            elif archetype.model_slot_status == "NOT_APPLICABLE":
                note = "Model slot NOT_APPLICABLE for backlog/RPO this archetype"
                status = "answered"
            else:
                note = "Backlog/RPO not disclosed — model-conditional UNKNOWN"
        elif qid == "S4-S1":
            bd8 = next((b for b in bench if b.dimension_id == "BD8"), None)
            note = f"BD8={bd8.label if bd8 else 'n/a'}: {bd8.why if bd8 else ''}"[:300]
        elif qid == "S4-S2":
            note = "Cannibalization assessment needs segment detail — monitor"
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
    # Explicitly do NOT use count of BELOW_REFERENCE / FP tags as a formula.
    process_outcome: Stage4ProcessOutcome
    must_missing = [a for a in answers if a.must and a.status == "missing"]
    material_fps = [t for t in fp_tags if t.get("severity") == "material"]
    material_escalations = [
        f
        for f in semantic.findings
        if f.escalate_to_human and f.materiality_judgment == "material"
    ]

    usable = [p for p in periods_sorted if (p.get("fields") or {}).get("revenue") is not None]

    if not periods_sorted or not usable:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — no Normalized revenue periods"]
        carry.append("Stage 4 TOO_HARD: no revenue periods")
    elif unresolved_major_conflict and not usable:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — conflict and missing growth spine"]
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
            carry.append("Thesis falsified by growth evidence — final FA must see this")
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
        a.status == "partial" for a in answers if a.must and a.question_id != "S4-M8"
    ):
        # CONDITIONAL requires named monitors
        process_outcome = "CONDITIONAL"
        why.append("Usable package with named monitors — gaps or partial MUST remain")
        for g in gaps:
            monitors.append(g)
            if g not in carry:
                carry.append(f"Monitor/gap: {g}")
        if "MATURE_FRANCHISE_OK" in context_tags:
            why.append(
                "MATURE_FRANCHISE_OK context tag present — modest growth not alone penalized"
            )
    else:
        process_outcome = "PROCEED"
        why.append(
            "MUST answered honestly; growth pack coherent; no material unresolved FP; "
            "continue with evidence (Stage 4 non-terminating by default)"
        )

    # Mature franchise must not be forced to BELOW→kill; ensure we didn't
    if "MATURE_FRANCHISE_OK" in context_tags and process_outcome == "TOO_HARD":
        # Only keep TOO_HARD if truly no data — already handled; no rewrite needed
        pass

    assert process_outcome in STAGE4_OUTCOMES

    # Named monitors for CONDITIONAL
    if process_outcome == "CONDITIONAL":
        if not any("organic" in x.lower() for x in monitors):
            if any(a.question_id == "S4-M2" and a.status == "partial" for a in answers) or any(
                b.dimension_id == "BD2" and b.label == "UNKNOWN" for b in bench
            ):
                monitors.append(
                    "Monitor: organic vs acquired disclosure remains UNKNOWN (not invented)"
                )
        if m.get("share_count_direction") == "UNKNOWN":
            monitors.append("Monitor: obtain diluted weighted shares for owner-growth path")
        if any(a.question_id == "S4-M3" and a.status == "partial" for a in answers):
            if not any("volume/price/mix" in x.lower() or "vpm" in x.lower() for x in monitors):
                monitors.append(
                    "Monitor: complete volume/price/mix attribution when company discloses"
                )
        if runway.confidence in {"LOW", "UNKNOWN"}:
            monitors.append("Monitor: strengthen runway evidence (geo/product/capacity citations)")
        # Prefer ≥3 FY monitor only while thin
        if (m.get("history_flags") or {}).get("history_thin"):
            if not any("≥3 FY" in x or ">=3 FY" in x for x in monitors):
                monitors.append("Prefer ≥3 FY when available (descriptive — not a fail bar)")

    ans(
        "S4-M8",
        "answered",
        (
            f"process_outcome={process_outcome}; carry_forward={len(carry)} items; "
            "Stage 4 does not alone mechanically terminate later stages; "
            "no label-count→outcome; NC* NOT LOCKED"
        ),
        [process_outcome, "terminates_later_stages=False"],
    )

    growth_obs = [
        f"Revenue FY series: {m.get('revenue_fy_series')}",
        f"Revenue YoY: {m.get('revenue_yoy')}",
        f"CAGR 3Y={m.get('revenue_cagr_3y')}; 5Y={m.get('revenue_cagr_5y')}",
        f"Path consistency={m.get('revenue_path_consistency')}",
        f"History flags={m.get('history_flags')}",
        f"Q path n={m.get('n_q')}",
    ]
    decomp_bullets = []
    for d in decomps_raw[-2:]:
        decomp_bullets.append(
            f"{d.get('period_key')}: Δrev%={d.get('reported_revenue_change_pct')}; "
            f"org/acq={d.get('organic_vs_acquired_summary')}; "
            f"components={len(d.get('components') or [])}; "
            f"unattr={d.get('unattributed_or_unknown')}"
        )
    if semantic and semantic.organic_acquired_notes:
        decomp_bullets.append(f"Semantic organic/acquired: {semantic.organic_acquired_notes[:240]}")
    if not decomp_bullets:
        decomp_bullets.append("No structured decomposition — UNKNOWN honest")

    runway_bullets = [
        runway.summary,
        f"confidence={runway.confidence}",
        f"lenses={runway.lenses_used}",
        f"falsifiers={runway.falsifiers}",
        *[f"FACT: {x}" for x in runway.fact_evidence[:3]],
        *[f"GUIDANCE: {x}" for x in runway.guidance_evidence[:3]],
        *[f"INFERENCE: {x}" for x in runway.inference_evidence[:2]],
    ]
    thesis_bullets = [
        f"coherence={thesis_coh}",
        f"PRIMARY={archetype.primary_archetype} ({archetype.primary_label})",
        f"traits={archetype.secondary_traits}",
        f"drivers={[d.get('id') for d in archetype.model_specific_drivers]}",
        f"model_slot={archetype.model_slot} status={archetype.model_slot_status}",
        f"classification_path={archetype.classification_path}",
        f"G2-M4: {(thesis_runway or '')[:240]}",
    ]

    strong = []
    if "MATURE_FRANCHISE_OK" in context_tags:
        strong.append("Mature franchise context — modest growth eligible for PASS/context tag")
    if m.get("n_fy", 0) >= 2:
        strong.append("Multi-period revenue exhibit present")
    if semantic.filled:
        strong.append("Filing-backed growth semantic filled")
    if archetype.classification_path == "AUTOMATED":
        strong.append(f"Archetype automated: {archetype.primary_archetype}")

    breaks = [
        "Organic bridge missing while M&A material",
        "Cyclical rebound sold as franchise growth",
        "Dilutive share issuance without economic earnings growth",
        "Thesis/category mismatch (CHALLENGE_ARCHETYPE)",
        "Runway claim without cited evidence (fake TAM as FACT)",
    ]

    for g in gaps:
        if g not in monitors:
            monitors.append(g)
    if not semantic.filled:
        monitors.append("Complete Notes/MD&A growth semantic review")
    if (m.get("history_flags") or {}).get("history_thin"):
        monitors.append("Prefer ≥3 FY when available (descriptive — not a fail bar)")

    missing = list(gaps)
    for k, v in list(calc.null_reasons.items())[:25]:
        missing.append(f"calc null: {k}: {v}")

    # Benchmark WHY bullets for report
    why.extend([f"{b.dimension_id}={b.label}: {b.why[:160]}" for b in bench if b.dimension_id.startswith("BD")][:4])

    return Stage4Report(
        ticker=ticker,
        date=utc_now(),
        periods_used=periods_used,
        sources=sources,
        process_outcome=process_outcome,
        why_bullets=why[:10],
        carry_forward_concerns=carry,
        growth_observed_bullets=growth_obs,
        decomposition_bullets=decomp_bullets,
        runway_bullets=runway_bullets,
        thesis_link_bullets=thesis_bullets,
        false_positive_tags=fp_tags,
        benchmark_results=bench,
        context_tags=context_tags,
        archetype=archetype,
        runway=runway,
        decompositions=decomps,
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
    )
