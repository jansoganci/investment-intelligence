"""Stage 8 question spine — FROZEN from STAGE_8_VALUATION_PLAN_v1.md §0.

No scores / colors / BUY/SELL / universal MoS% / P/E gates. No Stage 9.
"""
from __future__ import annotations

MUST_QUESTIONS = [
    (
        "S8-M1",
        "What is the market-value bridge (price → equity → EV) and session-aware "
        "freshness/provenance (CURRENT|RECENT|STALE|UNKNOWN)?",
    ),
    (
        "S8-M2",
        "Is the normalized earnings/CF/OE base honest for this archetype "
        "(normalization_uncertainty exposed; no aggressive norm)?",
    ),
    (
        "S8-M3",
        "What defensible intrinsic-value RANGE (conservative/central/optimistic) "
        "is constructible from Stages 1–7 — or NOT_APPLICABLE + WHY?",
    ),
    (
        "S8-M4",
        "What expectations does reverse DCF imply "
        "(conservative|plausible|demanding|heroic|incoherent_with_evidence|unknown) "
        "vs Stage 4–6 evidence — not cheap/expensive?",
    ),
    (
        "S8-M5",
        "What multiples + own-history context (Method E) apply — selective peers or N/A; "
        "no P/E gates / peer percentiles / mean=fair?",
    ),
    (
        "S8-M6",
        "How do filing-period capital structure, dilution/SBC, and debt/cash enter the "
        "bridge (no double-count; diluted trajectory)?",
    ),
    (
        "S8-M7",
        "What Margin-of-Safety evidence exists (range position, scenario spread, "
        "qualitative) — no universal % gate?",
    ),
    (
        "S8-M8",
        "What is valuation uncertainty (low|moderate|high|extreme|unanalyzable) + drivers, "
        "including method/terminal disagreement?",
    ),
    (
        "S8-M9",
        "VA1–VA8 labels + WHY (no weighted average) + S1–7 conflicts surfaced?",
    ),
    (
        "S8-M10",
        "Process outcome (PROCEED/CONDITIONAL/REVIEW_REQUIRED/TOO_HARD). "
        "NON-TERMINATING. Never BUY/SELL/colors/cheap-expensive auto-verdict.",
    ),
]

SHOULD_QUESTIONS = [
    (
        "S8-S1",
        "A7 dual organic vs acquisition exhibits + recurring M&A as reinvestment "
        "(consume S6_H7_*; no free-organic acquired growth; no deal-by-deal DCF)?",
    ),
    (
        "S8-S2",
        "Dual-terminal CROSS-CHECKS (perpetual-growth + exit-multiple) when DCF runs "
        "— never average; never silent override?",
    ),
    (
        "S8-S3",
        "Post-period material financing / acquisition / issuance / buyback flags?",
    ),
    (
        "S8-S4",
        "Currency reconciliation explicit (no silent mix)?",
    ),
    (
        "S8-S5",
        "S7_H8_* / S8_H9_* carries for final FA / Stage 9 notes (trim-ready)?",
    ),
]

STAGE8_OUTCOMES = frozenset({"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"})

STALENESS_CLASSES = frozenset({"CURRENT", "RECENT", "STALE", "UNKNOWN"})

EXPECTATIONS_VOCAB = frozenset(
    {
        "conservative",
        "plausible",
        "demanding",
        "heroic",
        "incoherent_with_evidence",
        "unknown",
    }
)

UNCERTAINTY_VOCAB = frozenset(
    {"low", "moderate", "high", "extreme", "unanalyzable"}
)

SCENARIO_NAMES = frozenset({"conservative", "central", "optimistic"})

DISCOUNT_CLASSES = frozenset(
    {
        "low_uncertainty_franchise",
        "standard_opco",
        "high_uncertainty",
        "cyclical_elevated",
    }
)

VA_LENSES = [
    ("VA1", "Market-Value Bridge & Freshness"),
    ("VA2", "Normalized Base Honesty"),
    ("VA3", "Intrinsic-Value Range"),
    ("VA4", "Reverse DCF / Embedded Expectations"),
    ("VA5", "Multiples & Historical Context"),
    ("VA6", "Capital Structure / Dilution Bridge"),
    ("VA7", "Margin of Safety Evidence"),
    ("VA8", "Uncertainty & Method Disagreement"),
]

# Method E valuation-facing dimensions (labels + WHY; ≠ hard gate)
VA_BENCHMARK_DIMENSIONS = [
    ("VA1", "Market-Value Bridge & Freshness"),
    ("VA2", "Normalized Base Honesty"),
    ("VA3", "Intrinsic-Value Range"),
    ("VA4", "Reverse DCF / Embedded Expectations"),
    ("VA5", "Multiples & Historical Context (Method E)"),
    ("VA6", "Capital Structure / Dilution Bridge"),
    ("VA7", "Margin of Safety Evidence"),
    ("VA8", "Uncertainty & Method Disagreement"),
]

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

