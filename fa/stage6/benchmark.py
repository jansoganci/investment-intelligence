"""Stage 6 Benchmark Layer RC1–RC8 — evidence labels + WHY. Not a hard gate.

Method E: archetype → company history → selective peer (never peer-primary).
No weighted score, no numeric ROIC/ROIIC/WACC bands, no label-count→outcome.
"""
from __future__ import annotations

from typing import Any

from ..models import (
    ArchetypeAdaptation,
    BenchmarkDimensionResult,
    Stage6SemanticReview,
)
from .questions import FALSE_POSITIVE_CATALOGUE, RC_DIMENSIONS


def _tag_false_positives(
    *,
    calc_metrics: dict[str, Any],
    semantic: Stage6SemanticReview | None,
    archetype: ArchetypeAdaptation | None,
) -> list[dict[str, Any]]:
    """FP-R catalogue as evidence tags — NOT automatic fails. No FP score average."""
    tags: list[dict[str, Any]] = []
    catalog = {fid: desc for fid, desc in FALSE_POSITIVE_CATALOGUE}
    sem_topics = {f.topic for f in (semantic.findings if semantic else [])}
    primary = archetype.primary_archetype if archetype else "A11"
    dual = calc_metrics.get("dual_roic") or {}
    windows = calc_metrics.get("incremental_roic_windows") or []
    reinv = calc_metrics.get("reinvestment_composition") or {}

    if primary in {"A4", "A8", "A9"}:
        tags.append(
            {
                "id": "FP-R1",
                "description": catalog["FP-R1"],
                "severity": "watchable",
                "why": "Cyclical archetype — do not treat peak ROIC as franchise alone",
                "counterexample": "Through-cycle capital returns disclosed",
            }
        )

    if "capex_productivity" in sem_topics and (
        (calc_metrics.get("latest_capital") or {}).get("capex") is not None
        and abs((calc_metrics.get("latest_capital") or {}).get("capex") or 0) < 1
    ):
        tags.append(
            {
                "id": "FP-R2",
                "description": catalog["FP-R2"],
                "severity": "watchable",
                "why": "Near-zero CapEx with productivity language — CapEx holiday watch",
                "counterexample": "Sustaining CapEx stable vs capacity",
            }
        )

    if dual.get("dual_view_emitted") and dual.get("roic_tangible") is not None:
        # Conflict watch: if inclusive weak optics vs tangible strong — don't hide
        ri = dual.get("roic_inclusive")
        rt = dual.get("roic_tangible")
        if ri is not None and rt is not None and rt > 0 and (ri is None or ri < 0.5 * rt):
            tags.append(
                {
                    "id": "FP-R3",
                    "description": catalog["FP-R3"],
                    "severity": "material",
                    "why": "Tangible companion much higher than inclusive — dual-view conflict must stay visible",
                    "counterexample": "Both views presented with acquisition narrative",
                }
            )

    if "lease_asc842" in sem_topics or "accounting_distortion" in sem_topics:
        tags.append(
            {
                "id": "FP-R4",
                "description": catalog["FP-R4"],
                "severity": "watchable",
                "why": "Lease/accounting break language — incremental windows may be distorted",
                "counterexample": "ASC 842 adoption year labeled and spliced honestly",
            }
        )

    if any(w.get("meaning_class") == "not_meaningful" for w in windows):
        tags.append(
            {
                "id": "FP-R7",
                "description": catalog["FP-R7"],
                "severity": "watchable",
                "why": "ΔIC≈0 / not_meaningful incremental — capital-light pathology honesty",
                "counterexample": "Level ROIC still definition-honest; runway/outlets noted",
            }
        )

    if primary == "A2" or (
        (calc_metrics.get("latest_capital") or {}).get("nopat") is not None
        and semantic
        and semantic.fp_explanation_notes
        and "sbc" in (semantic.fp_explanation_notes or "").lower()
    ):
        tags.append(
            {
                "id": "FP-R8",
                "description": catalog["FP-R8"],
                "severity": "watchable",
                "why": "SaaS/SBC context — NOPAT theatre watch; no cash-tax/SBC surgery in v1",
                "counterexample": "SBC companion note aligned with reported OP story",
            }
        )

    wc = calc_metrics.get("wc_metrics") or {}
    if wc.get("latest_wc_proxy") is not None and wc["latest_wc_proxy"] < 0:
        tags.append(
            {
                "id": "FP-R9",
                "description": catalog["FP-R9"],
                "severity": "watchable",
                "why": "Negative WC proxy present — never auto-reward as quality",
                "counterexample": "Deferred revenue / payables mechanism durable and disclosed",
            }
        )

    if primary == "A7" or "ppa_acquisition" in sem_topics or "acquisition_context" in sem_topics:
        tags.append(
            {
                "id": "FP-R10",
                "description": catalog["FP-R10"],
                "severity": "watchable",
                "why": "Acquisitive / PPA context — acquisition stub optics; tangible ≠ M&A success",
                "counterexample": "Deal-lag narrative + inclusive primary both shown",
            }
        )

    if semantic and semantic.investment_phase_notes:
        tags.append(
            {
                "id": "FP-R12",
                "description": catalog["FP-R12"],
                "severity": "watchable",
                "why": "Investment-phase language — do not auto-read as permanent value destruction",
                "counterexample": "Multi-year incremental remains poor after gestation → D10 path",
            }
        )

    if "impairment" in sem_topics or (semantic and semantic.impairment_notes):
        tags.append(
            {
                "id": "FP-R6",
                "description": catalog["FP-R6"],
                "severity": "watchable",
                "why": "Impairment language — ROIC may look improved after write-downs",
                "counterexample": "Impairment-adjusted incremental classed distorted/not_meaningful",
            }
        )

    runway_hint = (semantic.runway_notes if semantic else None) or ""
    if dual.get("roic_inclusive") is not None and (
        "limited" in runway_hint.lower() or "distrib" in runway_hint.lower()
    ):
        tags.append(
            {
                "id": "FP-R11",
                "description": catalog["FP-R11"],
                "severity": "watchable",
                "why": "High ROIC optics with limited-runway language — melting ice cube watch (not a Stage 6 fail)",
                "counterexample": "Distribute logic acknowledged; Stage 7/8 own allocator/valuation",
            }
        )

    if reinv.get("maint_capex_status") == "UNKNOWN" and primary in {"A5", "A8", "A9"}:
        # Not an FP itself — disclosure gap handled elsewhere
        pass

    return tags


