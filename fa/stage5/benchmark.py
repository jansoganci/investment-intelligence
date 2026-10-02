"""Stage 5 Benchmark Layer BE1–BE8 — evidence labels + WHY. Not a hard gate.

Method E: archetype → company history → selective peer (never peer-primary).
No weighted score, no numeric GM/OP/IM bands, no BE9 ROIC, no label-count→outcome.
"""
from __future__ import annotations

from typing import Any

from ..models import (
    ArchetypeAdaptation,
    BenchmarkDimensionResult,
    DurabilityAssessment,
    PricingPowerAssessment,
    Stage5SemanticReview,
)
from .questions import CONTEXT_TAGS, FALSE_POSITIVE_CATALOGUE, PRICING_POWER_POSTURES


def _tag_false_positives(
    *,
    calc_metrics: dict[str, Any],
    semantic: Stage5SemanticReview | None,
    archetype: ArchetypeAdaptation | None,
) -> list[dict[str, Any]]:
    """FP catalogue as evidence tags — NOT automatic fails. No FP score average."""
    tags: list[dict[str, Any]] = []
    catalog = {fid: desc for fid, desc in FALSE_POSITIVE_CATALOGUE}
    sem_topics = {f.topic for f in (semantic.findings if semantic else [])}
    primary = archetype.primary_archetype if archetype else "A11"

    # FP1 — cycle peak as franchise
    if primary in {"A4", "A8", "A9"} or "cycle_peak_margins" in sem_topics:
        tags.append(
            {
                "id": "FP1",
                "description": catalog["FP1"],
                "severity": "watchable",
                "why": "Cyclical archetype or peak-margin language — do not treat peak OP% as franchise alone",
                "counterexample": "Thesis is cycle-aware with through-cycle cash-cost evidence",
            }
        )

    # FP2 — CapEx holiday
    if "capex_holiday_margin" in sem_topics:
        tags.append(
            {
                "id": "FP2",
                "description": catalog["FP2"],
                "severity": "material",
                "why": "CapEx holiday / deferred investment language — underinvestment risk; Stage 3 context",
                "counterexample": "Sustaining CapEx stable relative to capacity",
            }
        )

    # FP3 — mix theatre
    if "mix_theatre" in sem_topics and not (semantic and semantic.margin_bridge_notes):
        tags.append(
            {
                "id": "FP3",
                "description": catalog["FP3"],
                "severity": "watchable",
                "why": "Mix benefit language without persistence evidence — honesty watch",
                "counterexample": "Mix improvement sustained across multi-year window",
            }
        )

    # FP4 — PPA / acquisition optics
    if primary == "A7" or "ppa_acquisition_optics" in sem_topics:
        tags.append(
            {
                "id": "FP4",
                "description": catalog["FP4"],
                "severity": "watchable",
                "why": "Acquisitive archetype or PPA language — decompose organic vs acquired margins",
                "counterexample": "Organic margin bridge disclosed and durable",
            }
        )

    # FP5 — SBC / non-GAAP
    if "sbc_nongaap" in sem_topics or (
        (calc_metrics.get("latest_margins") or {}).get("sbc_expense") is not None
        and primary == "A2"
    ):
        tags.append(
            {
                "id": "FP5",
                "description": catalog["FP5"],
                "severity": "watchable",
                "why": "SBC / adjusted-margin language or SaaS+SBC present — show SBC-aware view; not auto-fail",
                "counterexample": "GAAP and SBC-aware OP tell the same durability story",
            }
        )

    # FP6 — promo bought share
    if "promo_discounting" in sem_topics:
        tags.append(
            {
                "id": "FP6",
                "description": catalog["FP6"],
                "severity": "watchable",
                "why": "Promo/discounting language — volume vs price honesty required",
                "counterexample": "Price realization holds with volume resilience",
            }
        )

    # FP8 — low margin ≠ bad (SES awareness)
    if primary in {"A6"} or "ses_intentional_thin" in sem_topics:
        tags.append(
            {
                "id": "FP8",
                "description": catalog["FP8"],
                "severity": "context",
                "why": "Do not auto-read thin OP as bad — SES / intentional thin-margin path may apply",
                "counterexample": "SES evidence bar met with invalidators absent",
            }
        )

    # FP9 — high margin ≠ moat (evidence/language only — NO numeric OP% band)
    if "cycle_peak_margins" in sem_topics or primary in {"A4", "A8"}:
        tags.append(
            {
                "id": "FP9",
                "description": catalog["FP9"],
                "severity": "watchable",
                "why": "Peak/cycle or windfall-adjacent posture — high headline margins ≠ moat FACT; cause + durability required",
                "counterexample": "Durable pricing/cost evidence with named falsifiers",
            }
        )

    # FP11 — blended hides weak segment
    if "segment_margins" in sem_topics or primary == "A10":
        tags.append(
            {
                "id": "FP11",
                "description": catalog["FP11"],
                "severity": "watchable",
                "why": "Segment / hybrid posture — blended OP may hide weak engine; S5-S1",
                "counterexample": "Segment margins disclosed and coherent with thesis",
            }
        )

    # FP12 — investment-phase negative IOM
    iom = calc_metrics.get("incremental_om_windows") or []
    for w in iom:
        iom_v = w.get("incremental_om")
        if iom_v is not None and iom_v < 0:
            tags.append(
                {
                    "id": "FP12",
                    "description": catalog["FP12"],
                    "severity": "watchable",
                    "why": "Negative incremental OM window — cause-tag investment vs decay (not permanent fail)",
                    "counterexample": "Investment-phase with clear reinvestment thesis",
                }
            )
            break
    if "investment_phase_om" in sem_topics and not any(t["id"] == "FP12" for t in tags):
        tags.append(
            {
                "id": "FP12",
                "description": catalog["FP12"],
                "severity": "context",
                "why": "Investment-phase language — do not misread temporary negative leverage as decay",
                "counterexample": "Path to positive leverage with demand evidence",
            }
        )

    return tags


