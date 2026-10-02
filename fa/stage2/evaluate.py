"""Question spine → Stage 2 report + process outcome. No numeric thresholds; no colors."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ids import utc_now
from ..models import (
    ProcessOutcome,
    QuestionAnswer,
    Stage2Report,
    StructuredSemanticReview,
)
from .calc import compute_stage2_metrics
from .semantic import load_semantic_from_fixture_notes, placeholder_semantic_review

MUST_QUESTIONS = [
    ("S2-M1", "Cash + near-cash vs near-term contractual obligations?"),
    ("S2-M2", "Shape of interest-bearing debt + lease liabilities — leverage optional or required?"),
    ("S2-M3", "What matures when? (current portion / buckets / note)"),
    ("S2-M4", "Credible liquidity headroom beyond cash (undrawn facilities)?"),
    ("S2-M5", "Going-concern, covenant, or liquidity red flags in MD&A/notes?"),
    ("S2-M6", "Working-capital stress patterns (receivables/inventory trends)?"),
    ("S2-M7", "Goodwill/intangibles share vs tangible/monetary assets?"),
    ("S2-M8", "Is restricted cash material relative to headline cash?"),
    ("S2-M9", "Plausible bad case: franchise intact or refinancing/dilution/liquidation problem?"),
    ("S2-M10", "Strong enough to proceed to later stages, or REVIEW / TOO HARD?"),
]

SHOULD_QUESTIONS = [
    ("S2-S1", "Off-balance / note-heavy commitments that change survival picture?"),
    ("S2-S2", "Pension / OPEB materiality?"),
    ("S2-S3", "Customer/supplier concentration that could accelerate WC shock?"),
    ("S2-S4", "FX / trapped multi-currency cash?"),
    ("S2-S5", "Controllable levers under stress (defer CapEx, cut distributions, equity)?"),
]

# Process outcomes that block Stage 3+
BLOCKING_OUTCOMES = {
    "TOO_HARD",
    "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY",
}


def _fmt_money(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)



def _prior_year_period(
    current: dict[str, Any] | None,
    periods: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find same-shape prior-year period for YoY companion (SD-W4-C3).

    FY2025 → FY2024; 2026Q3 → 2025Q3. No invention; None if not found.
    """
    if not current:
        return None
    key = str(current.get("period_key") or "")
    ptype = current.get("period_type")
    target = None
    if ptype == "FY" and key.startswith("FY") and key[2:].isdigit():
        target = f"FY{int(key[2:]) - 1}"
    else:
        # Quarterly like 2026Q3
        import re
        m = re.fullmatch(r"(\d{4})Q([1-4])", key)
        if m:
            target = f"{int(m.group(1)) - 1}Q{m.group(2)}"
    if not target:
        return None
    for d in periods:
        if d.get("period_key") == target:
            return d
    return None


