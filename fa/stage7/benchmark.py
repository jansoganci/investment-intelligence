"""Stage 7 Benchmark Layer MG1–MG9 — evidence labels + WHY. Not a hard gate.

Method E: archetype → company own history → stated policy → selective peer.
No weighted score, no ISS/pay-percentile gates, no label-count→outcome.
"""
from __future__ import annotations

from typing import Any

from ..models import (
    ArchetypeAdaptation,
    BenchmarkDimensionResult,
    Stage7SemanticReview,
)
from .questions import FALSE_POSITIVE_CATALOGUE, MG_BENCHMARK_DIMENSIONS, S6_H7_CONSUMABLE
from .semantic import incentive_evidence_depth


def _tag_false_positives(
    *,
    calc_metrics: dict[str, Any],
    semantic: Stage7SemanticReview | None,
    archetype: ArchetypeAdaptation | None,
    s6_flags: list[str],
) -> list[dict[str, Any]]:
    """FP-M catalogue as evidence tags — NOT automatic fails. No FP score average."""
    tags: list[dict[str, Any]] = []
    catalog = {fid: desc for fid, desc in FALSE_POSITIVE_CATALOGUE}
    sem_topics = {f.topic for f in (semantic.findings if semantic else [])}
    primary = archetype.primary_archetype if archetype else "A11"
    share = calc_metrics.get("share_trend") or {}
    hierarchy = calc_metrics.get("revealed_hierarchy") or {}
    div_years = calc_metrics.get("dividend_years_positive") or 0
    bb_years = calc_metrics.get("buyback_years_positive") or 0
    motives = calc_metrics.get("debt_motive_tags") or []

    if primary in {"A7", "A11"} or "succession" in sem_topics or (
        semantic and semantic.succession_notes and "founder" in (semantic.succession_notes or "").lower()
    ):
        if "governance_structure" in sem_topics or (
            semantic and semantic.governance_structure_notes
            and "founder" in (semantic.governance_structure_notes or "").lower()
        ):
            tags.append(
                {
                    "id": "FP-M1",
                    "description": catalog["FP-M1"],
                    "severity": "watchable",
                    "why": "Founder/charisma language present — do not equate with owner alignment",
                    "counterexample": "Related-party + allocation evidence both clean",
                }
            )

    if bb_years >= 2 or (share.get("gross_repurchase_multi_year") or 0) > 0:
        tags.append(
            {
                "id": "FP-M2",
                "description": catalog["FP-M2"],
                "severity": "watchable",
                "why": "Buybacks present — size ≠ shareholder-friendly; check net share + SBC + debt",
                "counterexample": "Net share decline with FCF-funded opportunistic policy",
            }
        )

    if div_years == 0 and bb_years >= 1:
        tags.append(
            {
                "id": "FP-M3",
                "description": catalog["FP-M3"],
                "severity": "watchable",
                "why": "No dividend with buybacks — may be rational high-return reinvestment; not unfriendly auto",
                "counterexample": "Hierarchy fit vs Stage 6 runway supports distribute later",
            }
        )

    if div_years >= 3:
        tags.append(
            {
                "id": "FP-M4",
                "description": catalog["FP-M4"],
                "severity": "watchable",
                "why": "Multi-year dividends — aristocrat optics ≠ disciplined allocator alone",
                "counterexample": "Hierarchy + CapEx honesty support residual/commitment policy",
            }
        )

    if "deal_criteria" in sem_topics or "S6_H7_ACQ_RETURN_OPACITY" in s6_flags:
        tags.append(
            {
                "id": "FP-M5",
                "description": catalog["FP-M5"],
                "severity": "watchable"
                if "S6_H7_ACQ_RETURN_OPACITY" not in s6_flags
                else "material",
                "why": "Synergy/deal language or S6 acquisition opacity — CLAIM ≠ post-deal FACTS",
                "counterexample": "Post-deal accountability + impairment honesty disclosed",
            }
        )

    if "incentive_metrics" in sem_topics or (
        semantic and semantic.incentive_metrics_notes
    ):
        blob = (semantic.incentive_metrics_notes or "").lower() if semantic else ""
        if "roic" in blob or "tsr" in blob or "adjusted" in blob:
            tags.append(
                {
                    "id": "FP-M6",
                    "description": catalog["FP-M6"],
                    "severity": "watchable",
                    "why": "ROIC/TSR/adjusted metric in pay language — title ≠ economic alignment; read CD&A defs",
                    "counterexample": "Returns + growth both in unadjusted primary metrics",
                }
            )

    if "dual_class" in sem_topics:
        tags.append(
            {
                "id": "FP-M7",
                "description": catalog["FP-M7"],
                "severity": "watchable",
                "why": "Dual-class present — not auto-fail; ask alignment mechanism questions",
                "counterexample": "Long-term compounding protected with clean related-party record",
            }
        )

    if "ownership_guidelines" in sem_topics:
        tags.append(
            {
                "id": "FP-M8",
                "description": catalog["FP-M8"],
                "severity": "watchable",
                "why": "Ownership guidelines language — high insider ≠ always good; check tunneling/related-party",
                "counterexample": "Related-party clean + capital destination coherent",
            }
        )

    if "guidance_delivery" in sem_topics:
        tags.append(
            {
                "id": "FP-M9",
                "description": catalog["FP-M9"],
                "severity": "watchable",
                "why": "Guidance language present — beat-and-raise theatre ≠ execution excellence",
                "counterexample": "FACT vs GUIDANCE delivery tagged honestly over multi-year window",
            }
        )

    # FP-M10 always watchable reminder — ISS never a production gate
    tags.append(
        {
            "id": "FP-M10",
            "description": catalog["FP-M10"],
            "severity": "watchable",
            "why": "ISS/ESG vendor scores are OUT OF V1 as gates — do not import",
            "counterexample": "Owner alignment judged via allocation/incentives evidence",
        }
    )

    if hierarchy.get("dominant_use") == "organic_capex" and (
        (hierarchy.get("multi_year_totals") or {}).get("organic_capex") or 0
    ) == 0:
        pass  # unreachable; keep structure clear
    capex_total = (hierarchy.get("multi_year_totals") or {}).get("organic_capex")
    if capex_total is not None and capex_total == 0 and primary in {"A4", "A5", "A8"}:
        tags.append(
            {
                "id": "FP-M11",
                "description": catalog["FP-M11"],
                "severity": "watchable",
                "why": "Near-zero CapEx on capital-using archetype — underinvestment/harvest watch",
                "counterexample": "Stage 6 productivity + Stage 7 motive notes support efficiency",
            }
        )
    if "S6_H7_CAPEX_PRODUCTIVITY_OPAQUE" in s6_flags:
        tags.append(
            {
                "id": "FP-M11",
                "description": catalog["FP-M11"],
                "severity": "watchable",
                "why": "S6 CapEx productivity opaque — do not read low CapEx as efficient management",
                "counterexample": "Disclosed sustaining CapEx + productivity narrative",
            }
        )

    if primary == "A7" or "S6_H7_ACQ_RETURN_OPACITY" in s6_flags:
        tags.append(
            {
                "id": "FP-M12",
                "description": catalog["FP-M12"],
                "severity": "material"
                if "S6_H7_ACQ_RETURN_OPACITY" in s6_flags
                else "watchable",
                "why": "Acquisitive / opacity context — integration excellence narrative needs process FACTS",
                "counterexample": "Deal criteria + post-deal accountability + S6 dual-view honesty",
            }
        )

    if (share.get("sbc_expense_multi_year") or 0) > 0 or (
        share.get("gross_repurchase_multi_year") or 0
    ) > 0:
        tags.append(
            {
                "id": "FP-M13",
                "description": catalog["FP-M13"],
                "severity": "watchable",
                "why": "SBC and/or buybacks present — SBC is real ownership transfer; show net share",
                "counterexample": "Gross + net share both disclosed; dilution acknowledged",
            }
        )

    dominant = hierarchy.get("dominant_use")
    if dominant is None and calc_metrics.get("n_fy", 0) >= 3:
        tags.append(
            {
                "id": "FP-M14",
                "description": catalog["FP-M14"],
                "severity": "watchable",
                "why": "No clear dominant cash use — fortress/opportunity-cost watch (not auto prudence)",
                "counterexample": "Stated hierarchy + Stage 6 runway explain hold-cash posture",
            }
        )

    if "levered_distribution" in motives:
        tags.append(
            {
                "id": "FP-M15",
                "description": catalog["FP-M15"],
                "severity": "watchable",
                "why": "Debt co-moves with distributions — activist/levered buyback victory ≠ resilience",
                "counterexample": "Motive + leverage + cycle context all disclosed",
            }
        )

    # Dedup by id (keep first / higher severity)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for t in tags:
        if t["id"] in seen:
            # upgrade severity if later material
            for prev in out:
                if prev["id"] == t["id"] and t.get("severity") == "material":
                    prev["severity"] = "material"
                    prev["why"] = t["why"]
            continue
        seen.add(t["id"])
        out.append(t)
    # Only known catalogue IDs
    known = {fid for fid, _ in FALSE_POSITIVE_CATALOGUE}
    stamped = []
    for t in out:
        if t["id"] not in known:
            continue
        row = dict(t)
        # FP-M watches are always SYSTEM_INFERENCE (heuristic triggers), never company FACT
        row.setdefault("evidence_kind", "SYSTEM_INFERENCE")
        stamped.append(row)
    return stamped


