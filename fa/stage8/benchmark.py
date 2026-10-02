"""Method E valuation benchmarks — labels + WHY; ≠ hard gate.

Hierarchy: own history → archetype → selective peers → market secondary.
Forbidden: P/E gates, peer percentiles, mean=fair, cheaper-than-peers=undervalued.
"""
from __future__ import annotations

from typing import Any

from ..models import BenchmarkDimensionResult
from .questions import FALSE_POSITIVE_CATALOGUE, VA_BENCHMARK_DIMENSIONS


def _tag_false_positives(
    *,
    staleness: str,
    currency_ok: bool,
    a7: bool,
    silent_mix_risk: bool,
    terminal_disagreement_large: bool,
    expectations: str,
    sbc_present: bool,
    price_suppressed: bool,
) -> list[dict[str, Any]]:
    tags = []
    catalogue = {fid: (desc, sev) for fid, desc, sev in FALSE_POSITIVE_CATALOGUE}

    def add(fid: str, why: str):
        desc, sev = catalogue[fid]
        tags.append(
            {
                "id": fid,
                "description": desc,
                "severity": sev,
                "why": why,
                "counterexample": "flags-not-auto-fails; no FP score average; no count→outcome",
            }
        )

    if staleness in {"STALE", "UNKNOWN"} or price_suppressed:
        add("FP-V7", f"staleness={staleness}; price-sensitive suppressed={price_suppressed}")
    if silent_mix_risk:
        add("FP-V8", "Fresh price vs filing-period CS mix risk flagged")
    if not currency_ok:
        add("FP-V9", "Currency reconcile failed / unresolved")
    if a7:
        add("FP-V10", "A7 watch — acquired growth must not be free organic")
        add("FP-V12", "A7 — no deal-by-deal M&A DCF as primary")
    if sbc_present:
        add("FP-V11", "SBC present — never treat as free non-cash")
    if terminal_disagreement_large:
        add("FP-V18", "Large dual-terminal disagreement — terminal dominance / method info")
    if expectations in {"heroic", "incoherent_with_evidence"}:
        add("FP-V15", "Demanding/heroic/incoherent expectations ≠ auto-SELL")
    # Standing architecture watches
    add("FP-V2", "IV emitted as RANGE / dual CROSS-CHECKS — not one fair-value truth")
    add("FP-V3", "No mechanical method averaging")
    add("FP-V16", "Discount class + sensitivity — no CAPM β engine")
    return tags


