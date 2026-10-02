"""Stage 4 Benchmark Layer BD1–BD9 — evidence labels + WHY. Not a hard gate.

Hierarchy: (1) archetype (2) company history (3) selective peer secondary.
No weighted/blended score, peer percentile grade, universal CAGR hurdle,
or automatic label-count → outcome logic. BD9 observational only (no ROIC).
NC* bands RESEARCH CANDIDATE / NOT LOCKED — never used as production gates.
"""
from __future__ import annotations

from typing import Any

from ..models import (
    ArchetypeAdaptation,
    BenchmarkDimensionResult,
    RunwayAssessment,
    Stage4SemanticReview,
)
from .questions import BENCHMARK_LABELS, FALSE_POSITIVE_CATALOGUE


def _latest_yoy_fraction(calc_metrics: dict[str, Any]) -> float | None:
    yoy = calc_metrics.get("latest_revenue_yoy") or {}
    return yoy.get("fraction")


def _tag_false_positives(
    *,
    calc_metrics: dict[str, Any],
    semantic: Stage4SemanticReview | None,
    archetype: ArchetypeAdaptation | None,
) -> list[dict[str, Any]]:
    """FP catalogue as evidence tags — NOT automatic fails."""
    tags: list[dict[str, Any]] = []
    catalog = {fid: desc for fid, desc in FALSE_POSITIVE_CATALOGUE}
    sem_topics = {f.topic for f in (semantic.findings if semantic else [])}

    # FP1 / FP8 — M&A cash without organic bridge
    ma = calc_metrics.get("ma_cash_fy_series") or []
    ma_present = any((r.get("value") or 0) and abs(r["value"]) > 0 for r in ma)
    organic = (calc_metrics.get("latest_optional_disclosed") or {}).get(
        "revenue_organic_growth_yoy"
    )
    if ma_present and organic is None:
        tags.append(
            {
                "id": "FP1",
                "description": catalog["FP1"],
                "severity": "watchable",
                "why": "M&A cash present without disclosed organic YoY in Normalized — honesty watch, not auto-fail",
                "counterexample": "Disciplined bolt-on extending known franchise",
            }
        )
        tags.append(
            {
                "id": "FP8",
                "description": catalog["FP8"],
                "severity": "watchable",
                "why": "Capital-bought top-line clue via M&A cash — returns → Stage 6; not Stage 4 kill",
                "counterexample": "Growth CapEx against proven demand",
            }
        )

    # FP3 — FX language without constant-currency Normalized
    if semantic and semantic.fx_notes:
        cc = (calc_metrics.get("latest_optional_disclosed") or {}).get(
            "constant_currency_revenue_growth_yoy"
        )
        if cc is None:
            tags.append(
                {
                    "id": "FP3",
                    "description": catalog["FP3"],
                    "severity": "watchable",
                    "why": "FX discussion in filings without Normalized constant-currency field — disclosure honesty",
                    "counterexample": "Local-currency volume also healthy",
                }
            )

    # FP5 — thin history / base effects
    flags = calc_metrics.get("history_flags") or {}
    if flags.get("history_thin") or flags.get("fy_used", 0) < 3:
        tags.append(
            {
                "id": "FP5",
                "description": catalog["FP5"],
                "severity": "watchable",
                "why": "Thin FY history — base-effect honesty required; not a fail bar",
                "counterexample": "Multi-year unit path still constructive",
            }
        )

    # FP7 — EPS vs NI divergence
    ni_eps = calc_metrics.get("ni_vs_eps_yoy")
    if ni_eps:
        ni_f = (ni_eps.get("ni_yoy") or {}).get("fraction")
        eps_f = (ni_eps.get("eps_yoy") or {}).get("fraction")
        share_dir = calc_metrics.get("share_count_direction")
        if (
            ni_f is not None
            and eps_f is not None
            and eps_f > ni_f
            and share_dir == "down"
        ):
            tags.append(
                {
                    "id": "FP7",
                    "description": catalog["FP7"],
                    "severity": "watchable",
                    "why": "EPS YoY outpaces NI YoY while share count down — dilution/shrink optics watch",
                    "counterexample": "Per-share and economic earnings both compound",
                }
            )

    # FP2 / FP10 — cycle language
    if "cycle_base_effect" in sem_topics or (
        archetype and archetype.primary_archetype in {"A4", "A8", "A9"}
    ):
        tags.append(
            {
                "id": "FP2",
                "description": catalog["FP2"],
                "severity": "watchable",
                "why": "Cyclical archetype or rebound language — do not treat rebound as franchise alone",
                "counterexample": "Share gains through cycle with volume evidence",
            }
        )
    if archetype and archetype.primary_archetype == "A4":
        tags.append(
            {
                "id": "FP10",
                "description": catalog["FP10"],
                "severity": "watchable",
                "why": "Semiconductor PRIMARY — peak YoY ≠ franchise; cycle-normalize",
                "counterexample": "Cycle-normalized share + backlog quality",
            }
        )

    # FP9 — SaaS vanity
    if archetype and archetype.primary_archetype == "A2":
        if "recurring_revenue" not in sem_topics and "backlog_rpo" not in sem_topics:
            tags.append(
                {
                    "id": "FP9",
                    "description": catalog["FP9"],
                    "severity": "watchable",
                    "why": "SaaS archetype without retention/RPO evidence in semantic — vanity-metric watch",
                    "counterexample": "Strong net retention + efficient expansion",
                }
            )

    # FP13 — mature low growth (context — prevents false punishment)
    # Tagged as awareness that low growth ≠ fail for mature; actual MATURE_FRANCHISE_OK is context tag
    if archetype and archetype.primary_archetype == "A1":
        tags.append(
            {
                "id": "FP13",
                "description": catalog["FP13"],
                "severity": "context",
                "why": "Mature branded consumer — do not fail solely for modest headline growth",
                "counterexample": "Thesis-consistent modest growth + durability",
            }
        )

    if "fp_channel_stuffing" in sem_topics:
        tags.append(
            {
                "id": "FP6",
                "description": catalog["FP6"],
                "severity": "material",
                "why": "Channel stuffing / pull-forward language extracted — evidence tag, not auto-fail",
                "counterexample": "Sell-out / deferred revenue confirms demand",
            }
        )

    return tags