def assess_runway(
    *,
    semantic: Stage6SemanticReview | None,
    archetype: ArchetypeAdaptation | None,
    calc_metrics: dict[str, Any],
) -> tuple[str, list[str]]:
    """Evidence label only: ample|limited|unclear|not_applicable. Not an outcome."""
    why: list[str] = []
    primary = archetype.primary_archetype if archetype else "A11"
    notes = (semantic.runway_notes if semantic else None) or ""
    dest = (semantic.capital_destination_notes if semantic else None) or ""
    blob = f"{notes} {dest}".lower()
    reinv = calc_metrics.get("reinvestment_composition") or {}
    acq = reinv.get("business_acquisitions_cash")
    capex = reinv.get("organic_capex")

    if primary in {"A1"} and (
        "distribut" in blob or "repurchase" in blob or "dividend" in blob
    ):
        why.append("Mature franchise + distribute/repurchase language → limited runway lean")
        return "limited", why
    if "limited runway" in blob or "few reinvestment" in blob:
        why.append("Explicit limited-runway language in semantic")
        return "limited", why
    if "ample" in blob or "significant reinvestment opportunit" in blob:
        why.append("Ample reinvestment opportunity language")
        return "ample", why
    if primary == "A7" and acq is not None and abs(acq) > 0:
        why.append("A7 with ongoing acquisition capital — runway via M&A outlets (unclear organic)")
        return "unclear", why
    if primary in {"A2", "A3"} and (capex is None or abs(capex or 0) == 0):
        why.append("Capital-light archetype; organic CapEx thin — runway via other outlets unclear")
        return "unclear", why
    if not notes and not dest:
        why.append("No runway disclosure cues — unclear")
        return "unclear", why
    why.append("Default unclear pending fuller disclosure")
    return "unclear", why