def evaluate_stage2(
    ticker: str,
    periods: list[dict[str, Any]],
    *,
    gate0_class: str = "operating",
    sources: list[str] | None = None,
    semantic: StructuredSemanticReview | None = None,
    semantic_notes_path: Path | None = None,
    unresolved_major_conflict: bool = False,
    missing_critical_evidence: bool = False,
) -> Stage2Report:
    """
    Evaluate Stage 2 from Normalized CURRENT periods + semantic flags.

    Blocking is process-level only:
    - missing critical evidence
    - wrong Gate 0
    - unresolved major conflict
    - explicit going-concern / severe solvency language from semantic
    - credible near-term liquidity failure from semantic + evidence
    NOT ratio thresholds. High debt ratio alone does NOT auto-block.
    """
    ticker = ticker.upper()
    sources = sources or []

    if semantic is None:
        if semantic_notes_path:
            semantic = load_semantic_from_fixture_notes(semantic_notes_path)
        else:
            semantic = placeholder_semantic_review()

    # Sort periods: prefer FY then by period_key
    periods_sorted = sorted(
        periods,
        key=lambda d: (0 if d.get("period_type") == "FY" else 1, d.get("period_key") or ""),
        reverse=True,
    )
    current = periods_sorted[0] if periods_sorted else None
    prior = periods_sorted[1] if len(periods_sorted) > 1 else None

    block_reasons: list[str] = []
    gaps: list[str] = []

    # Gate 0
    if gate0_class != "operating":
        block_reasons.append(
            f"Gate 0 class is '{gate0_class}' — Operating Stage 2 contract out of scope (FI/Commodity)"
        )

    if unresolved_major_conflict:
        block_reasons.append("Unresolved major Normalized conflict (amendment/restatement)")

    if not current:
        missing_critical_evidence = True
        block_reasons.append("No Normalized CURRENT period available")

    prior_yoy = _prior_year_period(current, periods) if current else None
    calc = (
        compute_stage2_metrics(current, prior, prior_yoy=prior_yoy)
        if current
        else compute_stage2_metrics({"fields": {}})
    )

    # Critical evidence for Stage 2 honesty
    critical_fields = ["cash_and_equivalents", "total_assets", "equity_parent"]
    if current:
        fields = current.get("fields") or {}
        for cf in critical_fields:
            if fields.get(cf) is None:
                gaps.append(f"critical field null: {cf}")
        if fields.get("cash_and_equivalents") is None and fields.get("total_debt") is None:
            if fields.get("short_term_debt") is None and fields.get("long_term_debt") is None:
                missing_critical_evidence = True
                gaps.append("missing both cash and debt spine — cannot finish Stage 2 honestly")

    if missing_critical_evidence:
        block_reasons.append("Missing critical evidence for Stage 2")

    # Semantic blocking flags (explicit language / credible failure) — NOT ratios
    if semantic.going_concern_language:
        block_reasons.append(
            "Explicit going-concern language flagged in semantic review"
            + (f": {semantic.going_concern_excerpt}" if semantic.going_concern_excerpt else "")
        )
    if semantic.severe_solvency_language:
        block_reasons.append("Severe solvency language flagged in semantic review")
    if semantic.near_term_liquidity_failure_credible:
        block_reasons.append(
            "Credible near-term liquidity failure flagged (semantic + evidence)"
            + (
                f": {semantic.near_term_liquidity_notes}"
                if semantic.near_term_liquidity_notes
                else ""
            )
        )

    # Build question answers
    m = calc.metrics
    answers: list[QuestionAnswer] = []

    def ans(qid: str, q: str, status: str, summary: str, evidence: list[str], must: bool = True):
        answers.append(
            QuestionAnswer(
                question_id=qid,
                question=q,
                status=status,  # type: ignore[arg-type]
                answer_summary=summary,
                evidence=evidence,
                must=must,
            )
        )

    # M1
    if m.get("cash_vs_near_term_obligations") is not None:
        ans(
            "S2-M1",
            MUST_QUESTIONS[0][1],
            "answered",
            f"Cash(+STI) {_fmt_money(m.get('cash_plus_st_investments'))} vs near-term obligations "
            f"{_fmt_money(m.get('near_term_contractual_obligations'))} → gap "
            f"{_fmt_money(m.get('cash_vs_near_term_obligations'))}",
            [
                f"cash={_fmt_money(m.get('cash'))}",
                f"near_term={_fmt_money(m.get('near_term_contractual_obligations'))}",
            ],
        )
    else:
        ans(
            "S2-M1",
            MUST_QUESTIONS[0][1],
            "missing",
            calc.null_reasons.get("cash_vs_near_term_obligations", "incomplete"),
            [],
        )
        gaps.append("S2-M1 incomplete")

    # M2
    lev = semantic.leverage_optional_vs_required
    if m.get("lease_adjusted_contractual_debt") is not None or m.get("gross_debt") is not None:
        debt_incomplete = bool(m.get("gross_debt_incomplete"))
        opco_fs_unavail = bool(m.get("opco_fs_split_unavailable"))
        status = "partial" if debt_incomplete or lev == "not_assessed" else "answered"
        honesty_bits = []
        if debt_incomplete:
            honesty_bits.append(
                "gross_debt_incomplete=True (LTD null with other interest-bearing/"
                "securitization evidence — not a complete consolidated debt figure)"
            )
        if opco_fs_unavail:
            honesty_bits.append(
                "opco_fs_split_unavailable=True (no honest Equip vs FS dual debt view "
                "without structured segment tags — do not invent OpCo-only)"
            )
        if m.get("secured_debt") is not None:
            honesty_bits.append(f"secured_debt={_fmt_money(m.get('secured_debt'))}")
        if m.get("debt_view_label"):
            honesty_bits.append(f"debt_view_label={m.get('debt_view_label')}")
        ans(
            "S2-M2",
            MUST_QUESTIONS[1][1],
            status,
            f"Gross debt {_fmt_money(m.get('gross_debt'))}; lease-adj "
            f"{_fmt_money(m.get('lease_adjusted_contractual_debt'))}; net_debt "
            f"{_fmt_money(m.get('net_debt'))}; leverage assessment={lev}"
            + (("; " + "; ".join(honesty_bits)) if honesty_bits else ""),
            [
                f"debt/equity={m.get('debt_to_equity')}",
                f"debt/assets={m.get('debt_to_assets')}",
                "NOTE: ratios are descriptive only — not pass/fail thresholds",
            ]
            + honesty_bits,
        )
        if debt_incomplete:
            gaps.append(
                "S2-M2 gross_debt_incomplete — do not treat ST-only/partial sum as complete EV debt; "
                "OpCo vs FS dual view requires structured tags or REVIEW/TOO_HARD"
            )
            if opco_fs_unavail:
                block_reasons.append(
                    "Debt perimeter incomplete with secured/securitization present; "
                    "honest OpCo vs FS split unavailable — REVIEW before OpCo-only EV"
                )
    else:
        ans("S2-M2", MUST_QUESTIONS[1][1], "missing", "debt/lease spine incomplete", [])
        gaps.append("S2-M2 incomplete")

    # M3
    if m.get("debt_maturity_buckets") or m.get("near_term_contractual_obligations") is not None:
        status = "answered" if m.get("debt_maturity_buckets") else "partial"
        ans(
            "S2-M3",
            MUST_QUESTIONS[2][1],
            status,
            semantic.maturity_notes
            or f"current portion / near-term={_fmt_money(m.get('near_term_contractual_obligations'))}; "
            f"buckets={m.get('debt_maturity_buckets')}",
            [str(m.get("maturity_aggregation") or m.get("debt_maturity_buckets") or "coarse only")],
        )
    else:
        ans("S2-M3", MUST_QUESTIONS[2][1], "missing", "no maturity visibility", [])
        gaps.append("S2-M3 incomplete")

    # M4
    undrawn = m.get("undrawn_facilities")
    if undrawn is not None or semantic.undrawn_facilities_notes:
        ans(
            "S2-M4",
            MUST_QUESTIONS[3][1],
            "answered",
            semantic.undrawn_facilities_notes or f"undrawn facilities field={undrawn}",
            [str(undrawn)],
        )
    else:
        ans(
            "S2-M4",
            MUST_QUESTIONS[3][1],
            "partial",
            "Undrawn facilities not in Normalized (often note-only) — monitor / REVIEW if material",
            [],
        )
        gaps.append("S2-M4 undrawn facilities null")

    # M5
    flags = []
    if semantic.going_concern_language:
        flags.append("going-concern")
    if semantic.covenants_notes:
        flags.append("covenant notes present")
    flags.extend(semantic.liquidity_mdna_flags)
    if flags or semantic.filled:
        ans(
            "S2-M5",
            MUST_QUESTIONS[4][1],
            "answered",
            "; ".join(flags) if flags else "No going-concern/covenant red flags in semantic fixture",
            flags or ["semantic clear"],
        )
    else:
        ans(
            "S2-M5",
            MUST_QUESTIONS[4][1],
            "partial",
            "Semantic review not filled — human/LLM note read pending",
            [],
        )
        gaps.append("S2-M5 semantic pending")

    # M6
    if m.get("delta_receivables") is not None or m.get("delta_inventory") is not None:
        ans(
            "S2-M6",
            MUST_QUESTIONS[5][1],
            "answered",
            f"Δreceivables={_fmt_money(m.get('delta_receivables'))}; "
            f"Δinventory={_fmt_money(m.get('delta_inventory'))}",
            [],
        )
    else:
        ans(
            "S2-M6",
            MUST_QUESTIONS[5][1],
            "partial",
            calc.null_reasons.get("wc_trends", "WC trends incomplete"),
            [],
        )

    # M7
    if m.get("gw_intangibles_share_of_equity") is not None:
        ans(
            "S2-M7",
            MUST_QUESTIONS[6][1],
            "answered",
            f"GW+intangibles={_fmt_money(m.get('goodwill_plus_intangibles'))}; "
            f"share of equity={m.get('gw_intangibles_share_of_equity')}",
            [],
        )
    else:
        ans("S2-M7", MUST_QUESTIONS[6][1], "partial", "GW/intangibles or equity missing", [])

    # M8
    if m.get("restricted_cash_amount") is not None or semantic.restricted_cash_notes:
        ans(
            "S2-M8",
            MUST_QUESTIONS[7][1],
            "answered",
            semantic.restricted_cash_notes
            or f"restricted_cash={_fmt_money(m.get('restricted_cash_amount'))}; "
            f"unrestricted_proxy={_fmt_money(m.get('unrestricted_cash_proxy'))}",
            [],
        )
    else:
        ans(
            "S2-M8",
            MUST_QUESTIONS[7][1],
            "partial",
            "Restricted cash not disclosed in Normalized",
            [],
        )

    # M9 — qualitative from semantic + evidence presence
    if semantic.near_term_liquidity_failure_credible or semantic.going_concern_language:
        ans(
            "S2-M9",
            MUST_QUESTIONS[8][1],
            "blocked",
            "Semantic flags indicate plausible permanent-impairment / liquidity path risk",
            block_reasons[:],
        )
    elif current:
        ans(
            "S2-M9",
            MUST_QUESTIONS[8][1],
            "partial",
            "Descriptive BS available; bad-case judgment requires human (no auto threshold)",
            ["human judgment required — no numeric pass/fail"],
        )
    else:
        ans("S2-M9", MUST_QUESTIONS[8][1], "missing", "no period data", [])

    # SHOULD (brief)
    for qid, qtext in SHOULD_QUESTIONS:
        note = None
        if qid == "S2-S1":
            note = semantic.off_balance_commitments_notes
        status = "answered" if note else "partial"
        ans(qid, qtext, status, note or "not assessed in dry-run placeholder", [], must=False)

    # Determine process outcome
    process_outcome: ProcessOutcome
    narrative: str
    enough: str
    enough_why: str
    block_next = False

    fragility_blocks = [
        r
        for r in block_reasons
        if "going-concern" in r.lower()
        or "solvency" in r.lower()
        or "liquidity failure" in r.lower()
    ]
    structural_blocks = [
        r
        for r in block_reasons
        if r not in fragility_blocks
    ]

    must_missing = [a for a in answers if a.must and a.status == "missing"]
    must_ids_missing = {a.question_id for a in must_missing}

    if gate0_class != "operating":
        process_outcome = "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY"
        # Actually wrong gate0 is more TOO_HARD / blocked process — use TOO_HARD for wrong class
        process_outcome = "TOO_HARD"
        narrative = "Not enough evidence to proceed (REVIEW / TOO HARD)"
        enough = "No"
        enough_why = "Gate 0 ≠ operating; Operating Stage 2 does not apply"
        block_next = True
    elif fragility_blocks:
        process_outcome = "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY"
        narrative = "Not enough evidence to proceed (REVIEW / TOO HARD)"
        enough = "No"
        enough_why = "; ".join(fragility_blocks)
        block_next = True
    elif any("Missing critical" in r or "No Normalized" in r for r in structural_blocks):
        process_outcome = "TOO_HARD"
        narrative = "Not enough evidence to proceed (REVIEW / TOO HARD)"
        enough = "No"
        enough_why = "; ".join(structural_blocks) or "critical evidence missing"
        block_next = True
    elif m.get("gross_debt_incomplete") and m.get("opco_fs_split_unavailable"):
        # Wave2 A1: incomplete interest-bearing perimeter + no honest OpCo/FS split
        process_outcome = "REVIEW_REQUIRED"
        narrative = "Monitor-heavy — incomplete or mixed; continue only if listed monitors are watchable"
        enough = "No"
        enough_why = (
            "Interest-bearing debt incomplete (LTD null with securitization/other evidence) "
            "and OpCo vs FS dual debt view unavailable — do not publish understated single debt "
            "as complete; REVIEW / TOO_HARD on OpCo-only EV path"
        )
        block_next = True
    elif unresolved_major_conflict or any("conflict" in r.lower() for r in structural_blocks):
        process_outcome = "REVIEW_REQUIRED"
        narrative = "Monitor-heavy — incomplete or mixed; continue only if listed monitors are watchable"
        enough = "No"
        enough_why = "Unresolved conflict requires human review before later stages"
        block_next = True
    elif must_ids_missing & {"S2-M1", "S2-M2"} or len(must_missing) >= 4:
        process_outcome = "REVIEW_REQUIRED"
        narrative = "Monitor-heavy — incomplete or mixed; continue only if listed monitors are watchable"
        enough = "Conditional"
        enough_why = f"Key MUST questions incomplete: {[a.question_id for a in must_missing]}"
        block_next = True
    elif gaps and (must_missing or not semantic.filled):
        process_outcome = "CONDITIONAL"
        narrative = "Fragile / elevated survival risk — proceed only with eyes open + monitors"
        # Actually CONDITIONAL can be milder — use monitor-heavy if gaps only
        if must_missing:
            narrative = "Monitor-heavy — incomplete or mixed; continue only if listed monitors are watchable"
        enough = "Conditional"
        enough_why = "Gaps remain but core spine present; monitors required"
        block_next = False
    elif semantic.leverage_optional_vs_required == "required":
        process_outcome = "CONDITIONAL"
        narrative = "Fragile / elevated survival risk — proceed only with eyes open + monitors"
        enough = "Conditional"
        enough_why = "Leverage assessed as required for model (Smith-type) — not auto-blocked; monitors"
        block_next = False
    else:
        process_outcome = "PROCEED"
        narrative = "Strong enough BS to proceed"
        enough = "Yes"
        enough_why = "Core MUST spine answerable; no process-level block flags"
        block_next = False

    # M10
    ans(
        "S2-M10",
        MUST_QUESTIONS[9][1],
        "answered",
        f"process_outcome={process_outcome}; enough={enough}; {enough_why}",
        [process_outcome],
    )

    periods_used = []
    for p in periods_sorted:
        periods_used.append(
            {
                "period_key": p.get("period_key", ""),
                "version_id": p.get("version_id", ""),
            }
        )

    evidence_bullets = {
        "liquidity": [
            f"cash={_fmt_money(m.get('cash'))}",
            f"restricted={_fmt_money(m.get('restricted_cash_amount'))}",
            f"facilities={m.get('undrawn_facilities')}",
            f"cash_vs_near_term={_fmt_money(m.get('cash_vs_near_term_obligations'))}",
        ],
        "contractual_leverage": [
            f"gross_debt={_fmt_money(m.get('gross_debt'))}",
            f"leases={_fmt_money(m.get('lease_liability_total'))}",
            f"lease_adj={_fmt_money(m.get('lease_adjusted_contractual_debt'))}",
            f"current_portion={_fmt_money((current or {}).get('fields', {}).get('current_portion_ltd')) if current else None}",
        ],
        "maturities": [
            str(m.get("debt_maturity_buckets") or semantic.maturity_notes or "not disclosed in Normalized"),
        ],
        "wc_signals": [
            f"Δrecv={_fmt_money(m.get('delta_receivables'))}",
            f"Δinv={_fmt_money(m.get('delta_inventory'))}",
        ],
        "soft_equity": [
            f"GW+intang={_fmt_money(m.get('goodwill_plus_intangibles'))}",
            f"share_equity={m.get('gw_intangibles_share_of_equity')}",
        ],
        "note_flags": [
            f"going_concern={semantic.going_concern_language}",
            f"covenants={semantic.covenants_notes or 'n/a'}",
            f"other={semantic.other_flags}",
        ],
    }

    thesis_parts = [
        f"{ticker} Stage 2 process outcome: {process_outcome}.",
        f"Lease-adjusted contractual debt {_fmt_money(m.get('lease_adjusted_contractual_debt'))}; "
        f"cash(+STI) {_fmt_money(m.get('cash_plus_st_investments'))}.",
    ]
    if semantic.leverage_optional_vs_required != "not_assessed":
        thesis_parts.append(f"Leverage vs model: {semantic.leverage_optional_vs_required}.")
    thesis_parts.append(enough_why)

    monitors = []
    if m.get("undrawn_facilities") is None:
        monitors.append("Confirm undrawn facilities / covenant headroom from notes")
    if m.get("debt_maturity_buckets") is None:
        monitors.append("Obtain debt maturity schedule from notes")
    if not semantic.filled:
        monitors.append("Complete semantic MD&A / notes review (covenants, GC, liquidity)")
    for g in gaps:
        if g not in monitors:
            monitors.append(g)

    falsifiers = [
        "New going-concern or covenant-breach disclosure",
        "Near-term maturity wall without disclosed refinance path",
        "Restatement that breaks CURRENT Normalized acceptance",
        "Evidence that leverage is structurally required and liquidity fails under stress",
    ]

    # REVIEW_REQUIRED with block_next already set above for conflict/missing musts
    if process_outcome in BLOCKING_OUTCOMES:
        block_next = True
    if process_outcome == "REVIEW_REQUIRED" and block_next:
        pass

    return Stage2Report(
        ticker=ticker,
        date=utc_now(),
        periods_used=periods_used,
        sources=sources,
        process_outcome=process_outcome,
        narrative_verdict=narrative,
        survival_thesis=" ".join(thesis_parts),
        evidence_bullets=evidence_bullets,
        falsifiers=falsifiers,
        monitors=monitors,
        gaps=gaps,
        enough_to_proceed=enough,  # type: ignore[arg-type]
        enough_why=enough_why,
        question_answers=answers,
        calc=calc,
        semantic=semantic,
        block_next=block_next,
        block_reasons=block_reasons,
    )
