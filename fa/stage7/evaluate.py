"""Stage 7 MG1–MG9 evidence pack + process outcome.

Outcomes ONLY: PROCEED | CONDITIONAL | REVIEW_REQUIRED | TOO_HARD.
No mechanical label-count → outcome. No scores/colors/numeric gates.
No ROIC recompute. S6_H7_* factual consume only — no mechanical guilt.
terminates_later_stages always False in v1.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ids import utc_now
from ..models import (
    ArchetypeAdaptation,
    CalcResult,
    MGLensResult,
    QuestionAnswer,
    Stage7ProcessOutcome,
    Stage7Report,
    Stage7SemanticReview,
)
from .archetype import a7_or_acquisitive, adapt_from_prior
from .benchmark import label_benchmarks, _tag_false_positives
from .calc import compute_stage7_metrics
from .questions import (
    MG_LENSES,
    MUST_QUESTIONS,
    S6_H7_CONSUMABLE,
    SHOULD_QUESTIONS,
    STAGE7_OUTCOMES,
)
from .semantic import (
    incentive_evidence_depth,
    load_stage7_semantic_from_fixture,
    looks_like_toc_excerpt,
    placeholder_stage7_semantic,
    semantic_text_blob,
)


def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        fv = float(v)
        if abs(fv) < 1 and fv != 0:
            return f"{fv:.4f}"
        if abs(fv) < 100:
            return f"{fv:.2f}"
        return f"{fv:,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _must_map() -> dict[str, str]:
    return {qid: q for qid, q in MUST_QUESTIONS}


def _ingest_s6_flags(stage6_artifact: dict[str, Any] | None) -> list[str]:
    """Consume S6_H7_* factually only — never invent, never erase IDs."""
    if not stage6_artifact:
        return []
    raw = stage6_artifact.get("stage7_handoff_flags") or stage6_artifact.get(
        "s6_handoff_flags"
    ) or []
    out = []
    for f in raw:
        if f in S6_H7_CONSUMABLE:
            out.append(f)
    return list(dict.fromkeys(out))


def _alignment_label(
    *,
    semantic: Stage7SemanticReview | None,
    hierarchy: dict[str, Any],
    thesis_capital: str | None,
    s6_flags: list[str],
    runway_label: str | None,
) -> tuple[str, str]:
    """stated vs revealed → aligned|tension|opaque|unknown — evidence labels, not scores."""
    stated = bool(semantic and semantic.stated_hierarchy_notes)
    revealed_rank = hierarchy.get("revealed_rank_desc") or []
    dominant = hierarchy.get("dominant_use")
    if not stated and not revealed_rank:
        return "unknown", "No stated hierarchy notes and no revealed cash-use rank"
    if not stated and revealed_rank:
        # Prefer honest opaque; note proxy/DEF 14A retrieval gaps vs confirmed thin disclosure
        proxy_miss = False
        if semantic:
            for f in semantic.findings:
                if f.topic == "filing_retrieval" and (f.section or "").upper() in {
                    "DEF 14A",
                    "DEFA14A",
                    "DEF14A",
                }:
                    proxy_miss = True
                    break
        if proxy_miss:
            return (
                "opaque",
                "Revealed cash uses present but stated hierarchy not extracted "
                "(DEF 14A/proxy primary unavailable — retrieval gap possible, "
                "not confirmed disclosure absence)",
            )
        return "opaque", "Revealed cash uses present but stated hierarchy not extracted"
    # Stated present
    blob = (semantic.stated_hierarchy_notes or "").lower() if semantic else ""
    tension_tokens = []
    if "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION" in s6_flags:
        tension_tokens.append("s6_thesis_tension")
    if thesis_capital and dominant:
        tc = thesis_capital.lower()
        if "acquisit" in tc and dominant not in {"acquisitions"}:
            tension_tokens.append("thesis_ma_vs_revealed")
        if "reinvest" in tc and dominant in {"dividends", "share_repurchases"}:
            if runway_label == "ample":
                tension_tokens.append("reinvest_thesis_vs_distribute_revealed")
        if "distribut" in tc or "return capital" in tc:
            if dominant == "acquisitions" and runway_label == "limited":
                tension_tokens.append("distribute_thesis_vs_acq_revealed")
    # Language vs dominant — only when stated language is one-sided vs revealed dominant.
    # CapEx/infra + return-of-capital / repurchase language together is coherent when
    # organic_capex (or buybacks) dominates; do not auto-tension dual-use hierarchies.
    reinvest_like = any(
        tok in blob
        for tok in (
            "reinvest",
            "infrastructure",
            "organic",
            "capex",
            "capital expenditure",
            "investing activities",
            "investments in",
            "cash commitments for investing",
        )
    )
    distribute_like = any(
        tok in blob
        for tok in ("repurchase", "buyback", "return of capital", "dividend", "capital return")
    )
    if distribute_like and dominant and dominant not in {"share_repurchases", "dividends"}:
        if not reinvest_like:
            tension_tokens.append("buyback_language_vs_other_dominant")
    if "acquisit" in blob and dominant and dominant != "acquisitions":
        # Dual hierarchy mentioning both M&A and other uses is OK; one-sided M&A claim vs other dominant → tension
        if not reinvest_like and not distribute_like:
            tension_tokens.append("ma_language_vs_other_dominant")
        elif dominant not in {"acquisitions"} and "toward acquiring" in blob and not reinvest_like:
            tension_tokens.append("ma_language_vs_other_dominant")
    if tension_tokens:
        return "tension", f"Stated vs revealed tension cues={tension_tokens}"
    return "aligned", f"Stated hierarchy notes present; revealed dominant={dominant}"


def _dividend_policy_label(
    *,
    semantic: Stage7SemanticReview | None,
    div_years: int,
) -> str:
    """Descriptive label — not a company-policy assertion.

    commitment-like requires explicit commit/policy language (or consecutive-increase
    framing without discretionary override). Bare historical "increase" alone is not
    enough when the filing states board discretion / residual dependence on capital needs.
    Evidence taxonomy: filing excerpt kind stays FACT/CLAIM; this label is SYSTEM_INFERENCE
    from that evidence.
    """
    blob = ""
    if semantic and semantic.dividend_policy_notes:
        blob = semantic.dividend_policy_notes.lower()
    if "special" in blob:
        return "special/ad hoc"
    if div_years == 0 and not blob:
        return "none"
    if div_years == 0:
        return "none"
    discretionary = any(
        tok in blob
        for tok in (
            "sole discretion",
            "at the discretion",
            "board discretion",
            "no obligation",
            "depend upon",
            "depends upon",
            "subject to",
            "not obligated",
        )
    )
    # Do NOT treat bare "Dividend Policy" section heading / word "policy" as commitment.
    # Require explicit commit/commitment language (or consecutive-increase without discretion).
    explicit_commit = (
        any(
            tok in blob
            for tok in (
                "committed to",
                "commitment to",
                "our policy is to pay",
                "policy of paying",
                "policy of returning",
                "maintain a dividend policy committed",
            )
        )
        or ("committed" in blob and "dividend" in blob)
    ) and not discretionary
    # Consecutive-increase framing can support commitment-like ONLY without discretion override
    consecutive_increase = (
        ("increase" in blob or "increased" in blob)
        and ("consecutive" in blob or "consecutive year" in blob)
        and not discretionary
    )
    if explicit_commit or consecutive_increase:
        return "commitment-like"
    # Historical payments / increases with discretionary language → residual (not policy claim)
    if discretionary and div_years >= 1:
        return "residual"
    if div_years >= 2:
        return "residual"
    if "increase" in blob and div_years >= 1:
        # Single increase mention without commit/policy/consecutive → residual not commitment
        return "residual"
    return "unknown"


def _execution_tag(semantic: Stage7SemanticReview | None) -> str:
    if not semantic or not semantic.guidance_delivery_notes:
        if semantic and any(f.topic == "guidance_delivery" for f in semantic.findings):
            return "insufficient_history"
        return "unknown"
    blob = (semantic.guidance_delivery_notes or "").lower()
    if "withdrew" in blob or "abandon" in blob or "goalpost" in blob:
        return "goalposts_moved"
    if "miss" in blob or "below" in blob:
        return "missed"
    if "reaffirm" in blob or "delivered" in blob or "achieved" in blob:
        return "delivered"
    if "update" in blob or "revised" in blob:
        return "partial"
    return "insufficient_history"


def _thesis_coherence(
    thesis_summary: str | None,
    thesis_capital: str | None,
    alignment: str,
    s6_flags: list[str],
) -> str:
    if not thesis_summary and not thesis_capital:
        return "unknown"
    if "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION" in s6_flags or alignment == "tension":
        return "strains"
    if alignment == "aligned":
        return "supports"
    return "unknown"


def evaluate_stage7(
    ticker: str,
    periods: list[dict[str, Any]],
    *,
    gate0_class: str = "operating",
    sources: list[str] | None = None,
    semantic: Stage7SemanticReview | None = None,
    semantic_notes_path: Path | None = None,
    thesis_summary: str | None = None,
    thesis_capital: str | None = None,
    business_notes: str | None = None,
    prior_archetype: dict[str, Any] | ArchetypeAdaptation | None = None,
    stage6_artifact: dict[str, Any] | None = None,
    unresolved_major_conflict: bool = False,
    peer_notes: str | None = None,
    force_primary: str | None = None,
) -> Stage7Report:
    """
    Evaluate Stage 7 Management / Capital Allocation.
    FI / non-operating Gate 0 → TOO_HARD refuse.
    terminates_later_stages always False. No Stage 8. No ROIC rewrite.
    """
    ticker = ticker.upper()
    sources = sources or []
    must_q = _must_map()

    if semantic is None:
        if semantic_notes_path:
            semantic = load_stage7_semantic_from_fixture(semantic_notes_path)
        else:
            semantic = placeholder_stage7_semantic()

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

    if gate0_class != "operating":
        reason = (
            f"Gate 0 class is '{gate0_class}' — Financial Institutions / non-operating "
            "are HARD OUT OF SCOPE for Stage 7 OpCo allocation logic; refuse"
        )
        for qid in [f"S7-M{i}" for i in range(1, 10)]:
            ans(qid, "blocked", reason, [])
        ans("S7-M10", "answered", f"process_outcome=TOO_HARD; {reason}", ["TOO_HARD"])
        for qid, qtext in SHOULD_QUESTIONS:
            answers.append(
                QuestionAnswer(
                    question_id=qid,
                    question=qtext,
                    status="blocked",
                    answer_summary="Stage 7 refused — Gate 0 ≠ operating",
                    evidence=[],
                    must=False,
                )
            )
        return Stage7Report(
            ticker=ticker,
            date=utc_now(),
            periods_used=[],
            sources=sources,
            process_outcome="TOO_HARD",
            why_bullets=[reason],
            carry_forward_concerns=[reason],
            hierarchy_bullets=[],
            s6_handoff_bullets=[],
            ma_process_bullets=[],
            distribution_bullets=[],
            incentive_bullets=[],
            communication_execution_bullets=[],
            fp_gov_succession_bullets=[],
            false_positive_tags=[],
            benchmark_results=[],
            mg_lenses=[],
            archetype=None,
            calc=CalcResult(),
            semantic=semantic,
            terminates_later_stages=False,
            refuse_reason=reason,
            question_answers=answers,
        )

    s6_flags = _ingest_s6_flags(stage6_artifact)
    runway_label = None
    if stage6_artifact:
        runway_label = stage6_artifact.get("runway_label")

    sem_blob = semantic_text_blob(semantic)
    archetype = adapt_from_prior(
        prior_archetype,
        thesis_summary=thesis_summary,
        business_notes=business_notes,
        semantic_text=sem_blob,
        force_primary=force_primary,
    )
    a7_depth = a7_or_acquisitive(archetype.primary_archetype, archetype.secondary_traits)

    calc = compute_stage7_metrics(periods_sorted)
    m = calc.metrics
    hierarchy = m.get("revealed_hierarchy") or {}
    share = m.get("share_trend") or {}
    debt_motives = list(m.get("debt_motive_tags") or ["unclear"])
    # Soft semantic override for debt motive notes
    if semantic and semantic.debt_motive_notes:
        blob = semantic.debt_motive_notes.lower()
        if "acquisition" in blob or "deal" in blob:
            if "deal_finance" not in debt_motives:
                debt_motives.insert(0, "deal_finance")
        if "refinanc" in blob:
            if "refi_ops" not in debt_motives:
                debt_motives.append("refi_ops")
        debt_motives = list(dict.fromkeys(debt_motives))

    alignment, alignment_why = _alignment_label(
        semantic=semantic,
        hierarchy=hierarchy,
        thesis_capital=thesis_capital,
        s6_flags=s6_flags,
        runway_label=runway_label,
    )
    div_policy = _dividend_policy_label(
        semantic=semantic, div_years=int(m.get("dividend_years_positive") or 0)
    )
    exec_tag = _execution_tag(semantic)
    thesis_coh = _thesis_coherence(
        thesis_summary, thesis_capital, alignment, s6_flags
    )

    periods_used = [
        {
            "period_key": p.get("period_key") or "",
            "version_id": p.get("version_id") or "",
            "accession": p.get("accession") or p.get("source_id"),
            "filed_at": p.get("filed_at"),
            "period_end": p.get("period_end"),
            "source_type": "Normalized",
        }
        for p in periods_sorted
        if p.get("period_type") == "FY"
    ][-5:]

    fp_tags = _tag_false_positives(
        calc_metrics=m,
        semantic=semantic,
        archetype=archetype,
        s6_flags=s6_flags,
    )
    mg_label_bundle = {
        "alignment_label": alignment,
        "execution_tag": exec_tag,
        "dividend_policy_label": div_policy,
    }
    bench = label_benchmarks(
        calc_metrics=m,
        archetype=archetype,
        semantic=semantic,
        fp_tags=fp_tags,
        mg_labels=mg_label_bundle,
        s6_flags=s6_flags,
        thesis_coherence=thesis_coh,
        peer_notes=peer_notes,
    )

    # --- Build MG lenses ---
    mg_lenses: list[MGLensResult] = []
    lens_names = {i: n for i, n in MG_LENSES}

    # MG1
    mg_lenses.append(
        MGLensResult(
            lens_id="MG1",
            lens_name=lens_names["MG1"],
            summary=f"alignment={alignment}; dominant_use={hierarchy.get('dominant_use')}; "
            f"revealed_rank={hierarchy.get('revealed_rank_desc')}",
            why=alignment_why,
            labels={
                "alignment": alignment,
                "alignment_evidence_kind": "SYSTEM_INFERENCE",
                "no_fixed_order": True,
            },
            evidence=[
                f"stated_notes={bool(semantic and semantic.stated_hierarchy_notes)}",
                f"multi_year_totals={hierarchy.get('multi_year_totals')}",
                "alignment_label=SYSTEM_INFERENCE from stated hierarchy notes + revealed cash-use rank",
                f"input_provenance_periods={(m.get('input_provenance') or {}).get('periods')}",
            ],
            s6_flags_consumed=[
                f for f in s6_flags if f == "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION"
            ],
        )
    )
    ans(
        "S7-M1",
        "answered" if alignment != "unknown" else "partial",
        f"Capital Allocation Coherence alignment={alignment}; {alignment_why}",
        [str(hierarchy.get("revealed_rank_desc"))],
    )
    why.append(f"MG1 alignment={alignment} (evidence_kind=SYSTEM_INFERENCE; evidence label, not score)")

    # MG2 — recognition/response; NO ROIC recompute
    mg2_flags = [
        f
        for f in s6_flags
        if f
        in {
            "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST",
            "S6_H7_CAPEX_PRODUCTIVITY_OPAQUE",
        }
    ]
    mg2_summary = (
        "Ask: recognized? changed behavior? explained? incentives consistent? "
        "— factual S6 consume only; no ROIC/ROIIC rewrite"
    )
    mg_lenses.append(
        MGLensResult(
            lens_id="MG2",
            lens_name=lens_names["MG2"],
            summary=mg2_summary,
            why=f"S6 flags consumed factually={mg2_flags or 'none'}; runway_from_s6={runway_label}",
            labels={"no_roic_recompute": True},
            evidence=[f"s6_runway={runway_label}"],
            s6_flags_consumed=mg2_flags,
        )
    )
    ans(
        "S7-M2",
        "answered",
        f"Opportunity recognition/response notes; S6 flags={mg2_flags}; no ROIC recompute",
        mg2_flags or ["no_destruction_flag"],
    )

    # MG3
    mg3_flags = [
        f
        for f in s6_flags
        if f in {"S6_H7_ACQ_RETURN_OPACITY", "S6_H7_DUAL_VIEW_CONFLICT"}
    ]
    mg3_escalate = a7_depth and "S6_H7_ACQ_RETURN_OPACITY" in s6_flags
    mg_lenses.append(
        MGLensResult(
            lens_id="MG3",
            lens_name=lens_names["MG3"],
            summary=(
                f"a7_depth_required={a7_depth}; deal_notes="
                f"{bool(semantic and semantic.deal_criteria_notes)}; "
                f"no_return_recalc; no_ma_bad_assumption"
            ),
            why="Process/behavior only; consume S6 acquisition flags factually",
            labels={"a7_mg3_depth_required": a7_depth, "no_return_recalc": True},
            evidence=[
                (semantic.deal_criteria_notes or "")[:200]
                if semantic and semantic.deal_criteria_notes
                else "deal_criteria_unknown"
            ],
            s6_flags_consumed=mg3_flags,
            escalate_to_human=mg3_escalate,
        )
    )
    ans(
        "S7-M3",
        "answered" if (a7_depth or semantic and semantic.deal_criteria_notes) else "partial",
        f"Acquisition discipline; a7_depth={a7_depth}; S6={mg3_flags}; no return recalc",
        mg3_flags,
    )
    if mg3_escalate:
        carry.append(
            "A7 + S6_H7_ACQ_RETURN_OPACITY — mandatory MG3 process depth; "
            "REVIEW_REQUIRED candidate (non-terminating; no mechanical bad-manager)"
        )

    # MG4
    mg_lenses.append(
        MGLensResult(
            lens_id="MG4",
            lens_name=lens_names["MG4"],
            summary=(
                f"gross_repurchase={_fmt(share.get('gross_repurchase_multi_year'))}; "
                f"net_share_change={_fmt(share.get('net_share_change'))} "
                f"({share.get('net_share_basis')}); "
                f"sbc={_fmt(share.get('sbc_expense_multi_year'))}; "
                f"div_policy={div_policy}; no_payout_threshold"
            ),
            why="Combined buybacks+dividends; always gross+net when data exist",
            labels={
                "dividend_policy": div_policy,
                "dividend_policy_evidence_kind": "SYSTEM_INFERENCE",
                "no_payout_threshold": True,
                "gross_and_net": True,
                "sbc_expense_uncertain": bool(share.get("sbc_expense_uncertain")),
            },
            evidence=[
                str(share.get("series", [])[:2]),
                f"sbc_expense_uncertain={share.get('sbc_expense_uncertain')}",
                f"sbc_uncertainty_notes={share.get('sbc_uncertainty_notes')}",
                "dividend_policy_label=SYSTEM_INFERENCE from dividend FACT/CLAIM excerpts + payment years",
                f"normalized_input_provenance={(m.get('input_provenance') or {}).get('periods')}",
            ],
        )
    )
    ans(
        "S7-M4",
        "answered"
        if share.get("gross_repurchase_multi_year") is not None
        or (m.get("dividend_years_positive") or 0) > 0
        else "partial",
        f"Distributions: gross={_fmt(share.get('gross_repurchase_multi_year'))}; "
        f"net_share={_fmt(share.get('net_share_change'))}; policy={div_policy}",
        ["no_payout_threshold"],
    )

    # MG5
    mg_lenses.append(
        MGLensResult(
            lens_id="MG5",
            lens_name=lens_names["MG5"],
            summary=f"debt_motive_tags={debt_motives}; no_solvency_retest",
            why="Stage 7 = why/how leverage; Stage 2 owns solvency",
            labels={"motives": debt_motives, "no_solvency_retest": True},
            evidence=[
                f"delta_debt={_fmt((m.get('debt_context') or {}).get('delta_total_debt'))}"
            ],
        )
    )
    ans(
        "S7-M5",
        "answered",
        f"Debt as allocation tool; motives={debt_motives}; soft-link Stage 2 only",
        debt_motives,
    )

    # MG6
    mg_lenses.append(
        MGLensResult(
            lens_id="MG6",
            lens_name=lens_names["MG6"],
            summary=(
                f"incentive_notes={bool(semantic and semantic.incentive_metrics_notes)}; "
                f"ownership_guidelines={bool(semantic and semantic.ownership_guidelines_notes)}; "
                f"cda_depth={incentive_evidence_depth(semantic)['depth']}; "
                f"semantic_cda_mvp; no_pay_db; no_iss_gate"
            ),
            why=(
                "Semantic-first CD&A MVP — absolute pay percentiles OUT OF V1 as gates; "
                "shallow/TOC presence ≠ PASS"
            ),
            labels={
                "no_pay_db": True,
                "no_iss_gate": True,
                "cda_depth": incentive_evidence_depth(semantic)["depth"],
            },
            evidence=[
                (semantic.incentive_metrics_notes or "")[:200]
                if semantic and semantic.incentive_metrics_notes
                else "cda_unknown"
            ],
            s6_flags_consumed=[
                f
                for f in s6_flags
                if f == "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST"
            ],
            escalate_to_human=bool(
                semantic
                and semantic.incentive_metrics_notes
                and "conflict" in (semantic.incentive_metrics_notes or "").lower()
            ),
        )
    )
    _cda_depth = incentive_evidence_depth(semantic)
    ans(
        "S7-M6",
        "answered" if _cda_depth["depth"] == "substantive" else "partial",
        (
            f"Incentive alignment CD&A depth={_cda_depth['depth']}; "
            f"toc_only={_cda_depth['toc_only']}; "
            f"metric_hits={_cda_depth['substantive_hits'][:3]}; "
            "no pay DB / ISS gates"
        ),
        [],
    )

    # MG7
    mg_lenses.append(
        MGLensResult(
            lens_id="MG7",
            lens_name=lens_names["MG7"],
            summary=(
                f"gov_notes={bool(semantic and semantic.governance_structure_notes)}; "
                f"related_party={bool(semantic and semantic.related_party_notes)}; "
                f"neutral_factual; no_structure_auto_grade"
            ),
            why="Neutral factual + mechanism; forbidden: founder premium / dual-class auto-neg / insider auto-pos",
            labels={"no_auto_grade": True},
            evidence=[
                (semantic.governance_structure_notes or "")[:200]
                if semantic and semantic.governance_structure_notes
                else "gov_unknown"
            ],
            escalate_to_human=bool(
                semantic
                and any(
                    f.topic == "related_party" and f.escalate_to_human
                    for f in semantic.findings
                )
            ),
        )
    )
    ans(
        "S7-M7",
        "answered"
        if semantic and semantic.governance_structure_notes
        else "partial",
        "Ownership/governance context — neutral factual; no auto premiums/penalties",
        [],
    )

    # MG8
    kinds = sorted(
        {
            f.evidence_kind
            for f in (semantic.findings if semantic else [])
            if f.evidence_kind
        }
    )
    mg8_flags = [f for f in s6_flags if f == "S6_H7_DISCLOSURE_QUALITY_CAPITAL"]
    # dual-view also surfaces honesty in MG8
    if "S6_H7_DUAL_VIEW_CONFLICT" in s6_flags:
        mg8_flags.append("S6_H7_DUAL_VIEW_CONFLICT")
    mg_lenses.append(
        MGLensResult(
            lens_id="MG8",
            lens_name=lens_names["MG8"],
            summary=(
                f"taxonomy_kinds={kinds}; execution_tag={exec_tag}; "
                f"polish_ne_evidence; no_stage4_6_operating_redo"
            ),
            why=(
                "FACT/GUIDANCE/MANAGEMENT_CLAIM/SYSTEM_INFERENCE mandatory; "
                "execution=commitment vs delivery; combined lens — taxonomy alone "
                "≠ PASS when execution_tag=unknown"
            ),
            labels={"execution_tag": exec_tag, "taxonomy": kinds},
            evidence=[
                (semantic.guidance_delivery_notes or "")[:200]
                if semantic and semantic.guidance_delivery_notes
                else "guidance_unknown"
            ],
            s6_flags_consumed=list(dict.fromkeys(mg8_flags)),
        )
    )
    ans(
        "S7-M8",
        "answered" if kinds else "partial",
        f"Communication taxonomy kinds={kinds}; execution={exec_tag}",
        kinds,
    )

    # MG9
    mg_lenses.append(
        MGLensResult(
            lens_id="MG9",
            lens_name=lens_names["MG9"],
            summary=(
                f"succession_notes={bool(semantic and semantic.succession_notes)}; "
                f"evidence_only; no_personality_speculation"
            ),
            why="Standalone succession/key-person — evidence only; not terminating on founder narratives",
            labels={"evidence_only": True, "no_speculation": True},
            evidence=[
                (semantic.succession_notes or "")[:200]
                if semantic and semantic.succession_notes
                else "succession_unknown"
            ],
        )
    )
    ans(
        "S7-M9",
        "answered"
        if semantic and semantic.succession_notes
        else "partial",
        "Succession/key-person evidence-only; no health/personality/motive speculation",
        [],
    )

    # SHOULD
    for qid, qtext in SHOULD_QUESTIONS:
        status = "partial"
        note = "SHOULD gap = monitor, not kill"
        if qid == "S7-S1":
            if semantic and semantic.related_party_notes:
                note = f"Related-party: {semantic.related_party_notes[:200]}"
                status = "answered"
                if any(
                    f.escalate_to_human and f.topic == "related_party"
                    for f in semantic.findings
                ):
                    monitors.append("Related-party materiality — HITL exception queue")
            else:
                note = "No related-party notes extracted"
        elif qid == "S7-S2":
            if semantic and semantic.buyback_policy_notes:
                note = f"Buyback policy: {semantic.buyback_policy_notes[:200]}"
                status = "answered"
            else:
                note = "Buyback policy language not extracted — monitor"
        elif qid == "S7-S3":
            note = f"Dividend policy label={div_policy}"
            status = "answered"
        elif qid == "S7-S4":
            note = "Prior-proxy CD&A drift — semantic MVP; deepen when both proxies available"
            status = "partial"
        elif qid == "S7-S5":
            note = "S7_H8_* deferred until Stage 8 research — no valuation carries invented"
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

    # Dashboard bullets
    rows = m.get("cash_use_rows") or []
    hierarchy_bullets = [
        f"alignment_label={alignment} (evidence_kind=SYSTEM_INFERENCE) — {alignment_why}",
        f"revealed_rank_desc={hierarchy.get('revealed_rank_desc')} (no fixed universal order)",
        f"multi_year_totals={hierarchy.get('multi_year_totals')}",
        f"latest_composition_pct={m.get('latest_composition_pct')}",
        f"debt_motive_tags={debt_motives} (when material; fold under hierarchy)",
        f"n_fy={m.get('n_fy')}; history_thin={ (m.get('history_flags') or {}).get('history_thin') }",
    ]
    s6_bullets = [
        "S6_H7_* ingested with provenance; absence ≠ clean bill; no ROIC rewrite",
        f"flags_consumed={s6_flags or '(none present on Stage 6 artifact)'}",
        f"s6_runway_label={runway_label}",
        "Posture: recognized? changed behavior? explained credibly? incentives consistent?",
        "No mechanical conversion of dual-view / opacity / destruction flags into bad-manager",
    ]
    if "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST" in s6_flags:
        s6_bullets.append(
            "PERSISTENT_VALUE_DESTRUCTIVE_REINVEST → REVIEW_REQUIRED candidate after synthesis "
            "(strong final-FA carry; not mechanical guilt)"
        )
    ma_bullets = [
        f"a7_mg3_depth_required={a7_depth}",
        f"deal_criteria_notes={ (semantic.deal_criteria_notes[:180] if semantic and semantic.deal_criteria_notes else 'UNKNOWN') }",
        f"S6 acq/dual flags={mg3_flags}",
        "M&A use ≠ auto bad; opacity without accountability → escalate evidence",
        "No silent ROIC rewrite to prove deal quality",
    ]
    dist_bullets = [
        f"gross_repurchase_multi_year={_fmt(share.get('gross_repurchase_multi_year'))}",
        f"sbc_expense_multi_year={_fmt(share.get('sbc_expense_multi_year'))}",
        f"net_share_change={_fmt(share.get('net_share_change'))} (basis={share.get('net_share_basis')})",
        f"dividend_policy_label={div_policy} (evidence_kind=SYSTEM_INFERENCE); "
        f"dividend_years_positive={m.get('dividend_years_positive')}",
        f"buyback_years_positive={m.get('buyback_years_positive')}",
        "No universal payout/buyback thresholds; buybacks+dividends = one system",
    ]
    if share.get("sbc_expense_uncertain"):
        dist_bullets.insert(
            2,
            "sbc_expense_uncertain=True — Normalized SOURCE_CONFLICT on sbc_expense "
            "(multiple GAAP tags); multi-year SBC is preferred-tag sum, not final FACT",
        )
    incentive_bullets = [
        f"incentive_metrics={ (semantic.incentive_metrics_notes[:180] if semantic and semantic.incentive_metrics_notes else 'UNKNOWN') }",
        f"ownership_guidelines={ (semantic.ownership_guidelines_notes[:180] if semantic and semantic.ownership_guidelines_notes else 'UNKNOWN') }",
        "Semantic CD&A MVP — no compensation DB; ISS/pay-percentile OUT OF V1 as gates",
        f"SBC multi-year={_fmt(share.get('sbc_expense_multi_year'))} (dilution honesty with MG4)",
    ]
    comm_bullets = [
        f"taxonomy_kinds_present={kinds}",
        f"execution_delivery_tag={exec_tag}",
        f"guidance_notes={ (semantic.guidance_delivery_notes[:180] if semantic and semantic.guidance_delivery_notes else 'UNKNOWN') }",
        "Never promote CLAIM→FACT silently; polish ≠ evidence",
        "Execution = did management execute the strategy/allocation it chose (≠ Stages 4–6 redo)",
    ]
    fp_gov_bullets = [
        f"governance={ (semantic.governance_structure_notes[:160] if semantic and semantic.governance_structure_notes else 'UNKNOWN') }",
        f"related_party={ (semantic.related_party_notes[:160] if semantic and semantic.related_party_notes else 'UNKNOWN') }",
        f"succession={ (semantic.succession_notes[:160] if semantic and semantic.succession_notes else 'UNKNOWN') }",
        "FP-M = flags not auto-fails; no FP score average; no count→outcome",
    ]

    # --- Process outcome (NON-TERMINATING) ---
    process_outcome: Stage7ProcessOutcome
    material_fps = [t for t in fp_tags if t.get("severity") == "material"]
    # Related-party → REVIEW_REQUIRED only on non-TOC body disclosure (Plan: human
    # materiality). TOC/page-index hits stay monitors — not mechanical escalation.
    material_escalations = [
        f
        for f in (semantic.findings if semantic else [])
        if f.escalate_to_human
        and f.materiality_judgment in {"material", "watchable"}
        and f.topic == "related_party"
        and not looks_like_toc_excerpt(f.excerpt)
    ]
    usable = bool(rows) or bool(semantic and semantic.filled)

    # Archetype uncertainty (e.g. A11 LOW) may reduce confidence / add monitors —
    # must NOT by itself escalate to REVIEW_REQUIRED (Stage 7 outcome = substantive
    # mgmt/allocation/incentive/gov/communication evidence needing human review).
    archetype_uncertain = bool(
        archetype
        and archetype.confidence in {"LOW", "UNKNOWN"}
    )
    if archetype_uncertain:
        monitors.append(
            f"Archetype {archetype.primary_archetype} confidence={archetype.confidence} "
            f"(path={archetype.classification_path}) — uncertainty monitor; not mechanical REVIEW_REQUIRED"
        )
        carry.append(
            f"Final-FA note: archetype={archetype.primary_archetype} "
            f"confidence={archetype.confidence} (not alone a Stage 7 REVIEW_REQUIRED driver)"
        )

    if gate0_class != "operating":
        process_outcome = "TOO_HARD"
    elif not periods_sorted and not (semantic and semantic.filled):
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — no Normalized periods and empty semantic"]
        carry.append("Stage 7 TOO_HARD: no allocation spine")
    elif unresolved_major_conflict and not usable:
        process_outcome = "TOO_HARD"
        why = ["Not evaluable — conflict and missing allocation spine"]
    elif (
        "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST" in s6_flags
        or mg3_escalate
        or thesis_coh == "falsifies"
    ):
        process_outcome = "REVIEW_REQUIRED"
        reasons = []
        if "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST" in s6_flags:
            reasons.append("S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST factual consume")
        if mg3_escalate:
            reasons.append("A7 + S6_H7_ACQ_RETURN_OPACITY mandatory MG3 depth")
        if thesis_coh == "falsifies":
            reasons.append("thesis_coherence=falsifies")
        why.append(
            "REVIEW_REQUIRED candidacy from: "
            + "; ".join(reasons)
            + " — final-FA carry (NON-TERMINATING; no auto-RED; no mechanical bad-manager)"
        )
    elif (
        material_fps
        or material_escalations
        or thesis_coh == "strains"
        or alignment == "tension"
        or ("S6_H7_DUAL_VIEW_CONFLICT" in s6_flags and a7_depth)
        or ("S6_H7_ACQ_RETURN_OPACITY" in s6_flags)
    ):
        process_outcome = "REVIEW_REQUIRED"
        why.append(
            "Material FP / A7 S6 opacity / dual-view+A7 / alignment tension / thesis strain — "
            "human exception queue (labels are evidence; not a count formula; non-terminating)"
        )
        for t in material_fps:
            carry.append(f"FP {t['id']}: {t.get('why')}")
    elif gaps or not semantic.filled or any(
        a.status == "partial" for a in answers if a.must and a.question_id != "S7-M10"
    ):
        process_outcome = "CONDITIONAL"
        why.append("Usable package with named monitors — gaps or partial MUST remain")
        for g in gaps:
            monitors.append(g)
            if g not in carry:
                carry.append(f"Monitor/gap: {g}")
        if not semantic.filled:
            monitors.append("Stage 7 semantic incomplete — deepen DEF 14A / hierarchy extraction")
    else:
        process_outcome = "PROCEED"
        why.append(
            "MUST answered honestly; allocation pack coherent; no material unresolved FP; "
            "continue with evidence (Stage 7 non-terminating by default)"
        )

    assert process_outcome in STAGE7_OUTCOMES
    why.append(
        f"process_outcome={process_outcome} (evidence_kind=SYSTEM_INFERENCE from "
        f"MG/archetype/S6 synthesis; terminates_later_stages=False; non-terminating default)"
    )

    # Carries for final FA (and later Stage 8 when it exists) — no S7_H8 invented
    if s6_flags:
        carry.append(f"Final-FA carry: S6_H7 flags={s6_flags}")
    if alignment in {"tension", "opaque"}:
        carry.append(f"Final-FA carry: MG1 alignment={alignment}")
    if exec_tag in {"missed", "goalposts_moved"}:
        carry.append(f"Final-FA carry: MG8 execution_tag={exec_tag}")

    ans(
        "S7-M10",
        "answered",
        (
            f"process_outcome={process_outcome}; carry_forward={len(carry)} items; "
            f"S6_H7_consumed={s6_flags}; FP-M={[t['id'] for t in fp_tags]}; "
            "Stage 7 does not alone mechanically terminate later stages; "
            "no label-count→outcome; no scores/colors/BUY-SELL; no ROIC recompute"
        ),
        [process_outcome, "terminates_later_stages=False"],
    )

    what_strong = []
    if alignment == "aligned":
        what_strong.append("Stated vs revealed hierarchy coherence notes present")
    if share.get("gross_repurchase_multi_year") is not None and share.get(
        "net_share_change"
    ) is not None:
        what_strong.append("Gross repurchase + net share both shown")
    if kinds:
        what_strong.append(f"Communication taxonomy samples present: {kinds}")

    what_break = []
    if a7_depth:
        what_break.append("A7 acquisition accountability / opacity (MG3)")
    if "levered_distribution" in debt_motives:
        what_break.append("Debt-funded distribution resilience (FP-M15 watch)")
    if not (semantic and semantic.incentive_metrics_notes):
        what_break.append("Incentive metric opacity / CD&A gap")
    what_break.append("CLAIM inflation / goalpost moves (MG8)")

    if m.get("n_fy", 0) < 3:
        gaps.append("Thin FY allocation history (<3)")
        monitors.append("Extend allocation history toward ~5 FY when available")

    return Stage7Report(
        ticker=ticker,
        date=utc_now(),
        periods_used=periods_used,
        sources=sources,
        process_outcome=process_outcome,
        why_bullets=why,
        carry_forward_concerns=list(dict.fromkeys(carry)),
        hierarchy_bullets=hierarchy_bullets,
        s6_handoff_bullets=s6_bullets,
        ma_process_bullets=ma_bullets,
        distribution_bullets=dist_bullets,
        incentive_bullets=incentive_bullets,
        communication_execution_bullets=comm_bullets,
        fp_gov_succession_bullets=fp_gov_bullets,
        false_positive_tags=fp_tags,
        benchmark_results=bench,
        mg_lenses=mg_lenses,
        archetype=archetype,
        alignment_label=alignment,
        dividend_policy_label=div_policy,
        debt_motive_tags=debt_motives,
        s6_handoff_flags_consumed=s6_flags,
        what_is_strong=what_strong,
        what_can_break=what_break,
        monitors=list(dict.fromkeys(monitors)),
        missing_ambiguous=list(dict.fromkeys(gaps + [
            f"{k}: {v}" for k, v in (calc.null_reasons or {}).items()
        ])),
        question_answers=answers,
        calc=calc,
        semantic=semantic,
        terminates_later_stages=False,
        thesis_coherence=thesis_coh,
        a7_mg3_depth_required=a7_depth,
    )
