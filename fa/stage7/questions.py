"""Stage 7 question spine — FROZEN from STAGE_7_MANAGEMENT_ALLOCATION_PLAN_v1.md §0.

No scores / colors / numeric gates. No ROIC recompute. No Stage 8.
"""
from __future__ import annotations

MUST_QUESTIONS = [
    (
        "S7-M1",
        "What capital hierarchy does management state vs reveal, and is Capital Allocation "
        "Coherence aligned / tension / opaque / unknown vs thesis + Stage 6 runway?",
    ),
    (
        "S7-M2",
        "Did management recognize the opportunity set and change allocation behavior when "
        "returns deteriorated (consume S6_H7_*; no ROIC/ROIIC recompute)?",
    ),
    (
        "S7-M3",
        "What acquisition process / accountability evidence exists (criteria, cadence, "
        "integration follow-through)? Consume S6_H7_*; A7 → mandatory depth; no return recalc.",
    ),
    (
        "S7-M4",
        "How do buybacks + dividends work as one Shareholder Distributions system "
        "(gross repurchase + net diluted-share change + SBC honesty; no payout thresholds)?",
    ),
    (
        "S7-M5",
        "Why/how is debt used as an allocation tool (motive tags)? Soft-link Stage 2 — "
        "no solvency retest.",
    ),
    (
        "S7-M6",
        "What do incentives actually pay for (semantic CD&A MVP: metrics, vesting, "
        "ownership guidelines, dilution) — evidence not score; no pay DB / ISS gates?",
    ),
    (
        "S7-M7",
        "What ownership / governance context should owners know (neutral factual + "
        "mechanism; no founder premium / dual-class auto-negative)?",
    ),
    (
        "S7-M8",
        "Are communications labeled FACT/GUIDANCE/MANAGEMENT CLAIM/SYSTEM INFERENCE, "
        "and does execution match prior commitments (delivery tags; no Stage 4–6 redo)?",
    ),
    (
        "S7-M9",
        "What succession / key-person evidence exists (standalone; evidence only; "
        "no personality/health/motive speculation)?",
    ),
    (
        "S7-M10",
        "Process outcome (PROCEED / CONDITIONAL / REVIEW_REQUIRED / TOO_HARD) + FP-M flags "
        "+ final-FA carries. NON-TERMINATING (terminates_later_stages=False). No BUY/SELL.",
    ),
]

SHOULD_QUESTIONS = [
    (
        "S7-S1",
        "Related-party materiality notes (HITL when material; flags not auto-fails).",
    ),
    (
        "S7-S2",
        "Buyback policy language honesty (price discipline vs offset-dilution vs silent).",
    ),
    (
        "S7-S3",
        "Dividend policy label (commitment-like | residual | special/ad hoc | none | unknown).",
    ),
    (
        "S7-S4",
        "Prior-proxy vs current CD&A metric drift (when both available).",
    ),
    (
        "S7-S5",
        "S7_H8_* vocabulary deferred until Stage 8 research — do not invent valuation carries.",
    ),
]

STAGE7_OUTCOMES = frozenset({"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"})

BENCHMARK_LABELS = frozenset(
    {
        "ABOVE_REFERENCE",
        "PASS",
        "BELOW_REFERENCE",
        "MIXED",
        "UNKNOWN",
        "NOT_APPLICABLE",
    }
)

# Method E MG-facing dimensions (labels + WHY; ≠ hard gate)
MG_BENCHMARK_DIMENSIONS = [
    ("MG1", "Capital Allocation Coherence (stated vs revealed + fit)"),
    ("MG2", "Opportunity Recognition & Allocation Response"),
    ("MG3", "Acquisition Discipline (process/behavior)"),
    ("MG4", "Shareholder Distributions (buybacks + dividends)"),
    ("MG5", "Debt as Allocation Tool (motive)"),
    ("MG6", "Incentive Alignment (CD&A semantic)"),
    ("MG7", "Ownership / Governance Context"),
    ("MG8", "Communication & Execution Credibility"),
    ("MG9", "Succession / Key-Person"),
]

MG_LENSES = [
    ("MG1", "Capital Allocation Coherence"),
    ("MG2", "Opportunity Recognition & Allocation Response"),
    ("MG3", "Acquisition Discipline"),
    ("MG4", "Shareholder Distributions"),
    ("MG5", "Debt as Allocation Tool"),
    ("MG6", "Incentive Alignment"),
    ("MG7", "Ownership / Governance Context"),
    ("MG8", "Communication & Execution Credibility"),
    ("MG9", "Succession / Key-Person"),
]