PRIMARY_ARCHETYPES = {
    "A1": "Capital-light compounder",
    "A2": "SBC / dilution-sensitive growth",
    "A3": "Mature cash cow",
    "A4": "Heavy CapEx / project",
    "A5": "Working-capital intensive",
    "A6": "Regulated / utility-like",
    "A7": "Acquisitive compounder",
    "A8": "Commodity / price-taker cyclical",
    "A9": "Volume / capacity cyclical",
    "A10": "Turnaround / restructuring",
    "A11": "Hard-to-classify / special situation",
}

VALUATION_EMPHASIS_BY_ARCHETYPE = {
    "A1": ["reverse_dcf_duration", "owner_earnings", "fcf_yield_context"],
    "A2": ["dilution_path", "fcf_per_share", "sbc_honesty"],
    "A3": ["fcff_range", "distribution_sustainability", "own_history_multiples"],
    "A4": ["selective_extend", "capex_cycle", "fcff_with_reinvestment"],
    "A5": ["wc_normalized_base", "fcff", "bridge_cash_honesty"],
    "A6": ["regulated_base", "mid_cycle_like", "own_history"],
    "A7": [
        "recurring_ma_as_reinvestment",
        "organic_vs_acq_exhibits",
        "s6_h7_consume",
        "no_free_organic_acq_growth",
    ],
    "A8": ["mid_cycle_mandatory", "peak_capitalization_watch", "cycle_note_s8_h9"],
    "A9": ["mid_cycle_mandatory", "capacity_cycle", "cycle_note_s8_h9"],
    "A10": ["uncertainty_first", "too_hard_bias", "scenario_spread"],
    "A11": ["explicit_why_or_too_hard", "method_disagreement", "uncertainty_first"],
}

S6_H7_CONSUMABLE = frozenset(
    {
        "S6_H7_DUAL_VIEW_CONFLICT",
        "S6_H7_ACQ_RETURN_OPACITY",
        "S6_H7_ROIIC_DETERIORATION",
        "S6_H7_RUNWAY_LIMITED_DISTRIBUTE",
        "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION",
        "S6_H7_IC_BRIDGE_OPAQUE",
        "S6_H7_INCREMENTAL_NOT_MEANINGFUL",
    }
)

S7_H8_CARRIES = frozenset(
    {
        "S7_H8_DILUTION_MATERIAL",
        "S7_H8_BUYBACK_PRICE_DISCIPLINE_OPAQUE",
        "S7_H8_ALLOCATION_UNCERTAINTY_FOR_VALUATION",
    }
)

S8_H9_CARRIES = frozenset(
    {
        "S8_H9_CYCLE_SENSITIVE_VALUATION",
        "S8_H9_EXPECTATIONS_DEMANDING",
    }
)

# FP-V1–V20 catalogue (flags-not-auto-fails; Research §19 / Plan §19)
FALSE_POSITIVE_CATALOGUE = [
    ("FP-V1", "Trailing P/E worship as value", "high"),
    ("FP-V2", "One point-estimate fair value as truth", "high"),
    ("FP-V3", "Mechanical method average as truth", "high"),
    ("FP-V4", "Peak-cycle capitalization as cheap", "high"),
    ("FP-V5", "Peer percentile = undervalued", "medium"),
    ("FP-V6", "Historical mean multiple = fair", "medium"),
    ("FP-V7", "Silent stale price in MoS/IV", "high"),
    ("FP-V8", "Fresh price + materially stale capital structure", "high"),
    ("FP-V9", "Currency mix without reconcile", "high"),
    ("FP-V10", "Acquired growth treated as free organic", "high"),
    ("FP-V11", "SBC non-cash = free", "high"),
    ("FP-V12", "Deal-by-deal M&A DCF as primary", "medium"),
    ("FP-V13", "Aggressive normalization manufacturing precision", "high"),
    ("FP-V14", "Fat statistical cheapness on weak business", "medium"),
    ("FP-V15", "Demanding expectations auto-SELL", "high"),
    ("FP-V16", "CAPM β precision theatre", "medium"),
    ("FP-V17", "Exit multiple silent peer-median circularity", "medium"),
    ("FP-V18", "Terminal dominance ignored", "medium"),
    ("FP-V19", "Quality blended into lower discount as gate", "high"),
    ("FP-V20", "Undated/prior-UAT price silent reuse", "high"),
]

EVIDENCE_KINDS = frozenset({"FACT", "COMPANY_EXPLANATION", "MODEL_INFERENCE"})