def label_benchmarks(
    *,
    staleness: str,
    currency_ok: bool,
    norm: dict[str, Any],
    dcf: dict[str, Any],
    reverse: dict[str, Any],
    bridge_ok: bool,
    price_suppressed: bool,
    a7: bool,
    mos_notes_present: bool,
    uncertainty_label: str,
) -> list[BenchmarkDimensionResult]:
    """VA-facing Method E labels — evidence WHY, not gates."""
    results: list[BenchmarkDimensionResult] = []

    # VA1
    if not currency_ok or staleness in {"STALE", "UNKNOWN"}:
        lab1, why1 = "MIXED", f"Freshness={staleness}; currency_ok={currency_ok}; suppress={price_suppressed}"
    elif bridge_ok and staleness in {"CURRENT", "RECENT"}:
        lab1, why1 = "PASS", f"Bridge constructible; freshness={staleness}; provenance present"
    else:
        lab1, why1 = "UNKNOWN", "Bridge/freshness incomplete"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="VA1",
            label=lab1,
            why=why1,
            applicability="applicable",
            evidence=[f"staleness={staleness}", f"currency_ok={currency_ok}"],
            reference_frame="own_session_provenance",
        )
    )

    # VA2
    nu = (norm or {}).get("normalization_uncertainty") or "unanalyzable"
    if nu in {"extreme", "unanalyzable"} or not (norm or {}).get("fcf_like_base") and not (
        norm or {}
    ).get("ocf_base"):
        lab2, why2 = "MIXED", f"normalization_uncertainty={nu}; base thin/missing"
    elif (norm or {}).get("a7_dual"):
        lab2, why2 = (
            "PASS",
            f"Cash-preferring base with A7 dual exhibits; uncertainty={nu}; no aggressive norm",
        )
    else:
        lab2, why2 = "PASS", f"Archetype-aware base; uncertainty={nu}; no aggressive norm"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="VA2",
            label=lab2,
            why=why2,
            applicability="applicable",
            evidence=list((norm or {}).get("notes") or [])[:3],
            reference_frame="own_cash_history",
        )
    )

    # VA3 — CapEx-unknown OCF proxy must NOT yield authoritative PASS as if FCFF
    incomplete = bool(
        (dcf or {}).get("base_incomplete")
        or (norm or {}).get("fcf_method") == "ocf_proxy_capex_unknown"
        or (dcf or {}).get("fcf_proxy_status") == "ocf_proxy_capex_unknown"
    )
    if price_suppressed:
        lab3, why3 = (
            "NOT_APPLICABLE",
            "Price-sensitive IV suppressed due to freshness/currency failure",
        )
    elif incomplete and (dcf or {}).get("applicable"):
        lab3, why3 = (
            "MIXED",
            "PROVISIONAL incomplete-base IV exhibits (OCF proxy ≠ FCFF; CapEx unknown) — "
            "not defensible authoritative FCFF range; dual-terminal CROSS-CHECKS never averaged; "
            "numerics=RESEARCH_CANDIDATE/NOT_LOCKED; REVIEW_REQUIRED lean",
        )
    elif (dcf or {}).get("growth_path_regime_mismatch") and (dcf or {}).get("applicable"):
        mm = (dcf or {}).get("growth_path_regime_mismatch") or {}
        lab3, why3 = (
            "MIXED",
            "PROVISIONAL: RESEARCH_CANDIDATE FCFF growth paths not coherent with Stage4 "
            "high-growth regime evidence — dual-terminal CROSS-CHECKS emitted but "
            "not defensible as regime-calibrated IV; numerics=RESEARCH_CANDIDATE/NOT_LOCKED; "
            "do NOT retune assumptions to market price; reverse DCF carries expectations",
        )
        if mm.get("note"):
            why3 = mm["note"]
    elif (dcf or {}).get("applicable"):
        lab3, why3 = (
            "PASS",
            "FCFF scenario IV RANGE + dual-terminal CROSS-CHECKS (never averaged); "
            "numerics=RESEARCH_CANDIDATE/NOT_LOCKED (provisional calibration — not falsely authoritative)",
        )
    else:
        lab3, why3 = "NOT_APPLICABLE", (dcf or {}).get("why") or "DCF not meaningful"
    va3_evidence = ["no_terminal_average=True"]
    if incomplete:
        va3_evidence.extend(
            [
                "base_incomplete=True",
                "ocf_proxy_capex_unknown",
                "authoritative_fcff=False",
            ]
        )
    elif (dcf or {}).get("growth_path_regime_mismatch"):
        va3_evidence.extend(
            [
                "growth_path_regime_mismatch_vs_s4",
                "assumption_coherence_provisional",
                "defensible_iv=False",
                "numerics=RESEARCH_CANDIDATE_NOT_LOCKED_REGIME_MISMATCH_PROVISIONAL",
            ]
        )
    else:
        va3_evidence.append("numerics=RESEARCH_CANDIDATE_NOT_LOCKED")
    results.append(
        BenchmarkDimensionResult(
            dimension_id="VA3",
            label=lab3,
            why=why3,
            applicability="applicable" if (dcf or {}).get("applicable") else "not_applicable",
            evidence=va3_evidence,
            reference_frame="scenario_range",
        )
    )

    # VA4
    el = (reverse or {}).get("expectations_label") or "unknown"
    if not (reverse or {}).get("constructible"):
        lab4, why4 = "UNKNOWN", (reverse or {}).get("expectations_why") or "unconstructible"
    else:
        lab4, why4 = "PASS", f"expectations={el}; vocab≠cheap/expensive; first-class reverse DCF"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="VA4",
            label=lab4,
            why=why4,
            applicability="applicable",
            evidence=[f"expectations={el}"],
            reference_frame="embedded_expectations",
        )
    )

    # VA5 Method E — own history first; peers often N/A without selective set
    results.append(
        BenchmarkDimensionResult(
            dimension_id="VA5",
            label="NOT_APPLICABLE",
            why=(
                "Selective peers NOT_APPLICABLE without economic peer set; "
                "own-history multiples context preferred (Method E). "
                "No P/E gates / peer percentiles / mean=fair."
            ),
            applicability="not_applicable",
            evidence=["method_e_hierarchy", "peers_not_forced"],
            reference_frame="own_history_then_archetype",
        )
    )

    # VA6
    results.append(
        BenchmarkDimensionResult(
            dimension_id="VA6",
            label="PASS" if bridge_ok else "MIXED",
            why=(
                "Filing-period CS + diluted share preference + SBC honesty path"
                if bridge_ok
                else "CS/bridge inputs incomplete"
            ),
            applicability="applicable",
            evidence=["filing_period_cs", "sbc_never_ignore"],
            reference_frame="filing_period_capital_structure",
        )
    )

    # VA7 MoS — evidence combo, no universal %; provisional when IV base incomplete
    if price_suppressed:
        lab7, why7 = (
            "NOT_APPLICABLE",
            "MoS vs price suppressed — freshness/currency failure (no universal MoS%)",
        )
    elif incomplete and mos_notes_present:
        lab7, why7 = (
            "MIXED",
            "MoS vs PROVISIONAL OCF-proxy IV (CapEx unknown) — not authoritative FCFF; "
            "no universal % gate; RESEARCH_CANDIDATE/NOT_LOCKED",
        )
    elif (dcf or {}).get("growth_path_regime_mismatch") and mos_notes_present:
        lab7, why7 = (
            "MIXED",
            "MoS vs PROVISIONAL regime-mismatch IV (RESEARCH_CANDIDATE growth paths "
            "≠ Stage4 high-growth evidence) — not defensible regime-calibrated; "
            "no universal % gate; do not retune to price",
        )
    elif mos_notes_present:
        lab7, why7 = (
            "PASS",
            "MoS evidence via range position / scenario spread / qualitative — no universal % gate; "
            "IV numerics=RESEARCH_CANDIDATE/NOT_LOCKED (provisional)",
        )
    else:
        lab7, why7 = "UNKNOWN", "MoS evidence thin"
    results.append(
        BenchmarkDimensionResult(
            dimension_id="VA7",
            label=lab7,
            why=why7,
            applicability="applicable",
            evidence=["no_universal_mos_pct"],
            reference_frame="range_position_scenario_spread",
        )
    )

    # VA8
    if uncertainty_label in {"extreme", "unanalyzable"}:
        lab8 = "MIXED"
    elif uncertainty_label == "high":
        lab8 = "MIXED"
    else:
        lab8 = "PASS"
    va8_why = (
        f"uncertainty={uncertainty_label}; method disagreement = information (not averaged away); "
        "discount/growth/exit numerics=RESEARCH_CANDIDATE/NOT_LOCKED (provisional)"
    )
    if incomplete:
        va8_why += "; CapEx-unknown OCF proxy = incomplete CF base"
    if (dcf or {}).get("growth_path_regime_mismatch"):
        va8_why += "; growth_path_regime_mismatch vs Stage4 (RESEARCH_CANDIDATE provisional)"
    va8_evidence = [f"uncertainty={uncertainty_label}"]
    if incomplete:
        va8_evidence.extend(["base_incomplete", "ocf_proxy_capex_unknown"])
    elif (dcf or {}).get("growth_path_regime_mismatch"):
        va8_evidence.extend(["growth_path_regime_mismatch_vs_s4", "numerics_provisional"])
    else:
        va8_evidence.append("numerics_provisional")
    results.append(
        BenchmarkDimensionResult(
            dimension_id="VA8",
            label=lab8,
            why=va8_why,
            applicability="applicable",
            evidence=va8_evidence,
            reference_frame="uncertainty_first_class",
        )
    )
    return results
