"""Stage 8 VA1–VA8 evidence pack + process outcome.

Outcomes ONLY: PROCEED | CONDITIONAL | REVIEW_REQUIRED | TOO_HARD.
No weighted VA aggregation. No scores/colors/BUY/SELL/cheap-expensive.
terminates_later_stages always False in v1.
"""
from __future__ import annotations

from typing import Any

from ..ids import utc_now
from ..models import (
    ArchetypeAdaptation,
    CalcResult,
    QuestionAnswer,
    Stage8ProcessOutcome,
    Stage8Report,
    Stage8SemanticReview,
    VALensResult,
)
from .archetype import a7_or_acquisitive, a8_or_a9, adapt_from_prior
from .benchmark import _tag_false_positives, label_benchmarks
from .calc import compute_stage8_bridge_metrics, prefer_diluted_shares
from .dcf import choose_discount_class, run_fcff_scenarios
from .market_data import (
    build_price_provenance,
    capital_structure_freshness_notes,
    detect_material_post_period_events,
    price_sensitive_allowed,
    reconcile_currency,
)
from .normalization import build_normalized_base
from .questions import (
    MUST_QUESTIONS,
    S6_H7_CONSUMABLE,
    S7_H8_CARRIES,
    S8_H9_CARRIES,
    SHOULD_QUESTIONS,
    STAGE8_OUTCOMES,
    VA_LENSES,
)
from .reverse_dcf import run_reverse_dcf
from .semantic import build_heuristic_semantic, placeholder_stage8_semantic


def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        fv = float(v)
        if abs(fv) < 1 and fv != 0:
            return f"{fv:.4f}"
        if abs(fv) < 1000:
            return f"{fv:.2f}"
        return f"{fv:,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _ingest_s6_flags(stage6_artifact: dict[str, Any] | None) -> list[str]:
    if not stage6_artifact:
        return []
    raw = (
        stage6_artifact.get("stage7_handoff_flags")
        or stage6_artifact.get("s6_handoff_flags")
        or []
    )
    return list(dict.fromkeys(f for f in raw if f in S6_H7_CONSUMABLE))


def _stage4_revenue_cagr(stage4_artifact: dict[str, Any] | None) -> float | None:
    if not stage4_artifact:
        return None
    calc = stage4_artifact.get("calc") or {}
    metrics = calc.get("metrics") if isinstance(calc, dict) else {}
    if not isinstance(metrics, dict):
        return None
    for key in ("revenue_cagr_5y", "revenue_cagr_3y", "revenue_cagr_window"):
        v = metrics.get(key)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, dict) and v.get("cagr") is not None:
            try:
                return float(v["cagr"])
            except (TypeError, ValueError):
                pass
    return None



def _growth_path_regime_mismatch(
    *,
    dcf: dict[str, Any],
    stage4_revenue_cagr: float | None,
    growth_overrides_used: bool = False,
) -> dict[str, Any] | None:
    """
    Generic coherence check: RESEARCH_CANDIDATE low/mid growth defaults must not
    silently PASS as regime-coherent when Stage 4 evidence shows a materially
    higher-growth regime. Does NOT retune assumptions toward price.
    """
    if growth_overrides_used or stage4_revenue_cagr is None:
        return None
    paths = dcf.get("growth_paths") or {}
    opt = paths.get("optimistic")
    if opt is None:
        return None
    # Material gap: Stage4 CAGR exceeds optimistic RESEARCH path by >4pp,
    # or Stage4 is in demanding+ band (>=12%) while optimistic stays <12%.
    gap = float(stage4_revenue_cagr) - float(opt)
    demanding_band = float(stage4_revenue_cagr) >= 0.12 and float(opt) < 0.12
    if gap <= 0.04 and not demanding_band:
        return None
    return {
        "flag": "growth_path_regime_mismatch",
        "stage4_revenue_cagr": float(stage4_revenue_cagr),
        "research_candidate_optimistic_fcff_growth": float(opt),
        "research_candidate_growth_paths": dict(paths),
        "gap": gap,
        "note": (
            "Forward DCF FCFF growth paths are RESEARCH_CANDIDATE defaults materially "
            f"below Stage4 revenue CAGR≈{stage4_revenue_cagr:.1%} "
            f"(optimistic path={opt:.1%}). Assumptions provisional / not evidence-coherent "
            "with prior-stage high-growth regime — do NOT retune to market price; "
            "VA3/VA7 downgraded; uncertainty↑; reverse DCF carries expectations load."
        ),
        "provenance": "SYSTEM_INFERENCE_VS_S4_EVIDENCE",
    }

def _surface_conflicts(
    *,
    stage6: dict[str, Any] | None,
    stage7: dict[str, Any] | None,
    expectations: str,
    a7: bool,
) -> list[str]:
    conflicts: list[str] = []
    if stage6 and stage6.get("process_outcome") == "REVIEW_REQUIRED" and a7:
        conflicts.append(
            "Stage 6 REVIEW_REQUIRED (A7/ROIC opacity) — surface for valuation uncertainty; "
            "do not rewrite Stage 6 to make IV work"
        )
    if stage7 and stage7.get("process_outcome") == "REVIEW_REQUIRED":
        conflicts.append(
            "Stage 7 REVIEW_REQUIRED — allocation/governance carries inform dilution/uncertainty; "
            "do not rewrite MG conclusions"
        )
    if expectations == "incoherent_with_evidence":
        conflicts.append(
            "Reverse DCF expectations incoherent_with_evidence vs S4–6 — surface; not auto-SELL"
        )
    return conflicts