def assess_pricing_power(
    *,
    semantic: Stage5SemanticReview | None,
    archetype: ArchetypeAdaptation | None,
    thesis_summary: str | None,
) -> PricingPowerAssessment:
    """Evidence-of-claim posture — STRONG ≠ PROCEED; WEAK ≠ fail."""
    primary = archetype.primary_archetype if archetype else "A11"
    falsifiers = [
        "Promo dependency / share bought with price",
        "Volume collapse after list-price increases",
        "Pass-through fails while input costs rise",
    ]
    evidence: list[str] = []
    posture = "UNKNOWN"

    # NOT_APPLICABLE when pricing power is not the thesis lens (e.g. pure cost/SES retailer)
    blob = f"{thesis_summary or ''} {semantic_text_for_pricing(semantic)}".lower()
    if primary == "A6" and "ses" in blob and "pricing power" not in blob:
        return PricingPowerAssessment(
            posture="NOT_APPLICABLE",
            evidence=["Retailer SES posture — pricing power not primary thesis lens"],
            falsifiers=falsifiers,
            why="Pricing power NOT_APPLICABLE for SES/EDLP-style thesis lens",
        )

    if semantic and semantic.pricing_power_notes:
        evidence.append(f"COMPANY_EXPLANATION: {semantic.pricing_power_notes[:200]}")
        posture = "MODERATE"
        # Stronger cues
        low = semantic.pricing_power_notes.lower()
        if any(tok in low for tok in ("pricing power", "brand premium", "value-based", "pass-through")):
            posture = "STRONG"
        if any(tok in low for tok in ("promo", "discount", "elastic")):
            posture = "MIXED"
    elif primary == "A1":
        posture = "MODERATE"
        evidence.append("A1 mature branded consumer — pricing-power claim typical; confirm with MD&A")
    elif primary in {"A3"}:
        posture = "MODERATE"
        evidence.append("A3 network — take-rate durability is adjacent to pricing posture")
    elif semantic and semantic.filled:
        posture = "UNKNOWN"
        evidence.append("Semantic filled but no pricing-power excerpt — UNKNOWN honest")
    else:
        posture = "UNKNOWN"
        evidence.append("No pricing-power disclosure extracted — UNKNOWN")

    assert posture in PRICING_POWER_POSTURES
    return PricingPowerAssessment(
        posture=posture,
        evidence=evidence,
        falsifiers=falsifiers,
        why=f"posture={posture} (evidence-of-claim only; not a business grade or outcome)",
    )