def label_benchmarks(
    *,
    calc_metrics: dict[str, Any],
    archetype: ArchetypeAdaptation | None,
    semantic: Stage7SemanticReview | None,
    fp_tags: list[dict[str, Any]],
    mg_labels: dict[str, Any],
    s6_flags: list[str],
    thesis_coherence: str,
    peer_notes: str | None = None,
) -> list[BenchmarkDimensionResult]:
    """MG1–MG9 Method E labels. Benchmark ≠ hard gate. Peer never primary."""
    results: list[BenchmarkDimensionResult] = []
    primary = archetype.primary_archetype if archetype else "A11"
    alignment = mg_labels.get("alignment_label") or "unknown"
    exec_tag = mg_labels.get("execution_tag") or "unknown"
    div_policy = mg_labels.get("dividend_policy_label") or "unknown"

    def _mk(
        dim_id: str,
        name: str,
        label: str,
        why: str,
        refs: list[str] | None = None,
    ) -> BenchmarkDimensionResult:
        method_e = (
            f"Method E: archetype={primary} → own history → stated policy"
            + (f" → selective peer note ({peer_notes[:80]})" if peer_notes else "")
            + "; ≠ hard gate; no ISS/percentile"
        )
        frame = "peer_secondary" if peer_notes else "company_history"
        if refs and "archetype" in refs and not peer_notes:
            frame = "archetype"
        return BenchmarkDimensionResult(
            dimension_id=dim_id,
            label=label,  # type: ignore[arg-type]
            why=f"{name}: {why} | {method_e}",
            applicability="universal",
            evidence=refs or ["company_history", "stated_policy", "archetype"],
            reference_frame=frame,
        )

    # MG1
    if alignment == "aligned":
        lab1 = "PASS"
        why1 = "Stated vs revealed hierarchy coherent with thesis/runway notes"
    elif alignment == "tension":
        lab1 = "MIXED"
        why1 = "Stated vs revealed tension — evidence label, not a fail gate"
    elif alignment == "opaque":
        lab1 = "BELOW_REFERENCE"
        why1 = "Hierarchy opaque — disclosure quality concern (not numeric gate)"
    else:
        lab1 = "UNKNOWN"
        why1 = "Insufficient stated hierarchy and/or cash-use history"
    if "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION" in s6_flags:
        lab1 = "MIXED"
        why1 = "S6 thesis capital-destination tension consumed factually in MG1"
    results.append(_mk("MG1", MG_BENCHMARK_DIMENSIONS[0][1], lab1, why1))

    # MG2
    if "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST" in s6_flags:
        lab2, why2 = "MIXED", "S6 persistent value-destructive reinvest flag — ask recognition/response (no guilt conversion)"
    elif "S6_H7_CAPEX_PRODUCTIVITY_OPAQUE" in s6_flags:
        lab2, why2 = "UNKNOWN", "CapEx productivity opaque — recognition/response disclosure thin"
    else:
        lab2, why2 = "PASS", "No mechanical S6 destruction flag; response notes descriptive"
    results.append(_mk("MG2", MG_BENCHMARK_DIMENSIONS[1][1], lab2, why2))

    # MG3
    if "S6_H7_ACQ_RETURN_OPACITY" in s6_flags:
        lab3, why3 = "MIXED", "S6 acq return opacity — MG3 process depth mandatory when A7"
    elif primary == "A7":
        lab3, why3 = "PASS", "A7 process review path; no M&A-bad assumption; no return recalc"
    else:
        lab3, why3 = "NOT_APPLICABLE", "Non-acquisitive posture — MG3 light"
        if (calc_metrics.get("revealed_hierarchy") or {}).get("dominant_use") == "acquisitions":
            lab3, why3 = "PASS", "Acquisitions appear in cash uses — process notes without return math"
    results.append(_mk("MG3", MG_BENCHMARK_DIMENSIONS[2][1], lab3, why3))

    # MG4
    share = calc_metrics.get("share_trend") or {}
    if share.get("gross_repurchase_multi_year") is not None or (
        calc_metrics.get("dividend_years_positive") or 0
    ) > 0:
        lab4, why4 = "PASS", "Distributions exhibit present (gross + net when available); no payout threshold"
    else:
        lab4, why4 = "UNKNOWN", "Limited distribution history in Normalized"
    if share.get("net_share_change") is not None and share.get(
        "gross_repurchase_multi_year"
    ):
        why4 += f"; net_share_change={share.get('net_share_change')} ({share.get('net_share_basis')})"
    results.append(_mk("MG4", MG_BENCHMARK_DIMENSIONS[3][1], lab4, why4, ["company_history"]))

    # MG5
    motives = calc_metrics.get("debt_motive_tags") or ["unclear"]
    if motives == ["unclear"]:
        lab5, why5 = "UNKNOWN", "Debt motive unclear — soft-link Stage 2 only; no solvency retest"
    else:
        lab5, why5 = "PASS", f"Debt motive tags={motives} (descriptive; not Stage 2 retest)"
    results.append(_mk("MG5", MG_BENCHMARK_DIMENSIONS[4][1], lab5, why5))

    # MG6 — evidence-depth gate (Plan §8 / §0.C). Proxy/TOC presence alone ≠ PASS.
    cda = incentive_evidence_depth(semantic)
    if cda["depth"] == "substantive":
        lab6, why6 = (
            "PASS",
            "Substantive CD&A spine (metrics/vesting/LTI/dilution linkage) — semantic MVP; "
            f"hits={cda['substantive_hits'][:3]}; no pay DB/ISS gate",
        )
    elif cda["presence"]:
        lab6, why6 = (
            "MIXED",
            "Incentive/proxy language present but CD&A evidence shallow "
            f"(toc_only={cda['toc_only']}; support_hits={cda['support_hits'][:2] or 'none'}) — "
            "weak/TOC semantic must not become PASS; no pay DB/ISS gate",
        )
    else:
        lab6, why6 = "UNKNOWN", "CD&A metrics not extracted — HITL if material"
    results.append(_mk("MG6", MG_BENCHMARK_DIMENSIONS[5][1], lab6, why6))

    # MG7
    if semantic and (
        semantic.governance_structure_notes
        or any(f.topic in {"governance_structure", "dual_class"} for f in semantic.findings)
    ):
        lab7, why7 = "PASS", "Governance structure notes present — neutral factual; no auto premium/penalty"
    else:
        lab7, why7 = "UNKNOWN", "Governance structure sparse — prefer UNKNOWN over invention"
    results.append(_mk("MG7", MG_BENCHMARK_DIMENSIONS[6][1], lab7, why7))

    # MG8 — combined Communication & Execution lens (Plan §0.F D8/D9).
    # Taxonomy presence alone must not PASS when execution half is materially unknown
    # (evidence-sufficiency; parallel to MG6 depth gate). insufficient_history = evaluated
    # but thin history → may PASS with honest tag; unknown = execution half not evaluated → MIXED.
    kinds = {
        f.evidence_kind
        for f in (semantic.findings if semantic else [])
        if f.evidence_kind
    }
    has_taxonomy = bool(
        kinds & {"FACT", "GUIDANCE", "MANAGEMENT_CLAIM", "SYSTEM_INFERENCE"}
    )
    if not has_taxonomy:
        lab8, why8 = "UNKNOWN", "Communication taxonomy samples thin"
    elif exec_tag in {"delivered", "partial"}:
        lab8 = "PASS"
        why8 = (
            f"Taxonomy kinds present={sorted(kinds)}; execution_tag={exec_tag}; "
            "polish ≠ evidence"
        )
    elif exec_tag == "insufficient_history":
        lab8 = "PASS"
        why8 = (
            f"Taxonomy kinds present={sorted(kinds)}; "
            "execution_tag=insufficient_history (delivery history thin after evaluation); "
            "polish ≠ evidence"
        )
    elif exec_tag == "unknown":
        lab8 = "MIXED"
        why8 = (
            f"Taxonomy kinds present={sorted(kinds)}; execution_tag=unknown — "
            "combined lens incomplete (execution half UNKNOWN); "
            "taxonomy ≠ PASS alone; polish ≠ evidence"
        )
    else:
        # missed / goalposts_moved
        lab8 = "MIXED"
        why8 = (
            f"Taxonomy kinds present={sorted(kinds)}; execution_tag={exec_tag}; "
            "polish ≠ evidence"
        )
    if "S6_H7_DISCLOSURE_QUALITY_CAPITAL" in s6_flags:
        lab8 = "MIXED"
        why8 += "; S6 disclosure-quality flag consumed"
    results.append(_mk("MG8", MG_BENCHMARK_DIMENSIONS[7][1], lab8, why8))

    # MG9
    if semantic and (
        semantic.succession_notes
        or any(f.topic == "succession" for f in semantic.findings)
    ):
        lab9, why9 = "PASS", "Succession disclosure evidence present — no personality speculation"
    else:
        lab9, why9 = "UNKNOWN", "Succession disclosure sparse — honest UNKNOWN"
    results.append(_mk("MG9", MG_BENCHMARK_DIMENSIONS[8][1], lab9, why9))

    # Thesis coherence soft note on MG1 already handled; ensure catalogue flags only
    _ = thesis_coherence
    _ = fp_tags
    _ = S6_H7_CONSUMABLE
    _ = div_policy
    return results