def _uncertainty_pack(
    *,
    norm: dict[str, Any],
    dcf: dict[str, Any],
    reverse: dict[str, Any],
    price_suppressed: bool,
    staleness: str,
    conflicts: list[str],
    a7: bool,
) -> tuple[str, list[str]]:
    drivers: list[str] = []
    drivers.extend(norm.get("uncertainty_drivers") or [])
    if price_suppressed or staleness in {"STALE", "UNKNOWN"}:
        drivers.append("stale_or_unknown_price")
    if dcf.get("terminal_disagreement_large"):
        drivers.append("terminal_method_disagreement")
    if dcf.get("applicable"):
        # terminal dominance watch on central
        scen = (dcf.get("scenarios") or {}).get("central") or {}
        dom = scen.get("terminal_dominance_perpetual")
        if dom is not None and dom > 0.75:
            drivers.append("terminal_dominance")
    if reverse.get("expectations_label") in {"heroic", "incoherent_with_evidence", "demanding"}:
        drivers.append(f"expectations_{reverse.get('expectations_label')}")
    if dcf.get("growth_path_regime_mismatch"):
        drivers.append("growth_path_regime_mismatch_vs_s4")
    if dcf.get("assumption_coherence") == "provisional_research_candidate_vs_prior_stage_regime":
        drivers.append("assumption_coherence_provisional")
    if a7:
        drivers.append("a7_acquisition_opacity_risk")
    if conflicts:
        drivers.append("s1_7_conflicts_surfaced")
    if not norm.get("fcf_like_base") and not norm.get("ocf_base"):
        drivers.append("no_honest_cash_base")

    drivers = sorted(set(drivers))
    n = len(drivers)
    if "no_honest_cash_base" in drivers or (
        price_suppressed and not dcf.get("applicable") and not reverse.get("constructible")
    ):
        label = "unanalyzable"
    elif n >= 6 or "terminal_method_disagreement" in drivers and a7:
        label = "extreme" if n >= 7 else "high"
    elif n >= 4:
        label = "high"
    elif n >= 2:
        label = "moderate"
    elif n == 1:
        label = "moderate"
    else:
        label = "low"
    # Cap: cyclical mid-cycle
    if norm.get("mid_cycle_mandatory") and label == "low":
        label = "moderate"
        drivers.append("cyclical_mid_cycle")
    return label, drivers


def _mos_evidence(
    *,
    price_suppressed: bool,
    share_price: float | None,
    dcf: dict[str, Any],
    reverse: dict[str, Any],
    uncertainty_label: str,
) -> dict[str, Any]:
    """MoS evidence combo — no universal % gate. Descriptive % only."""
    if price_suppressed:
        return {
            "applicable": False,
            "why": "Price-sensitive MoS suppressed (freshness/currency)",
            "no_universal_mos_pct": True,
            "bullets": [
                "MoS vs market price suppressed — exception queue; do not pretend fresh",
                "No universal MoS% pass/fail (forbidden)",
            ],
        }
    bullets = ["MoS evidence = range position + scenario spread + qualitative — no universal % gate"]
    envelope = (dcf or {}).get("iv_range_envelope_descriptive") or {}
    low, high = envelope.get("low"), envelope.get("high")
    position = None
    descriptive_pct = None
    if share_price is not None and low is not None and high is not None and high != low:
        if share_price < low:
            position = "below_range"
            descriptive_pct = (low - share_price) / share_price
            bullets.append(
                f"Price {_fmt(share_price)} below IV envelope low {_fmt(low)} "
                f"(descriptive gap≈{descriptive_pct:.1%} — not a PASS badge)"
            )
        elif share_price > high:
            position = "above_range"
            descriptive_pct = (share_price - high) / share_price
            bullets.append(
                f"Price {_fmt(share_price)} above IV envelope high {_fmt(high)} "
                f"(descriptive premium≈{descriptive_pct:.1%} — not auto-expensive/SELL)"
            )
        else:
            position = "inside_range"
            bullets.append(
                f"Price {_fmt(share_price)} inside IV envelope [{_fmt(low)}, {_fmt(high)}] — "
                "thin MoS possible even on quality business (state honestly)"
            )
    elif not (dcf or {}).get("applicable"):
        bullets.append("DCF N/A — MoS leans on reverse DCF / multiples context / qualitative only")

    spread = None
    if low is not None and high is not None and low != 0:
        spread = (high - low) / abs(low)
        bullets.append(f"Scenario/method envelope spread≈{spread:.1%} (descriptive)")

    bullets.append(f"Uncertainty={uncertainty_label} affects confidence, not business-quality score")
    bullets.append(
        f"Expectations={reverse.get('expectations_label')} — MoS qualitative link; ≠ cheap/expensive"
    )
    return {
        "applicable": True,
        "position_vs_range": position,
        "descriptive_gap_or_premium": descriptive_pct,
        "scenario_spread_rel": spread,
        "no_universal_mos_pct": True,
        "no_mos_color_or_pass_badge": True,
        "bullets": bullets,
    }


def _decide_outcome(
    *,
    price_suppressed: bool,
    staleness: str,
    currency_ok: bool,
    norm: dict[str, Any],
    dcf: dict[str, Any],
    reverse: dict[str, Any],
    uncertainty_label: str,
    conflicts: list[str],
    a7: bool,
    s6_flags: list[str],
) -> tuple[Stage8ProcessOutcome, list[str]]:
    """Contextual outcome lean — not a formula. NON-TERMINATING always."""
    why: list[str] = []
    expectations = reverse.get("expectations_label") or "unknown"

    if uncertainty_label == "unanalyzable" or (
        not norm.get("ocf_base") and not norm.get("fcf_like_base")
    ):
        why.append("Unanalyzable / no honest cash base → TOO_HARD")
        return "TOO_HARD", why

    if not currency_ok:
        why.append("Currency unresolved → REVIEW_REQUIRED")
        return "REVIEW_REQUIRED", why

    if price_suppressed or staleness in {"STALE", "UNKNOWN"}:
        why.append(f"Price freshness={staleness} / suppressed → REVIEW_REQUIRED (exception queue)")
        return "REVIEW_REQUIRED", why

    review_cues = []
    if expectations in {"heroic", "incoherent_with_evidence"}:
        review_cues.append(f"expectations={expectations}")
    if a7 and "S6_H7_ACQ_RETURN_OPACITY" in s6_flags:
        review_cues.append("A7 + S6_H7_ACQ_RETURN_OPACITY")
    if dcf.get("terminal_disagreement_large"):
        review_cues.append("large dual-terminal disagreement")
    if conflicts:
        review_cues.append("S1–7 conflicts surfaced")
    if uncertainty_label in {"extreme", "high"} and a7:
        review_cues.append(f"uncertainty={uncertainty_label} with A7")
    if norm.get("fcf_method") == "ocf_proxy_capex_unknown" or dcf.get("base_incomplete"):
        review_cues.append("CapEx unknown / OCF-proxy incomplete CF base (not authoritative FCFF)")

    if review_cues:
        why.append("REVIEW_REQUIRED candidacy from: " + "; ".join(review_cues))
        why.append("NON-TERMINATING — no BUY/SELL/RED; no mechanical kill")
        return "REVIEW_REQUIRED", why

    cond_cues = []
    if expectations == "demanding":
        cond_cues.append("demanding expectations — monitors")
    if uncertainty_label in {"moderate", "high"}:
        cond_cues.append(f"uncertainty={uncertainty_label}")
    if dcf.get("applicable") and dcf.get("terminal_disagreement_central_rel"):
        rel = dcf.get("terminal_disagreement_central_rel") or 0
        if rel > 0.15:
            cond_cues.append("material terminal method disagreement")
    if a7:
        cond_cues.append("A7 recurring-M&A reinvestment honesty")

    if cond_cues:
        why.append("CONDITIONAL from: " + "; ".join(cond_cues))
        return "CONDITIONAL", why

    if dcf.get("applicable") or reverse.get("constructible"):
        why.append("Constructible range/expectations with moderate-or-better clarity → PROCEED")
        return "PROCEED", why

    why.append("Thin constructibility → CONDITIONAL")
    return "CONDITIONAL", why