def assess_runway(
    *,
    archetype: ArchetypeAdaptation | None,
    semantic: Stage4SemanticReview | None,
    thesis_runway: str | None,
    calc_metrics: dict[str, Any],
) -> RunwayAssessment:
    """Structured runway evidence + confidence — not a score; no fake year counts."""
    lenses: list[str] = []
    fact: list[str] = []
    guidance: list[str] = []
    external: list[str] = []
    inference: list[str] = []
    falsifiers: list[str] = [
        "Category shrinkage or share loss without pricing power",
        "Dilutive share issuance without economic earnings growth",
        "Cyclical peak mistaken for structural demand",
    ]

    primary = archetype.primary_archetype if archetype else "A11"
    if primary == "A1":
        lenses += ["mature_compounder", "geo_white_space", "product_adjacency"]
    elif primary == "A2":
        lenses += ["usage_wallet", "product_adjacency"]
    elif primary == "A3":
        lenses += ["usage_wallet", "geo_white_space"]
    elif primary in {"A4", "A5"}:
        lenses += ["capacity_limited_demand", "product_adjacency"]
    elif primary == "A6":
        lenses += ["penetration_density", "geo_white_space"]
    elif primary == "A9":
        lenses += ["capacity_limited_demand"]
    else:
        lenses += ["product_adjacency"]

    if thesis_runway:
        guidance.append(f"Stage 1 G2-M4 runway story: {thesis_runway[:300]}")
    if semantic and semantic.runway_claim_notes:
        guidance.append(f"MD&A/IR runway language: {semantic.runway_claim_notes[:240]}")
        # Uncited TAM as FACT is forbidden — treat TAM hits as COMPANY_EXPLANATION/guidance
        if re_search_tam(semantic.runway_claim_notes):
            guidance.append(
                "TAM language present — treated as COMPANY_EXPLANATION/GUIDANCE, not FACT"
            )
    if semantic and semantic.geography_product_notes:
        fact.append(f"Geo/product disclosure: {semantic.geography_product_notes[:200]}")
    if semantic and semantic.backlog_rpo_notes:
        fact.append(f"Backlog/RPO: {semantic.backlog_rpo_notes[:200]}")

    path = calc_metrics.get("revenue_path_consistency")
    if path and path != "UNKNOWN":
        fact.append(f"Revenue YoY sign path consistency={path} (descriptive)")

    # Confidence from evidence richness — not a numeric scorecard
    n_ev = len(fact) + len(guidance)
    flags = calc_metrics.get("history_flags") or {}
    if n_ev >= 3 and not flags.get("history_thin"):
        confidence = "MEDIUM"
    elif n_ev >= 1:
        confidence = "MEDIUM" if thesis_runway else "LOW"
    else:
        confidence = "UNKNOWN"

    # Young / thin history bias toward UNKNOWN/LOW
    if flags.get("history_thin"):
        confidence = "LOW" if confidence != "UNKNOWN" else "UNKNOWN"
        inference.append("Thin history → lower runway confidence (not a fail bar)")

    if primary in {"A8", "A9", "A4"}:
        inference.append("Cyclical/semi archetype — runway confidence tempered by cycle position")
        if confidence == "MEDIUM":
            confidence = "LOW"

    summary = (
        f"Runway lenses={lenses}; confidence={confidence}; "
        f"evidence FACT={len(fact)} GUIDANCE={len(guidance)} INFERENCE={len(inference)}. "
        "No fake-precision year forecast."
    )
    return RunwayAssessment(
        summary=summary,
        lenses_used=lenses,
        confidence=confidence,
        falsifiers=falsifiers,
        thesis_link=thesis_runway,
        fact_evidence=fact,
        guidance_evidence=guidance,
        external_evidence=external,
        inference_evidence=inference,
    )