ALIGNMENT_LABELS = frozenset({"aligned", "tension", "opaque", "unknown"})

DEBT_MOTIVE_TAGS = frozenset(
    {
        "deal_finance",
        "levered_distribution",
        "refi_ops",
        "fortress_build",
        "cyclical_timing",
        "over_conservatism",
        "unclear",
    }
)

COMM_EVIDENCE_KINDS = frozenset(
    {"FACT", "GUIDANCE", "MANAGEMENT_CLAIM", "SYSTEM_INFERENCE"}
)

EXECUTION_DELIVERY_TAGS = frozenset(
    {
        "delivered",
        "partial",
        "missed",
        "goalposts_moved",
        "insufficient_history",
        "unknown",
    }
)

DIVIDEND_POLICY_LABELS = frozenset(
    {"commitment-like", "residual", "special/ad hoc", "none", "unknown"}
)

# Locked S6_H7_* catalogue Stage 7 may consume (factual only)
S6_H7_CONSUMABLE = frozenset(
    {
        "S6_H7_ACQ_RETURN_OPACITY",
        "S6_H7_DUAL_VIEW_CONFLICT",
        "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST",
        "S6_H7_CAPEX_PRODUCTIVITY_OPAQUE",
        "S6_H7_DISCLOSURE_QUALITY_CAPITAL",
        "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION",
    }
)

FALSE_POSITIVE_CATALOGUE = [
    ("FP-M1", "Charismatic founder = aligned owner"),
    ("FP-M2", "Large buybacks = shareholder-friendly"),
    ("FP-M3", "No dividend = unfriendly"),
    ("FP-M4", "Dividend aristocrat = disciplined allocator"),
    ("FP-M5", "Synergy slides = deal returns"),
    ("FP-M6", "ROIC-linked pay in title only"),
    ("FP-M7", "Dual-class = always bad governance"),
    ("FP-M8", "High insider ownership = always good"),
    ("FP-M9", "Beat-and-raise theatre = great execution"),
    ("FP-M10", "ESG / ISS top quartile = owner alignment"),
    ("FP-M11", "Low CapEx = efficient management"),
    ("FP-M12", "Serial acquirer integration excellence narrative"),
    ("FP-M13", "SBC non-cash → ignore dilution"),
    ("FP-M14", "Fortress cash + zero deployment = prudence"),
    ("FP-M15", "Activist-driven buyback wave = victory"),
]

# Allocation emphasis by archetype (Plan §17 / Research) — notes only, not grades
ALLOCATION_EMPHASIS_BY_ARCHETYPE = {
    "A1": ["distribute_vs_reinvest", "franchise_stewardship"],
    "A2": ["sbc_dilution_honesty", "ma_outlet", "buyback_policy"],
    "A3": ["buyback_heavy_capital_light", "delta_ic_not_redo"],
    "A4": ["cycle_capex_communication", "peak_narrative"],
    "A5": ["sustaining_vs_growth_honesty", "debt_motive"],
    "A6": ["store_capex_vs_distribute", "wc_discipline"],
    "A7": ["mg3_mandatory_depth", "s6_flag_consume", "acq_accountability"],
    "A8": ["cycle_distribution_waves", "sustaining_capex"],
    "A9": ["fleet_capex_timing", "leverage_cycle"],
    "A10": ["segment_allocation_coherence"],
    "A11": ["explicit_why_required", "human_bias_if_unclear"],
}

from fa.stage4.questions import PRIMARY_ARCHETYPES  # noqa: E402 — reuse locked A1–A11

__all__ = [
    "MUST_QUESTIONS",
    "SHOULD_QUESTIONS",
    "STAGE7_OUTCOMES",
    "BENCHMARK_LABELS",
    "MG_BENCHMARK_DIMENSIONS",
    "MG_LENSES",
    "ALIGNMENT_LABELS",
    "DEBT_MOTIVE_TAGS",
    "COMM_EVIDENCE_KINDS",
    "EXECUTION_DELIVERY_TAGS",
    "DIVIDEND_POLICY_LABELS",
    "S6_H7_CONSUMABLE",
    "FALSE_POSITIVE_CATALOGUE",
    "ALLOCATION_EMPHASIS_BY_ARCHETYPE",
    "PRIMARY_ARCHETYPES",
]