def semantic_text_for_pricing(semantic: Stage5SemanticReview | None) -> str:
    if not semantic:
        return ""
    return " ".join(
        x
        for x in (
            semantic.pricing_power_notes,
            semantic.ses_notes,
            semantic.promo_discounting if False else None,  # noqa — keep simple
            semantic.margin_bridge_notes,
        )
        if x
    )


def assess_durability(
    *,
    archetype: ArchetypeAdaptation | None,
    semantic: Stage5SemanticReview | None,
    calc_metrics: dict[str, Any],
    thesis_summary: str | None,
    fp_tags: list[dict[str, Any]],
) -> DurabilityAssessment:
    """Durability confidence is NOT a score; no fake moat width."""
    primary = archetype.primary_archetype if archetype else "A11"
    lenses: list[str] = []
    falsifiers = [
        "Pricing power breaks under competition or regulation",
        "Cost advantage eroded by input inflation without pass-through",
        "Mix / cycle peak mistaken for structural franchise",
        "Accounting / SBC / PPA optics reverse",
    ]
    if primary == "A1":
        lenses += ["franchise_intangible", "brand_pricing", "mix_sustainability"]
    elif primary == "A2":
        lenses += ["gm_durability", "sbc_path", "retention_clue"]
    elif primary == "A3":
        lenses += ["network_switching", "take_rate_risk"]
    elif primary in {"A4", "A8", "A9"}:
        lenses += ["cycle_mean_reversion", "cash_cost_curve"]
    elif primary == "A6":
        lenses += ["ses_flywheel", "gross_vs_sga"]
    else:
        lenses += ["cause_persistence", "competitive_posture"]

    flags = calc_metrics.get("history_flags") or {}
    material_fps = [t for t in fp_tags if t.get("severity") == "material"]
    conf = "MEDIUM"
    if flags.get("history_thin"):
        conf = "LOW"
    if primary == "A1" and (calc_metrics.get("n_fy") or 0) >= 3:
        conf = "HIGH" if not material_fps else "MEDIUM"
    if primary in {"A4", "A8", "A9"}:
        conf = "LOW" if conf == "HIGH" else conf  # cycle honesty bias
        if conf == "MEDIUM":
            conf = "MEDIUM"
    if not semantic or not semantic.filled:
        if conf == "HIGH":
            conf = "MEDIUM"
    if (calc_metrics.get("n_fy") or 0) == 0:
        conf = "UNKNOWN"

    summary = (
        f"Economics durability for PRIMARY={primary}: lenses={lenses}; "
        f"history_fy={calc_metrics.get('n_fy')}; material_fp={len(material_fps)}. "
        "Confidence is not a score; no uncited wide-moat FACT."
    )
    return DurabilityAssessment(
        summary=summary,
        confidence=conf,
        falsifiers=falsifiers,
        thesis_link=(thesis_summary or "")[:300] or None,
        lenses_used=lenses,
    )