def re_search_tam(text: str) -> bool:
    import re

    return bool(re.search(r"\btotal\s+addressable\s+market\b|\bTAM\b", text or "", re.I))


def label_benchmarks(
    *,
    calc_metrics: dict[str, Any],
    archetype: ArchetypeAdaptation | None,
    semantic: Stage4SemanticReview | None,
    runway: RunwayAssessment | None,
    fp_tags: list[dict[str, Any]],
    thesis_coherence: str,
    peer_notes: str | None = None,
) -> tuple[list[BenchmarkDimensionResult], list[str]]:
    """
    Produce BD1–BD9 labels + WHY. Context tags returned separately.
    FORBIDDEN: counting labels to force outcomes (evaluator must not do that either).
    """
    results: list[BenchmarkDimensionResult] = []
    context_tags: list[str] = []
    primary = archetype.primary_archetype if archetype else "A11"
    latest_frac = _latest_yoy_fraction(calc_metrics)
    path = calc_metrics.get("revenue_path_consistency") or "UNKNOWN"
    hist = calc_metrics.get("history_flags") or {}

    # --- BD1 Headline growth reality ---
    bd1_label = "UNKNOWN"
    bd1_why = "Insufficient multi-period revenue path"
    if latest_frac is not None:
        if primary == "A1":
            # Mature franchise: modest growth can still be PASS — numeric bands NOT LOCKED
            bd1_label = "PASS"
            bd1_why = (
                f"Mature branded consumer frame: latest revenue YoY fraction={latest_frac:.4f} "
                f"(descriptive); path={path}. Modest headline growth not below-reference alone. "
                "NC* bands NOT LOCKED — no universal CAGR hurdle."
            )
            context_tags.append("MATURE_FRANCHISE_OK")
        elif primary in {"A4", "A8", "A9"}:
            bd1_label = "MIXED"
            bd1_why = (
                f"Cyclical/semi/travel frame: latest YoY={latest_frac:.4f}; path={path}. "
                "Peak/rebound honesty required — not ABOVE_REFERENCE from headline alone."
            )
        elif abs(latest_frac) > 0.25:
            bd1_label = "ABOVE_REFERENCE"
            bd1_why = (
                f"High headline YoY fraction={latest_frac:.4f} vs archetype {primary} — "
                "still check FP/dilution/cycle (not auto quality)."
            )
            context_tags.append("HIGH_GROWTH_QUALITY_RISK")
        else:
            bd1_label = "PASS"
            bd1_why = (
                f"Headline YoY={latest_frac:.4f}; path={path}; archetype={primary}. "
                "Descriptive consistency — not a hurdle score."
            )
    if hist.get("history_thin"):
        if bd1_label == "UNKNOWN":
            bd1_why += " Thin FY history."
        else:
            bd1_why += " History thinner than ~5 FY preference (flag only)."
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD1",
            label=bd1_label,
            why=bd1_why,
            applicability="universal",
            evidence=[f"latest_yoy={latest_frac}", f"path={path}"],
            reference_frame="archetype",
        )
    )

    # --- BD2 Organic vs acquired ---
    opt = calc_metrics.get("latest_optional_disclosed") or {}
    ma_present = any(
        (r.get("value") or 0) and abs(r["value"]) > 0
        for r in (calc_metrics.get("ma_cash_fy_series") or [])
    )
    if opt.get("revenue_organic_growth_yoy") is not None or opt.get(
        "revenue_acquired_impact_yoy"
    ) is not None:
        bd2_label = "PASS"
        bd2_why = (
            f"Disclosed organic={opt.get('revenue_organic_growth_yoy')}; "
            f"acquired={opt.get('revenue_acquired_impact_yoy')} — FACT Normalized"
        )
    elif semantic and semantic.organic_acquired_notes:
        bd2_label = "MIXED"
        bd2_why = (
            "Organic/acquired discussed in MD&A (COMPANY_EXPLANATION) without Normalized "
            "organic field — honesty partial"
        )
    elif not ma_present:
        bd2_label = "NOT_APPLICABLE"
        bd2_why = "No material M&A cash in window — inorganic depth NOT_APPLICABLE; organic honesty still UNKNOWN without disclosure"
        # Actually Plan: BD2 universal honesty; inorganic depth conditional.
        # Re-label: honesty UNKNOWN if no organic disclosure; N/A for inorganic detail
        bd2_label = "UNKNOWN"
        bd2_why = (
            "Organic bridge not disclosed in Normalized; no M&A cash — inorganic detail "
            "NOT_APPLICABLE; organic honesty remains UNKNOWN (not invented)"
        )
    else:
        bd2_label = "BELOW_REFERENCE"
        bd2_why = (
            "M&A cash present without organic bridge disclosure — composition honesty weak "
            "(evidence label, not auto-reject)"
        )
    if not ma_present:
        bd2_why += "; inorganic depth detail NOT_APPLICABLE (no M&A cash)"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD2",
            label=bd2_label,
            why=bd2_why,
            applicability="universal_honesty",
            evidence=[
                f"organic={opt.get('revenue_organic_growth_yoy')}",
                f"ma_present={ma_present}",
            ],
            reference_frame="archetype",
        )
    )

    # --- BD3 Volume/price/mix/FX ---
    if (
        opt.get("volume_metric") is not None
        or opt.get("constant_currency_revenue_growth_yoy") is not None
        or (semantic and (semantic.volume_price_mix_notes or semantic.fx_notes))
    ):
        bd3_label = "PASS" if opt.get("volume_metric") is not None else "MIXED"
        bd3_why = (
            "Volume/price/mix/FX disclosure present "
            f"(volume={opt.get('volume_metric')}; cc={opt.get('constant_currency_revenue_growth_yoy')}; "
            f"semantic_vpm={bool(semantic.volume_price_mix_notes if semantic else False)}; "
            f"semantic_fx={bool(semantic.fx_notes if semantic else False)})"
        )
    else:
        bd3_label = "UNKNOWN"
        bd3_why = "Volume/price/mix/FX not disclosed in Normalized and no semantic hit — conditional UNKNOWN"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD3",
            label=bd3_label,
            why=bd3_why,
            applicability="conditional",
            evidence=[],
            reference_frame="company_history",
        )
    )

    # --- BD4 Owner growth / dilution ---
    # Descriptive only — NEVER mechanical buyback=good / dilution=bad.
    share_dir = calc_metrics.get("share_count_direction")
    share_concept = calc_metrics.get("share_concept_label") or calc_metrics.get(
        "share_concept_used_for_bd4"
    )
    abs_vs = calc_metrics.get("absolute_vs_per_share_growth") or []
    latest_abs_vs = abs_vs[-1] if abs_vs else None
    if share_dir == "UNKNOWN":
        bd4_label = "UNKNOWN"
        bd4_why = (
            "Share count not disclosed (diluted/basic weighted-average absent) — "
            "owner-growth / dilution path UNKNOWN; period-end outstanding alone is not used"
        )
    else:
        bd4_label = "PASS"
        bd4_why = (
            f"Owner-growth exhibit present using concept={share_concept}; "
            f"share_direction={share_dir}; delta={calc_metrics.get('share_count_delta')}; "
            "absolute vs per-share growth computed when inputs exist. "
            "Descriptive only — NOT mechanical buyback=good / dilution=bad."
        )
        if latest_abs_vs:
            ni_abs = (latest_abs_vs.get("ni_abs_yoy") or {}).get("fraction")
            ni_ps = (latest_abs_vs.get("ni_ps_yoy") or {}).get("fraction")
            if ni_abs is not None or ni_ps is not None:
                bd4_why += f" Latest NI abs_yoy_frac={ni_abs}; NI/share_yoy_frac={ni_ps}."
        # FP7 already tagged separately — optics watch, not auto fail
        if any(t.get("id") == "FP7" for t in fp_tags):
            bd4_label = "MIXED"
            bd4_why += " FP7 watch (EPS vs NI optics) — still not mechanical good/bad."
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD4",
            label=bd4_label,
            why=bd4_why,
            applicability="universal",
            evidence=[
                f"share_dir={share_dir}",
                f"share_concept={share_concept}",
            ],
            reference_frame="company_history",
        )
    )

    # --- BD5 Runway residual + confidence ---
    conf = runway.confidence if runway else "UNKNOWN"
    if conf in {"HIGH", "MEDIUM"}:
        bd5_label = "PASS"
    elif conf == "LOW":
        bd5_label = "MIXED"
    else:
        bd5_label = "UNKNOWN"
    bd5_why = (
        f"Runway confidence={conf}; lenses={runway.lenses_used if runway else []}. "
        "Confidence is not a score; no fake year precision."
    )
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD5",
            label=bd5_label,
            why=bd5_why,
            applicability="universal",
            evidence=list((runway.fact_evidence if runway else [])[:3]),
            reference_frame="archetype",
        )
    )

    # --- BD6 Thesis / archetype coherence ---
    if thesis_coherence == "supports":
        bd6_label = "PASS"
        bd6_why = "Observed growth supports Stage 1 / G2-M4 thesis (contextual)"
    elif thesis_coherence == "strains":
        bd6_label = "BELOW_REFERENCE"
        bd6_why = "Growth evidence strains Stage 1 thesis — carry REVIEW if material"
        context_tags.append("CHALLENGE_ARCHETYPE")
    elif thesis_coherence == "falsifies":
        bd6_label = "BELOW_REFERENCE"
        bd6_why = "Growth evidence falsifies Stage 1 thesis — REVIEW_REQUIRED carry-forward"
        context_tags.append("CHALLENGE_ARCHETYPE")
    else:
        bd6_label = "UNKNOWN"
        bd6_why = "Thesis coherence not fully resolved — human judgment on S4-M6"
    if archetype and archetype.classification_path == "REVIEW_REQUIRED":
        context_tags.append("CHALLENGE_ARCHETYPE")
        bd6_why += f"; archetype path={archetype.classification_path}"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD6",
            label=bd6_label,
            why=bd6_why,
            applicability="universal",
            evidence=[f"coherence={thesis_coherence}", f"primary={primary}"],
            reference_frame="archetype",
        )
    )

    # --- BD7 False-positive load (no FP score average) ---
    material_fps = [t for t in fp_tags if t.get("severity") == "material"]
    watch_fps = [t for t in fp_tags if t.get("severity") == "watchable"]
    if material_fps:
        bd7_label = "MIXED"
        bd7_why = (
            f"Material FP tags={[t['id'] for t in material_fps]} — evidence, not auto-fail; "
            f"watchable={[t['id'] for t in watch_fps]}"
        )
    elif watch_fps:
        bd7_label = "PASS"
        bd7_why = (
            f"Watchable FP tags={[t['id'] for t in watch_fps]} — catalogue philosophy; "
            "no FP score average; not count→outcome"
        )
    else:
        bd7_label = "PASS"
        bd7_why = "No material/watchable FP tags raised from available evidence"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD7",
            label=bd7_label,
            why=bd7_why,
            applicability="universal",
            evidence=[t["id"] for t in fp_tags],
            reference_frame="archetype",
        )
    )

    # --- BD8 Category / share (SHOULD) ---
    if peer_notes:
        bd8_label = "PASS"
        bd8_why = f"Selective peer/category note present (secondary): {peer_notes[:200]}"
        ref = "peer_secondary"
    elif semantic and any(f.topic == "category_share" for f in semantic.findings):
        bd8_label = "MIXED"
        bd8_why = "Category/share language in filings — company-disclosed; not peer percentile grade"
        ref = "company_history"
    else:
        bd8_label = "UNKNOWN"
        bd8_why = (
            "Category/share peer set not assessed — SHOULD gap; "
            "never peer-percentile primary judgment"
        )
        ref = "peer_secondary"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD8",
            label=bd8_label,
            why=bd8_why,
            applicability="should",
            evidence=[],
            reference_frame=ref,
        )
    )

    # --- BD9 Capital-intensity pattern only (no ROIC) ---
    cip = calc_metrics.get("capital_intensity_pattern") or {}
    if cip.get("capex") is not None or cip.get("business_acquisitions_cash") is not None:
        bd9_label = "PASS"
        bd9_why = (
            f"CapEx/revenue pattern={cip.get('capex_to_revenue')}; "
            f"M&A cash={cip.get('business_acquisitions_cash')}. "
            "Observational only — incremental returns → Stage 6; no ROIC math here."
        )
    else:
        bd9_label = "NOT_APPLICABLE"
        bd9_why = "CapEx/M&A pattern fields thin — BD9 NOT_APPLICABLE this window"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="BD9",
            label=bd9_label,
            why=bd9_why,
            applicability="pattern_only",
            evidence=[str(cip)],
            reference_frame="company_history",
        )
    )

    # Dedupe context tags preserving order
    seen: set[str] = set()
    ctx = []
    for t in context_tags:
        if t not in seen:
            seen.add(t)
            ctx.append(t)

    # Validate labels
    for r in results:
        assert r.label in BENCHMARK_LABELS, r.label
        assert r.dimension_id in {
            "BD1", "BD2", "BD3", "BD4", "BD5", "BD6", "BD7", "BD8", "BD9"
        }, r.dimension_id

    return results, ctx


# Public helper used by tests to prove no count→outcome engine lives here
def count_labels(results: list[BenchmarkDimensionResult]) -> dict[str, int]:
    """Diagnostic only — MUST NOT be used to decide process outcomes."""
    out: dict[str, int] = {}
    for r in results:
        out[r.label] = out.get(r.label, 0) + 1
    return out