def label_benchmarks(
    *,
    calc_metrics: dict[str, Any],
    archetype: ArchetypeAdaptation | None,
    semantic: Stage6SemanticReview | None,
    fp_tags: list[dict[str, Any]],
    thesis_coherence: str,
    runway_label: str,
    peer_notes: str | None = None,
) -> list[BenchmarkDimensionResult]:
    """RC1–RC8 evidence labels + WHY. Method E. ≠ hard gate."""
    dual = calc_metrics.get("dual_roic") or {}
    windows = calc_metrics.get("incremental_roic_windows") or []
    primary = archetype.primary_archetype if archetype else "A11"
    results: list[BenchmarkDimensionResult] = []

    # RC1 Current ROIC reality
    if dual.get("roic_inclusive") is not None:
        why = (
            f"Inclusive ROIC={dual.get('roic_inclusive')}; "
            f"tax_source={dual.get('tax_rate_source')}; "
            f"avg_ic_method={dual.get('average_ic_method')}; "
            f"dual_emitted={dual.get('dual_view_emitted')} "
            "(descriptive; no universal ROIC hurdle)"
        )
        label = "PASS"
        if dual.get("dual_view_mandatory") and dual.get("roic_tangible") is None:
            label = "MIXED"
            why += "; A7 mandatory dual incomplete"
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC1",
                label=label,
                why=why,
                applicability="universal",
                evidence=[str(dual.get("definition_labels"))],
                reference_frame="company_history",
            )
        )
    else:
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC1",
                label="UNKNOWN",
                why="ROIC inclusive not computable — missing NOPAT/IC inputs",
                applicability="universal",
                reference_frame="company_history",
            )
        )

    # RC2 Incremental meaning
    if windows:
        primary_w = next(
            (w for w in windows if w.get("window_id") == "cumulative_3y"),
            windows[-1],
        )
        mc = primary_w.get("meaning_class") or "unknown"
        label_map = {
            "structurally_informative": "PASS",
            "noisy": "MIXED",
            "distorted": "MIXED",
            "not_meaningful": "NOT_APPLICABLE",
            "unknown": "UNKNOWN",
        }
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC2",
                label=label_map.get(mc, "UNKNOWN"),
                why=(
                    f"Primary incremental window={primary_w.get('window_id')}; "
                    f"meaning_class={mc}; ≠ Stage 5 IOM; no numeric ROIIC hurdle"
                ),
                applicability="universal",
                evidence=[str(primary_w)[:200]],
                reference_frame="company_history",
            )
        )
    else:
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC2",
                label="UNKNOWN",
                why="No incremental ROIC windows — insufficient FY depth",
                applicability="universal",
                reference_frame="company_history",
            )
        )

    # RC3 Runway
    runway_label_map = {
        "ample": "PASS",
        "limited": "MIXED",  # limited ≠ fail (Buffett distribute)
        "unclear": "UNKNOWN",
        "not_applicable": "NOT_APPLICABLE",
    }
    results.append(
        BenchmarkDimensionResult(
            dimension_id="RC3",
            label=runway_label_map.get(runway_label, "UNKNOWN"),
            why=f"Runway evidence label={runway_label} (not an outcome; high ROIC+limited ≠ Stage 6 fail)",
            applicability="universal",
            reference_frame="archetype",
        )
    )

    # RC4 Organic vs acquisition honesty
    if primary == "A7" or dual.get("dual_view_mandatory"):
        label = "PASS" if dual.get("dual_view_emitted") else "BELOW_REFERENCE"
        why = (
            f"A7/acquisitive dual spine mandatory; dual_emitted={dual.get('dual_view_emitted')}; "
            "tangible ≠ M&A success"
        )
    elif dual.get("dual_view_emitted"):
        label = "PASS"
        why = "Dual view emitted due to GW/intangibles materiality"
    else:
        label = "NOT_APPLICABLE"
        why = "No material GW/intangibles — single primary view"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="RC4",
            label=label,
            why=why,
            applicability="conditional",
            reference_frame="archetype",
        )
    )

    # RC5 CapEx productivity
    latest = calc_metrics.get("latest_capital") or {}
    if semantic and (
        any(f.topic == "capex_productivity" for f in semantic.findings)
        or semantic.maint_growth_capex_notes
    ):
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC5",
                label="MIXED",
                why="CapEx productivity cues present — evidence notes only; not a score",
                applicability="universal",
                reference_frame="company_history",
            )
        )
    elif latest.get("capex") is not None:
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC5",
                label="PASS",
                why=f"CapEx present ({latest.get('capex')}); CapEx/D&A={latest.get('capex_to_da')} descriptive only",
                applicability="universal",
                reference_frame="company_history",
            )
        )
    else:
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC5",
                label="UNKNOWN",
                why="CapEx not in Normalized — productivity UNKNOWN; no forced maint CapEx",
                applicability="universal",
                reference_frame="company_history",
            )
        )

    # RC6 WC mechanism
    wc = calc_metrics.get("wc_metrics") or {}
    if wc.get("latest_wc_proxy") is not None:
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC6",
                label="PASS",
                why=(
                    f"WC proxy={wc.get('latest_wc_proxy')}; delta={wc.get('delta_wc')}; "
                    "mechanism-first; never auto-reward negative WC"
                ),
                applicability="universal",
                reference_frame="company_history",
            )
        )
    else:
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC6",
                label="UNKNOWN",
                why="WC components thin — mechanism UNKNOWN",
                applicability="universal",
                reference_frame="company_history",
            )
        )

    # RC7 Accounting distortion
    material_fp = [t for t in fp_tags if t.get("severity") == "material"]
    if material_fp or (
        semantic
        and (
            semantic.distortion_notes
            or semantic.impairment_notes
            or semantic.lease_accounting_notes
        )
    ):
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC7",
                label="MIXED",
                why=f"Distortion/FP materiality cues present; FP={[t['id'] for t in fp_tags]}",
                applicability="universal",
                reference_frame="company_history",
            )
        )
    else:
        results.append(
            BenchmarkDimensionResult(
                dimension_id="RC7",
                label="PASS",
                why="No material accounting-distortion flags tagged (honesty still required)",
                applicability="universal",
                reference_frame="company_history",
            )
        )

    # RC8 Thesis coherence
    coh_map = {
        "supports": "PASS",
        "strains": "MIXED",
        "falsifies": "BELOW_REFERENCE",
        "unknown": "UNKNOWN",
    }
    results.append(
        BenchmarkDimensionResult(
            dimension_id="RC8",
            label=coh_map.get(thesis_coherence, "UNKNOWN"),
            why=f"Thesis capital-destination coherence={thesis_coherence}; peer_notes secondary only",
            applicability="universal",
            evidence=[peer_notes[:160]] if peer_notes else [],
            reference_frame="archetype",
        )
    )

    assert [r.dimension_id for r in results] == [d[0] for d in RC_DIMENSIONS]
    return results