def evaluate_stage8(
    ticker: str,
    periods: list[dict[str, Any]],
    *,
    gate0_class: str = "operating",
    sources: list[str] | None = None,
    semantic: Stage8SemanticReview | None = None,
    market_price: float | None = None,
    price_currency: str | None = "USD",
    price_as_of: str | None = None,
    price_source: str | None = None,
    price_delay_note: str | None = None,
    post_period_events: list[str] | None = None,
    thesis_summary: str | None = None,
    business_notes: str | None = None,
    prior_archetype: dict[str, Any] | None = None,
    stage4_artifact: dict[str, Any] | None = None,
    stage6_artifact: dict[str, Any] | None = None,
    stage7_artifact: dict[str, Any] | None = None,
    unresolved_major_conflict: bool = False,
    force_primary: str | None = None,
    selective_extend: bool = False,
) -> Stage8Report:
    sources = list(sources or [])
    if gate0_class != "operating":
        return Stage8Report(
            ticker=ticker,
            date=utc_now(),
            periods_used=[],
            sources=sources,
            process_outcome="TOO_HARD",
            why_bullets=["Non-operating / FI out of Stage 8 v1 scope"],
            carry_forward_concerns=[],
            market_bridge_bullets=[],
            normalized_base_bullets=[],
            iv_range_bullets=[],
            reverse_dcf_bullets=[],
            multiples_bullets=[],
            dilution_cs_bullets=[],
            mos_uncertainty_bullets=[],
            false_positive_tags=[],
            benchmark_results=[],
            va_lenses=[],
            archetype=None,
            terminates_later_stages=False,
            refuse_reason=f"gate0_class={gate0_class} out of scope",
        )

    archetype = adapt_from_prior(
        prior_archetype,
        thesis_summary=thesis_summary,
        business_notes=business_notes,
        force_primary=force_primary,
    )
    primary = archetype.primary_archetype
    a7 = a7_or_acquisitive(primary, archetype.secondary_traits)
    cyclical = a8_or_a9(primary)

    s6_flags = _ingest_s6_flags(stage6_artifact)
    calc = compute_stage8_bridge_metrics(periods, share_price=market_price)
    metrics = calc.metrics
    cs = metrics["capital_structure"]
    bridge = metrics["ev_equity_bridge"]

    provenance = build_price_provenance(
        share_price=market_price,
        currency=price_currency,
        as_of=price_as_of,
        source=price_source,
        delay_note=price_delay_note,
    )
    currency = reconcile_currency(price_currency, cs.get("reporting_currency") or "USD")
    # Wave 3 / B3: auto-detect material post-period events when caller did not supply.
    # Historical CS bases remain on statement date; events are separate evidence.
    # Explicit caller list is preserved; empty caller list ≠ proven "none".
    post_period_event_records: list[dict] = []
    post_period_evidence_status: str
    if post_period_events is None:
        detected = detect_material_post_period_events(
            periods,
            cs_period_key=cs.get("period_key"),
            cs_period_end=cs.get("period_end"),
            cs_fields={
                k: cs.get(k)
                for k in (
                    "total_debt",
                    "long_term_debt",
                    "short_term_debt",
                    "secured_debt",
                    "shares_outstanding",
                    "shares_diluted_weighted",
                    "business_acquisitions_cash",
                )
            },
        )
        post_period_events = list(detected.get("events") or [])
        post_period_event_records = list(detected.get("event_records") or [])
        post_period_evidence_status = str(
            detected.get("evidence_status") or "insufficient_evidence"
        )
    else:
        post_period_events = list(post_period_events)
        if post_period_events:
            post_period_evidence_status = "caller_supplied"
            post_period_event_records = [
                {
                    "type": "caller_supplied",
                    "relationship": "post_period_vs_cs_statement_date",
                    "event_date": None,
                    "source": "caller",
                    "status": "caller_supplied",
                    "raw": ev,
                }
                for ev in post_period_events
            ]
        else:
            post_period_evidence_status = "caller_supplied_empty_unverified"
    cs_fresh = capital_structure_freshness_notes(
        filing_period_end=cs.get("period_end"),
        filing_as_of=cs.get("filed_at"),
        price_staleness=provenance["staleness_class"],
        post_period_events=post_period_events,
        post_period_evidence_status=post_period_evidence_status,
        post_period_event_records=post_period_event_records,
    )
    allowed, allow_why = price_sensitive_allowed(
        provenance["staleness_class"], currency["ok"]
    )
    # Also suppress on silent mix risk with material post-period events when severe
    price_suppressed = not allowed
    if cs_fresh.get("silent_mix_risk") and provenance["staleness_class"] in {
        "CURRENT",
        "RECENT",
    }:
        # Still allow exhibits but elevate uncertainty — do not silent-mix; label heavily
        pass

    norm = build_normalized_base(
        metrics.get("cash_fy_series") or [],
        primary_archetype=primary,
        secondary_traits=archetype.secondary_traits,
        s6_flags=s6_flags,
    )

    discount_class = choose_discount_class(
        primary_archetype=primary,
        uncertainty_drivers=norm.get("uncertainty_drivers"),
        normalization_uncertainty=norm.get("normalization_uncertainty"),
    )

    # Cash base for DCF/reverse: prefer fcf_like; for A7 use organic OCF/FCF (not acq-inflated).
    # CRITICAL: OCF must NOT silently become FCFF when CapEx/reinvestment unknown.
    base_cash = norm.get("fcf_like_base") or norm.get("ocf_base")
    if a7 and norm.get("organic_exhibit"):
        base_cash = norm["organic_exhibit"].get("fcf_like_base") or norm["organic_exhibit"].get(
            "ocf_base"
        ) or base_cash
    capex_proxy_incomplete = (
        norm.get("fcf_method") == "ocf_proxy_capex_unknown"
        or "capex_unknown_fcf_proxy" in (norm.get("uncertainty_drivers") or [])
    )
    # Only treat as FCFF base when CapEx path is known (or disclosed FCF). Else incomplete proxy.
    base_fcff = None if capex_proxy_incomplete else base_cash

    dcf: dict[str, Any]
    reverse: dict[str, Any]
    if price_suppressed:
        dcf = {
            "applicable": False,
            "why": f"Price-sensitive DCF/IV suppressed — {allow_why}",
            "scenarios": {},
            "no_terminal_average": True,
            "dual_terminal_note": "Dual-terminal CROSS-CHECKS skipped while price-sensitive path suppressed",
        }
        reverse = {
            "constructible": False,
            "expectations_label": "unknown",
            "expectations_why": f"Reverse DCF suppressed — {allow_why}",
            "never_cheap_expensive": True,
            "never_buy_sell": True,
            "first_class": True,
        }
    elif capex_proxy_incomplete:
        # Plan D3 fallback: emit proxy exhibits + base_incomplete; do NOT claim authoritative FCFF.
        # Still run scenario math on OCF proxy as PROVISIONAL sensitivity — labeled incomplete.
        proxy_dcf = run_fcff_scenarios(
            base_fcff=base_cash,
            discount_class=discount_class,
            primary_archetype=primary,
            selective_extend=selective_extend or cyclical,
            bridge=bridge,
        )
        provisional_note = (
            "CapEx materially unknown — OCF used as incomplete cash proxy only; "
            "NOT silent FCFF. IV exhibits are PROVISIONAL / base_incomplete; "
            "not a defensible authoritative FCFF range (maint CapEx not invented)."
        )
        if proxy_dcf.get("applicable"):
            dcf = dict(proxy_dcf)
            dcf["applicable"] = True  # exhibits emitted
            dcf["base_incomplete"] = True
            dcf["fcf_proxy_status"] = "ocf_proxy_capex_unknown"
            dcf["authoritative_fcff"] = False
            dcf["defensible_iv"] = False
            dcf["method"] = "OCF_PROXY_INCOMPLETE_NOT_FCFF"
            dcf["base_cash_proxy"] = base_cash
            dcf["base_fcff"] = None  # refuse silent FCFF claim
            dcf["provisional_note"] = provisional_note
            dcf["numerics_tag"] = "RESEARCH_CANDIDATE_NOT_LOCKED_PROVISIONAL_INCOMPLETE_BASE"
            dcf["dual_terminal_note"] = (
                (proxy_dcf.get("dual_terminal_note") or "")
                + " PROVISIONAL: CapEx unknown — OCF proxy ≠ FCFF; not authoritative IV."
            ).strip()
            s4_cagr_proxy = _stage4_revenue_cagr(stage4_artifact)
            mismatch_p = _growth_path_regime_mismatch(
                dcf=dcf, stage4_revenue_cagr=s4_cagr_proxy, growth_overrides_used=False
            )
            if mismatch_p:
                dcf["growth_path_regime_mismatch"] = mismatch_p
                dcf["assumption_coherence"] = "provisional_research_candidate_vs_prior_stage_regime"
                dcf["growth_note"] = (dcf.get("growth_note") or "") + " " + mismatch_p["note"]
            else:
                dcf["assumption_coherence"] = "research_candidate_not_contradicted_by_s4"
        else:
            dcf = {
                "applicable": False,
                "why": provisional_note,
                "scenarios": {},
                "no_terminal_average": True,
                "base_incomplete": True,
                "fcf_proxy_status": "ocf_proxy_capex_unknown",
                "authoritative_fcff": False,
                "defensible_iv": False,
                "provisional_note": provisional_note,
                "dual_terminal_note": provisional_note,
            }
        # Reverse DCF still constructible on incomplete proxy (Plan D3 fallback) — labeled.
        reverse = run_reverse_dcf(
            market_bridge=bridge,
            base_fcff=base_cash,
            discount_class=discount_class,
            primary_archetype=primary,
            s6_flags=s6_flags,
            stage4_revenue_cagr=_stage4_revenue_cagr(stage4_artifact),
        )
        reverse = dict(reverse)
        reverse["base_incomplete"] = True
        reverse["fcf_proxy_status"] = "ocf_proxy_capex_unknown"
        reverse["base_is_ocf_proxy_not_fcff"] = True
        reverse["expectations_why"] = (
            (reverse.get("expectations_why") or "")
            + "; base_incomplete: CapEx unknown — implied growth on OCF proxy ≠ FCFF "
            "(provisional; REVIEW_REQUIRED lean)"
        )
    else:
        dcf = run_fcff_scenarios(
            base_fcff=base_fcff,
            discount_class=discount_class,
            primary_archetype=primary,
            selective_extend=selective_extend or cyclical,
            bridge=bridge,
        )
        s4_cagr = _stage4_revenue_cagr(stage4_artifact)
        if dcf.get("applicable"):
            dcf = dict(dcf)
            dcf["base_incomplete"] = False
            dcf["authoritative_fcff"] = True
            dcf["defensible_iv"] = True  # still RESEARCH_CANDIDATE numerics — provisional calibration
            mismatch = _growth_path_regime_mismatch(
                dcf=dcf, stage4_revenue_cagr=s4_cagr, growth_overrides_used=False
            )
            if mismatch:
                dcf["growth_path_regime_mismatch"] = mismatch
                dcf["assumption_coherence"] = "provisional_research_candidate_vs_prior_stage_regime"
                dcf["defensible_iv"] = False
                dcf["numerics_tag"] = "RESEARCH_CANDIDATE_NOT_LOCKED_REGIME_MISMATCH_PROVISIONAL"
                note = mismatch["note"]
                dcf["growth_note"] = (dcf.get("growth_note") or "") + " " + note
                dcf["dual_terminal_note"] = (
                    (dcf.get("dual_terminal_note") or "") + " " + note
                ).strip()
            else:
                dcf["assumption_coherence"] = "research_candidate_not_contradicted_by_s4"
        reverse = run_reverse_dcf(
            market_bridge=bridge,
            base_fcff=base_fcff,
            discount_class=discount_class,
            primary_archetype=primary,
            s6_flags=s6_flags,
            stage4_revenue_cagr=s4_cagr,
        )

    conflicts = _surface_conflicts(
        stage6=stage6_artifact,
        stage7=stage7_artifact,
        expectations=reverse.get("expectations_label") or "unknown",
        a7=a7,
    )
    if unresolved_major_conflict:
        conflicts.append("Unresolved major Normalized conflict flagged upstream")

    uncertainty_label, uncertainty_drivers = _uncertainty_pack(
        norm=norm,
        dcf=dcf,
        reverse=reverse,
        price_suppressed=price_suppressed,
        staleness=provenance["staleness_class"],
        conflicts=conflicts,
        a7=a7,
    )

    mos = _mos_evidence(
        price_suppressed=price_suppressed,
        share_price=market_price,
        dcf=dcf,
        reverse=reverse,
        uncertainty_label=uncertainty_label,
    )

    if semantic is None or not semantic.filled:
        semantic = build_heuristic_semantic(
            ticker=ticker,
            primary_archetype=primary,
            norm=norm,
            reverse=reverse,
            dcf=dcf,
            staleness=provenance["staleness_class"],
            price_suppressed=price_suppressed,
            s6_flags=s6_flags,
            post_period_events=post_period_events,
            conflicts=conflicts,
        )

    fp_tags = _tag_false_positives(
        staleness=provenance["staleness_class"],
        currency_ok=currency["ok"],
        a7=a7,
        silent_mix_risk=bool(cs_fresh.get("silent_mix_risk") or cs_fresh.get("material_stale_cs_risk")),
        terminal_disagreement_large=bool(dcf.get("terminal_disagreement_large")),
        expectations=reverse.get("expectations_label") or "unknown",
        sbc_present=bool(norm.get("sbc_honesty")),
        price_suppressed=price_suppressed,
    )

    benchmarks = label_benchmarks(
        staleness=provenance["staleness_class"],
        currency_ok=currency["ok"],
        norm=norm,
        dcf=dcf,
        reverse=reverse,
        bridge_ok=bridge.get("enterprise_value") is not None,
        price_suppressed=price_suppressed,
        a7=a7,
        mos_notes_present=bool(mos.get("bullets")),
        uncertainty_label=uncertainty_label,
    )

    outcome, outcome_why = _decide_outcome(
        price_suppressed=price_suppressed,
        staleness=provenance["staleness_class"],
        currency_ok=currency["ok"],
        norm=norm,
        dcf=dcf,
        reverse=reverse,
        uncertainty_label=uncertainty_label,
        conflicts=conflicts,
        a7=a7,
        s6_flags=s6_flags,
    )
    assert outcome in STAGE8_OUTCOMES

    # VA lenses (evidence, not scored average)
    va_lenses: list[VALensResult] = []
    for vid, vname in VA_LENSES:
        b = next((x for x in benchmarks if x.dimension_id == vid), None)
        labels: dict[str, Any] = {"benchmark_label": b.label if b else "UNKNOWN"}
        evidence: list[str] = list(b.evidence) if b else []
        summary = b.why if b else ""
        why = b.why if b else ""
        if vid == "VA1":
            labels.update(
                {
                    "staleness_class": provenance["staleness_class"],
                    "share_price": market_price,
                    "currency": price_currency,
                    "source": price_source,
                    "equity_market_cap": bridge.get("equity_market_cap"),
                    "enterprise_value": bridge.get("enterprise_value"),
                }
            )
            evidence.append(provenance.get("staleness_why") or "")
            summary = (
                f"Price={_fmt(market_price)} {price_currency}; "
                f"mkt_cap={_fmt(bridge.get('equity_market_cap'))}; "
                f"EV={_fmt(bridge.get('enterprise_value'))}; "
                f"freshness={provenance['staleness_class']}"
            )
            why = f"{provenance.get('staleness_why')}; {currency.get('why')}; {cs_fresh.get('why')}"
        elif vid == "VA2":
            labels["normalization_uncertainty"] = norm.get("normalization_uncertainty")
            labels["fcf_method"] = norm.get("fcf_method")
            labels["a7_dual"] = norm.get("a7_dual")
            summary = (
                f"OCF base={_fmt(norm.get('ocf_base'))}; "
                f"FCF-like={_fmt(norm.get('fcf_like_base'))}; "
                f"uncertainty={norm.get('normalization_uncertainty')}"
            )
        elif vid == "VA3":
            labels["dcf_applicable"] = dcf.get("applicable")
            labels["no_terminal_average"] = True
            labels["base_incomplete"] = bool(dcf.get("base_incomplete"))
            labels["authoritative_fcff"] = dcf.get("authoritative_fcff")
            labels["numerics_tag"] = dcf.get("numerics_tag") or "RESEARCH_CANDIDATE_NOT_LOCKED"
            if dcf.get("applicable"):
                env = dcf.get("iv_range_envelope_descriptive") or {}
                if dcf.get("base_incomplete"):
                    summary = (
                        f"PROVISIONAL incomplete-base envelope (OCF proxy ≠ FCFF): "
                        f"[{_fmt(env.get('low'))}, {_fmt(env.get('high'))}] /sh — "
                        "not defensible authoritative FCFF IV; RESEARCH_CANDIDATE/NOT_LOCKED"
                    )
                    why = dcf.get("provisional_note") or dcf.get("dual_terminal_note") or why
                elif dcf.get("growth_path_regime_mismatch"):
                    summary = (
                        f"PROVISIONAL regime-mismatch envelope: "
                        f"[{_fmt(env.get('low'))}, {_fmt(env.get('high'))}] /sh — "
                        "RESEARCH_CANDIDATE growth paths not coherent with Stage4 high-growth "
                        "evidence; not defensible as regime-calibrated IV; do not retune to price"
                    )
                    why = (dcf.get("growth_path_regime_mismatch") or {}).get("note") or why
                    labels["assumption_coherence"] = dcf.get("assumption_coherence")
                    labels["defensible_iv"] = False
                else:
                    summary = (
                        f"IV envelope (descriptive, not averaged fair value): "
                        f"[{_fmt(env.get('low'))}, {_fmt(env.get('high'))}] per share; "
                        "numerics=RESEARCH_CANDIDATE/NOT_LOCKED (provisional calibration)"
                    )
                    why = dcf.get("dual_terminal_note") or why
            else:
                summary = dcf.get("why") or "DCF N/A"
        elif vid == "VA4":
            labels["expectations"] = reverse.get("expectations_label")
            summary = f"expectations={reverse.get('expectations_label')}"
            why = reverse.get("expectations_why") or why
        elif vid == "VA5":
            summary = "Method E: own history → archetype → selective peers (N/A) → market secondary"
            why = "No P/E gates / peer percentiles / mean=fair"
        elif vid == "VA6":
            sh, basis = prefer_diluted_shares(cs)
            labels["share_basis"] = basis
            labels["net_share_change"] = (metrics.get("share_trajectory") or {}).get(
                "net_share_change"
            )
            gross = bridge.get("gross_debt")
            debt_note = ""
            if cs.get("total_debt") is None and gross is not None:
                debt_note = " (LT+ST components; total_debt null)"
            summary = (
                f"shares={_fmt(sh)} ({basis}); gross_debt={_fmt(gross)}{debt_note}; "
                f"cash={_fmt(cs.get('cash_and_equivalents'))}; "
                f"filing={cs.get('period_key')} period_end={cs.get('period_end')}"
            )
            why = "Filing-period CS; SBC never ignore; no double-count policy stated"
        elif vid == "VA7":
            labels["mos_position"] = mos.get("position_vs_range")
            labels["no_universal_mos_pct"] = True
            labels["provisional_iv"] = bool(dcf.get("base_incomplete")) or (
                dcf.get("numerics_tag") or ""
            ).startswith("RESEARCH_CANDIDATE")
            summary = "; ".join((mos.get("bullets") or [])[:2])
            if dcf.get("base_incomplete"):
                why = (
                    "MoS vs PROVISIONAL OCF-proxy IV (CapEx unknown) — not authoritative FCFF; "
                    "no universal %; RESEARCH_CANDIDATE/NOT_LOCKED"
                )
            else:
                why = (
                    (mos.get("why") or "MoS evidence combo; no universal %")
                    + "; IV numerics=RESEARCH_CANDIDATE/NOT_LOCKED (provisional)"
                )
        elif vid == "VA8":
            labels["uncertainty"] = uncertainty_label
            labels["drivers"] = uncertainty_drivers
            labels["numerics_provisional"] = True
            summary = f"uncertainty={uncertainty_label}; drivers={uncertainty_drivers}"
            why = (
                "Disagreement = information; confidence ≠ quality score; "
                "discount/growth/exit numerics=RESEARCH_CANDIDATE/NOT_LOCKED (provisional)"
            )
            if dcf.get("base_incomplete"):
                why += "; CapEx-unknown OCF proxy elevates incomplete-base uncertainty"
        va_lenses.append(
            VALensResult(
                lens_id=vid,
                lens_name=vname,
                summary=summary,
                why=why,
                labels=labels,
                evidence=[e for e in evidence if e],
                escalate_to_human=vid in {"VA1", "VA4", "VA8"}
                and (
                    price_suppressed
                    or (reverse.get("expectations_label") in {"heroic", "incoherent_with_evidence"})
                    or uncertainty_label in {"extreme", "unanalyzable"}
                ),
            )
        )

    # Carries
    s7_h8: list[str] = []
    s8_h9: list[str] = []
    traj = metrics.get("share_trajectory") or {}
    if traj.get("net_share_change") is not None and traj["net_share_change"] > 0:
        s7_h8.append("S7_H8_DILUTION_MATERIAL")
    if a7 or "S6_H7_ACQ_RETURN_OPACITY" in s6_flags:
        s7_h8.append("S7_H8_ALLOCATION_UNCERTAINTY_FOR_VALUATION")
    if stage7_artifact and "buyback" in str(stage7_artifact.get("distribution_bullets") or "").lower():
        # thin opacity note when buybacks present but price discipline unknown
        if stage7_artifact.get("alignment_label") == "opaque":
            s7_h8.append("S7_H8_BUYBACK_PRICE_DISCIPLINE_OPAQUE")
    if cyclical:
        s8_h9.append("S8_H9_CYCLE_SENSITIVE_VALUATION")
    if reverse.get("expectations_label") in {"demanding", "heroic", "incoherent_with_evidence"}:
        s8_h9.append("S8_H9_EXPECTATIONS_DEMANDING")
    s7_h8 = [c for c in s7_h8 if c in S7_H8_CARRIES]
    s8_h9 = [c for c in s8_h9 if c in S8_H9_CARRIES]

    # Dashboard bullets
    market_bridge_bullets = [
        f"share_price={_fmt(market_price)} {price_currency}; as_of_utc={provenance.get('as_of_utc')}; "
        f"as_of_europe_istanbul={provenance.get('as_of_europe_istanbul')}; source={price_source}",
        f"staleness_class={provenance['staleness_class']} — {provenance.get('staleness_why')}",
        f"equity_market_cap={_fmt(bridge.get('equity_market_cap'))}; "
        f"EV={_fmt(bridge.get('enterprise_value'))}; net_debt={_fmt(bridge.get('net_debt'))}",
        f"share_basis={bridge.get('share_basis')}; shares_used={_fmt(bridge.get('shares_used'))}",
        f"currency: {currency.get('why')}",
        f"CS filing: {cs_fresh.get('why')}",
        f"price_sensitive_suppressed={price_suppressed} — {allow_why}",
        "Never silent fresh-price + materially stale CS mix",
    ]

    normalized_base_bullets = [
        f"PRIMARY_ARCHETYPE={primary}; normalization_uncertainty={norm.get('normalization_uncertainty')}",
        f"OCF base={_fmt(norm.get('ocf_base'))}; FCF-like={_fmt(norm.get('fcf_like_base'))} "
        f"(method={norm.get('fcf_method')})",
        f"Owner-earnings companion: {norm.get('owner_earnings_label')} "
        f"value={_fmt(norm.get('owner_earnings_base'))}",
        "No aggressive normalization; prefer cash over adjusted-EPS worship",
        *list(norm.get("notes") or [])[:6],
    ]
    if a7 and norm.get("organic_exhibit"):
        normalized_base_bullets.append(
            f"A7 organic exhibit: {norm['organic_exhibit'].get('note')}"
        )
        normalized_base_bullets.append(
            f"A7 acq reinvestment exhibit: recurring_ma="
            f"{(norm.get('acq_exhibit') or {}).get('recurring_ma_as_reinvestment')}; "
            f"acq_sum={_fmt((norm.get('acq_exhibit') or {}).get('acq_cash_multi_year_sum'))}"
        )

    iv_range_bullets: list[str] = []
    if dcf.get("applicable"):
        if dcf.get("base_incomplete"):
            iv_range_bullets.append(
                "PROVISIONAL incomplete CF base: OCF proxy ≠ FCFF (CapEx unknown; maint CapEx not invented); "
                "exhibits only — not authoritative/defensible FCFF IV"
            )
            iv_range_bullets.append(
                f"method={dcf.get('method')}; base_cash_proxy={_fmt(dcf.get('base_cash_proxy'))}; "
                "authoritative_fcff=False; defensible_iv=False"
            )
        else:
            iv_range_bullets.append(
                "FCFF default; scenarios=conservative|central|optimistic; ~5Y default; "
                "numerics=RESEARCH_CANDIDATE/NOT_LOCKED (provisional calibration)"
            )
        iv_range_bullets.append(dcf.get("dual_terminal_note") or "Dual-terminal CROSS-CHECKS")
        iv_range_bullets.append(
            f"IV range perpetual-growth: {_fmt((dcf.get('iv_range_perpetual_growth') or {}).get('low'))}–"
            f"{_fmt((dcf.get('iv_range_perpetual_growth') or {}).get('high'))} /sh"
        )
        iv_range_bullets.append(
            f"IV range exit-multiple: {_fmt((dcf.get('iv_range_exit_multiple') or {}).get('low'))}–"
            f"{_fmt((dcf.get('iv_range_exit_multiple') or {}).get('high'))} /sh"
        )
        env = dcf.get("iv_range_envelope_descriptive") or {}
        iv_range_bullets.append(
            f"Descriptive envelope (NOT averaged fair value): "
            f"[{_fmt(env.get('low'))}, {_fmt(env.get('high'))}] — {env.get('note')}"
        )
        iv_range_bullets.append(
            f"Discount class={discount_class}; numerics=RESEARCH_CANDIDATE/NOT_LOCKED; no CAPM"
        )
        iv_range_bullets.append("no_terminal_average=True; no_method_average=True")
    else:
        iv_range_bullets.append(dcf.get("why") or "IV range NOT_APPLICABLE")

    reverse_bullets = [
        f"expectations_label={reverse.get('expectations_label')} "
        f"(locked vocab; ≠ cheap/expensive; ≠ BUY/SELL)",
        reverse.get("expectations_why") or "n/a",
        f"constructible={reverse.get('constructible')}; first_class={reverse.get('first_class')}",
    ]
    solve = reverse.get("solve") or {}
    if solve:
        sr = solve.get("search_range") or {}
        reverse_bullets.append(
            f"search_range=[{sr.get('growth_low')}, {sr.get('growth_high')}]; "
            f"variable_solved={solve.get('variable_solved') or 'constant_fcff_growth'}; "
            f"solve_status={solve.get('solve_status') or solve.get('bound')}; "
            f"root_found={solve.get('root_found')}"
        )
        if solve.get("lower_bound_only") or solve.get("solve_status") == "unresolved_above_search_range":
            lb = solve.get("implied_fcff_growth_lower_bound")
            reverse_bullets.append(
                f"implied_fcff_growth > {lb:.1%} "
                f"(lower_bound_only / unresolved_above_search_range — NOT a solved point estimate; "
                f"held discount/terminal/base approximately fixed)"
                if lb is not None
                else "implied_fcff_growth unresolved above search ceiling (lower_bound_only)"
            )
            if solve.get("price_value_residual_ev") is not None:
                reverse_bullets.append(
                    f"price/value residual at ceiling: EV_target−EV_at_ceiling≈"
                    f"{_fmt(solve.get('price_value_residual_ev'))} "
                    f"(rel≈{(solve.get('price_value_residual_rel') or 0):.1%}); "
                    f"matched_ev={_fmt(solve.get('matched_ev'))} vs target_ev={_fmt(solve.get('target_ev'))}"
                )
        elif solve.get("upper_bound_only") or solve.get("solve_status") == "unresolved_below_search_range":
            ub = solve.get("implied_fcff_growth_upper_bound")
            reverse_bullets.append(
                f"implied_fcff_growth < {ub:.1%} "
                f"(upper_bound_only / unresolved_below_search_range — NOT a solved point estimate)"
                if ub is not None
                else "implied_fcff_growth unresolved below search floor (upper_bound_only)"
            )
        elif solve.get("implied_fcff_growth") is not None:
            reverse_bullets.append(
                f"implied_fcff_growth≈{solve['implied_fcff_growth']:.1%} "
                f"(root_found; smallest solve; held discount/terminal/base approximately fixed)"
            )
        if solve.get("note"):
            reverse_bullets.append(solve["note"])

    multiples_bullets = [
        "Method E hierarchy: (1) own normalized history (2) archetype context "
        "(3) selective peers (4) market secondary",
        "Selective peers = NOT_APPLICABLE without economic peer set WHY (not forced)",
        "Forbidden: P/E < X = cheap; peer percentile grade; historical mean = fair; "
        "cheaper-than-peers = undervalued",
    ]

    dilution_bullets = [
        f"Filing-period CS {cs.get('period_key')} period_end={cs.get('period_end')}",
        (
            f"gross_debt={_fmt(bridge.get('gross_debt'))}"
            + (
                " (LT+ST components; total_debt null)"
                if cs.get("total_debt") is None and bridge.get("gross_debt") is not None
                else ""
            )
            + f"; cash={_fmt(cs.get('cash_and_equivalents'))}"
        ),
        f"net_share_change={_fmt(traj.get('net_share_change'))}; "
        f"sbc_multi_year={_fmt(traj.get('sbc_expense_multi_year'))}",
        traj.get("no_double_count_policy") or "SBC honesty / no double-count",
        "SBC never ignore because non-cash (FP-V11)",
    ]

    mos_unc_bullets = list(mos.get("bullets") or [])
    mos_unc_bullets.append(f"uncertainty_label={uncertainty_label}; drivers={uncertainty_drivers}")
    if dcf.get("terminal_disagreement_large"):
        mos_unc_bullets.append("Large dual-terminal disagreement elevates VA8 / REVIEW lean")

    # Question spine
    qas: list[QuestionAnswer] = []
    must_answers = {
        "S8-M1": f"freshness={provenance['staleness_class']}; EV={_fmt(bridge.get('enterprise_value'))}",
        "S8-M2": f"norm_uncertainty={norm.get('normalization_uncertainty')}; method={norm.get('fcf_method')}",
        "S8-M3": "DCF range" if dcf.get("applicable") else "N/A + WHY",
        "S8-M4": f"expectations={reverse.get('expectations_label')}",
        "S8-M5": "Method E; peers N/A default",
        "S8-M6": f"filing CS {cs.get('period_key')}; SBC honesty",
        "S8-M7": f"MoS applicable={mos.get('applicable')}; no universal %",
        "S8-M8": f"uncertainty={uncertainty_label}",
        "S8-M9": "VA1–VA8 emitted; no weighted average",
        "S8-M10": f"outcome={outcome}; terminates_later_stages=False",
    }
    for qid, qtext in MUST_QUESTIONS:
        qas.append(
            QuestionAnswer(
                question_id=qid,
                question=qtext,
                status="answered",
                answer_summary=must_answers.get(qid, "see report"),
                must=True,
            )
        )
    for qid, qtext in SHOULD_QUESTIONS:
        qas.append(
            QuestionAnswer(
                question_id=qid,
                question=qtext,
                status=(
                    "answered"
                    if qid != "S8-S3"
                    or post_period_events
                    or post_period_evidence_status
                    in {
                        "events_found",
                        "searched_none_material",
                        "no_post_cs_interim_available",
                        "insufficient_evidence",
                        "caller_supplied",
                        "caller_supplied_empty_unverified",
                    }
                    else "partial"
                ),
                answer_summary=(
                    "A7 dual exhibits" if qid == "S8-S1" and a7
                    else "dual-terminal CROSS-CHECKS" if qid == "S8-S2"
                    else (
                        f"events={post_period_events or []}; "
                        f"evidence_status={post_period_evidence_status}; "
                        "empty≠proven_none"
                    ) if qid == "S8-S3"
                    else currency.get("why") if qid == "S8-S4"
                    else f"carries s7_h8={s7_h8}; s8_h9={s8_h9}"
                ),
                must=False,
            )
        )

    fy_periods_sorted = sorted(
        [p for p in periods if p.get("period_type") == "FY"],
        key=lambda p: str(p.get("period_key") or ""),
    )
    periods_used = [
        {"period_key": p.get("period_key"), "version_id": p.get("version_id")}
        for p in fy_periods_sorted
    ][-5:]

    # Enrich calc metrics with valuation packs (provenance structural)
    calc.metrics["price_provenance"] = provenance
    calc.metrics["currency_reconcile"] = currency
    calc.metrics["cs_freshness"] = cs_fresh
    calc.metrics["normalized_base"] = norm
    calc.metrics["dcf"] = dcf
    calc.metrics["reverse_dcf"] = reverse
    calc.metrics["mos_evidence"] = mos
    calc.metrics["discount_class"] = discount_class
    calc.metrics["price_sensitive_suppressed"] = price_suppressed
    calc.metrics["uncertainty"] = {
        "label": uncertainty_label,
        "drivers": uncertainty_drivers,
    }

    why_bullets = [
        f"expectations={reverse.get('expectations_label')} (evidence label, not cheap/expensive)",
        f"uncertainty={uncertainty_label}",
        f"freshness={provenance['staleness_class']}; suppressed={price_suppressed}",
        *outcome_why,
    ]

    carry = []
    carry.extend(conflicts)
    if s7_h8:
        carry.append(f"S7_H8 carries={s7_h8}")
    if s8_h9:
        carry.append(f"S8_H9 carries={s8_h9}")
    if a7:
        carry.append(
            "A7: recurring M&A = reinvestment; organic vs acq exhibits; "
            "no free-organic acquired growth; no deal-by-deal DCF"
        )

    return Stage8Report(
        ticker=ticker,
        date=utc_now(),
        periods_used=periods_used,
        sources=sources,
        process_outcome=outcome,
        why_bullets=why_bullets,
        carry_forward_concerns=carry,
        market_bridge_bullets=market_bridge_bullets,
        normalized_base_bullets=normalized_base_bullets,
        iv_range_bullets=iv_range_bullets,
        reverse_dcf_bullets=reverse_bullets,
        multiples_bullets=multiples_bullets,
        dilution_cs_bullets=dilution_bullets,
        mos_uncertainty_bullets=mos_unc_bullets,
        false_positive_tags=fp_tags,
        benchmark_results=benchmarks,
        va_lenses=va_lenses,
        archetype=archetype,
        staleness_class=provenance["staleness_class"],
        expectations_label=reverse.get("expectations_label") or "unknown",
        uncertainty_label=uncertainty_label,
        uncertainty_drivers=uncertainty_drivers,
        discount_class=discount_class,
        price_sensitive_suppressed=price_suppressed,
        a7_dual_exhibits=bool(a7 and norm.get("a7_dual")),
        dual_terminal_note=dcf.get("dual_terminal_note"),
        stage4_6_7_conflicts=conflicts,
        s6_handoff_flags_consumed=s6_flags,
        s7_h8_carries=s7_h8,
        s8_h9_carries=s8_h9,
        what_is_strong=[
            x
            for x in [
                "Session-aware freshness + filing-period CS labeled" if not price_suppressed else None,
                "FCFF range + dual-terminal CROSS-CHECKS" if dcf.get("applicable") else None,
                "Reverse DCF first-class with locked expectations vocab"
                if reverse.get("constructible")
                else None,
                "A7 dual organic/acq exhibits" if a7 else None,
            ]
            if x
        ],
        what_can_break=[
            "Freshness failure suppresses price-sensitive IV/MoS",
            "A7 acquisition opacity / free-organic illusion (FP-V10)",
            "Terminal disagreement / dominance (FP-V18)",
            "SBC/dilution ignored (FP-V11)",
            "Silent method averaging / one fair-value myth (FP-V2/V3)",
        ],
        monitors=[
            "Price provenance on every re-run",
            "Post-period financing/M&A/issuance/buyback flags",
            "A7 organic bridge vs acquisition capital",
            "Expectations vocab drift vs Stage 4–6 evidence",
        ],
        missing_ambiguous=[
            k for k, v in (calc.null_reasons or {}).items()
        ],
        question_answers=qas,
        calc=calc,
        semantic=semantic,
        terminates_later_stages=False,
        thesis_coherence="unknown",
    )