def label_benchmarks(
    *,
    calc_metrics: dict[str, Any],
    archetype: ArchetypeAdaptation | None,
    semantic: Stage5SemanticReview | None,
    pricing: PricingPowerAssessment | None,
    durability: DurabilityAssessment | None,
    fp_tags: list[dict[str, Any]],
    thesis_coherence: str,
    peer_notes: str | None = None,
) -> tuple[list[BenchmarkDimensionResult], list[str]]:
    """BE1–BE8 labels + closed context tags. Method E. No bands. No BE9."""
    results: list[BenchmarkDimensionResult] = []
    context_tags: list[str] = []
    primary = archetype.primary_archetype if archetype else "A11"
    latest = calc_metrics.get("latest_margins") or {}
    n_fy = calc_metrics.get("n_fy") or 0
    flags = calc_metrics.get("history_flags") or {}

    # --- BE1 Margin structure reality ---
    if latest.get("gross_margin") is not None or latest.get("operating_margin") is not None:
        be1_label = "PASS"
        be1_why = (
            f"Multi-period margin exhibit present (n_fy={n_fy}); "
            f"GM={latest.get('gross_margin')}; OP={latest.get('operating_margin')}; "
            f"gm_path={calc_metrics.get('gm_path_consistency')}; "
            f"op_path={calc_metrics.get('op_path_consistency')}. "
            "Descriptive only — no universal GM/OP hurdle."
        )
        if flags.get("history_thin"):
            be1_label = "MIXED"
            be1_why += " Thin FY history — honesty required; not a fail bar."
    else:
        be1_label = "UNKNOWN"
        be1_why = "Gross/operating margin not computable from Normalized — UNKNOWN honest"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BE1",
            label=be1_label,
            why=be1_why,
            applicability="universal",
            evidence=[f"n_fy={n_fy}", f"keys={calc_metrics.get('periods_fy_keys')}"],
            reference_frame="company_history",
        )
    )

    # --- BE2 Driver decomposition honesty ---
    has_bridge = bool(
        semantic
        and (
            semantic.margin_bridge_notes
            or semantic.pricing_power_notes
            or semantic.input_cost_notes
            or semantic.cost_advantage_notes
        )
    )
    decomp = calc_metrics.get("decompositions") or []
    if has_bridge:
        be2_label = "PASS" if decomp else "MIXED"
        be2_why = (
            "MD&A/Notes margin-driver cues present; components tagged "
            "FACT|COMPANY_EXPLANATION|MODEL_INFERENCE; complete sum-to-100% not required"
        )
    else:
        be2_label = "UNKNOWN"
        be2_why = (
            "Driver decomposition not disclosed / not extracted — left UNKNOWN "
            "(no invention of price/mix/volume attribution)"
        )
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BE2",
            label=be2_label,
            why=be2_why,
            applicability="universal",
            evidence=[],
            reference_frame="company_history",
        )
    )

    # --- BE3 Pricing-power evidence ---
    posture = pricing.posture if pricing else "UNKNOWN"
    if posture == "NOT_APPLICABLE":
        be3_label = "NOT_APPLICABLE"
        be3_why = pricing.why if pricing else "Pricing power not thesis lens"
    elif posture in {"STRONG", "MODERATE"}:
        be3_label = "PASS"
        be3_why = f"Pricing posture={posture} (evidence-of-claim); {pricing.why if pricing else ''}"
    elif posture == "MIXED":
        be3_label = "MIXED"
        be3_why = f"Pricing posture=MIXED; {pricing.why if pricing else ''}"
    elif posture == "WEAK":
        be3_label = "BELOW_REFERENCE"
        be3_why = (
            "Pricing posture=WEAK vs archetype/history reference — evidence label only; "
            "WEAK ≠ kill / fail / RED"
        )
    else:
        be3_label = "UNKNOWN"
        be3_why = "Pricing-power evidence UNKNOWN — not invented"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BE3",
            label=be3_label,
            why=be3_why,
            applicability="near_universal",
            evidence=list((pricing.evidence if pricing else [])[:3]),
            reference_frame="archetype",
        )
    )

    # --- BE4 Cost advantage / scale / OL (P&L) ---
    if semantic and semantic.cost_advantage_notes:
        be4_label = "PASS"
        be4_why = f"Cost/scale/OL cues: {semantic.cost_advantage_notes[:180]}"
    elif (calc_metrics.get("incremental_om_windows") or []) and latest.get("opex_intensity") is not None:
        be4_label = "MIXED"
        be4_why = (
            "Opex intensity + incremental OM exhibits present (descriptive P&L leverage); "
            "full cost-advantage claim still disclosure-dependent"
        )
    else:
        be4_label = "UNKNOWN"
        be4_why = "Cost advantage / scale evidence thin — UNKNOWN honest"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BE4",
            label=be4_label,
            why=be4_why,
            applicability="near_universal",
            evidence=[],
            reference_frame="archetype",
        )
    )

    # --- BE5 Incremental OM ---
    iom = calc_metrics.get("incremental_om_windows") or []
    if iom and any(w.get("incremental_om") is not None for w in iom):
        classes = {w.get("posture_class") for w in iom}
        # Distorted windows (seasonality/one-off/extreme ratio honesty) → MIXED evidence, not a fail
        if "distorted" in classes:
            be5_label = "MIXED"
        else:
            be5_label = "PASS"
        be5_why = (
            f"Descriptive incremental OM windows={len(iom)}; classes={sorted(c for c in classes if c)}; "
            "no numeric IOM hurdle; Incremental OM ≠ ROIIC (Stage 6); "
            "distorted class = honesty flag not auto-fail"
        )
    elif latest.get("operating_income") is None or latest.get("revenue") is None:
        be5_label = "UNKNOWN"
        be5_why = "OP+revenue unavailable — incremental OM UNKNOWN"
    else:
        be5_label = "UNKNOWN"
        be5_why = "Insufficient multi-period OP/revenue for ΔOM exhibit"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BE5",
            label=be5_label,
            why=be5_why,
            applicability="conditional",
            evidence=[str(w)[:120] for w in iom[:2]],
            reference_frame="company_history",
        )
    )

    # --- BE6 Durability ---
    conf = durability.confidence if durability else "UNKNOWN"
    if conf in {"HIGH", "MEDIUM"}:
        be6_label = "PASS"
    elif conf == "LOW":
        be6_label = "MIXED"
    else:
        be6_label = "UNKNOWN"
    be6_why = (
        f"durability_confidence={conf}; lenses={durability.lenses_used if durability else []}. "
        "Confidence is not a score; no fake-precision moat width."
    )
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BE6",
            label=be6_label,
            why=be6_why,
            applicability="universal",
            evidence=list((durability.falsifiers if durability else [])[:2]),
            reference_frame="archetype",
        )
    )

    # --- BE7 FP load ---
    material = [t for t in fp_tags if t.get("severity") == "material"]
    if material:
        be7_label = "MIXED"
        be7_why = (
            f"Material FP tags={[t['id'] for t in material]} — evidence flags, not auto-fails; "
            "no FP score average; no count→outcome"
        )
    elif fp_tags:
        be7_label = "PASS"
        be7_why = (
            f"FP watches={[t['id'] for t in fp_tags]} (context/watchable) — catalogue philosophy; "
            "not auto-fails"
        )
    else:
        be7_label = "PASS"
        be7_why = "No FP tags raised from available evidence (catalogue still applies as monitors)"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BE7",
            label=be7_label,
            why=be7_why,
            applicability="universal",
            evidence=[t.get("id", "") for t in fp_tags],
            reference_frame="company_history",
        )
    )

    # --- BE8 Thesis coherence ---
    if thesis_coherence == "supports":
        be8_label = "PASS"
        be8_why = "Observed economics support Stage 1 thesis (contextual)"
    elif thesis_coherence == "strains":
        be8_label = "BELOW_REFERENCE"
        be8_why = "Economics evidence strains Stage 1 thesis — carry REVIEW if material"
        context_tags.append("CHALLENGE_ARCHETYPE")
    elif thesis_coherence == "falsifies":
        be8_label = "BELOW_REFERENCE"
        be8_why = "Economics evidence falsifies Stage 1 thesis — REVIEW carry-forward (non-terminating)"
        context_tags.append("CHALLENGE_ARCHETYPE")
    else:
        be8_label = "UNKNOWN"
        be8_why = "Stage 1 thesis pointer thin — coherence UNKNOWN"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BE8",
            label=be8_label,
            why=be8_why,
            applicability="universal",
            evidence=[f"coherence={thesis_coherence}", f"PRIMARY={primary}"],
            reference_frame="archetype",
        )
    )

    # --- Context tags (closed set) ---
    if primary == "A1":
        context_tags.append("MATURE_FRANCHISE_ECONOMICS_OK")
    if semantic and semantic.ses_notes:
        # SES evidence bar — proposal only; invalidators block
        invalidators = any(
            t.get("id") in {"FP2", "FP6"} and t.get("severity") == "material" for t in fp_tags
        )
        if not invalidators:
            context_tags.append("SCALE_ECONOMIES_SHARED_OK")
    if primary in {"A4", "A8", "A9"} or (semantic and semantic.cycle_peak_notes):
        context_tags.append("CYCLE_PEAK_MARGIN_RISK")
    if any(
        t.get("id") in {"FP4", "FP10"}
        or (t.get("id") == "FP5" and t.get("severity") == "material")
        for t in fp_tags
    ):
        if "ACCOUNTING_MARGIN_DISTORTION" not in context_tags:
            context_tags.append("ACCOUNTING_MARGIN_DISTORTION")
    if any(t.get("id") == "FP9" for t in fp_tags):
        context_tags.append("HIGH_MARGIN_QUALITY_RISK")

    # Peer secondary only
    if peer_notes:
        # Never peer-percentile primary — note only on BE1 reference frame if present
        pass

    # Enforce closed set
    context_tags = [t for t in dict.fromkeys(context_tags) if t in CONTEXT_TAGS]
    return results, context_tags
