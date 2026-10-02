"""Stage 6 question spine — FROZEN from STAGE_6_ROIC_REINVESTMENT_PLAN_v1.md §0.

No numeric ROIC/ROIIC/WACC thresholds. IOM ≠ ROIIC. No Stage 7.
"""
from __future__ import annotations

MUST_QUESTIONS = [
    (
        "S6-M1",
        "Over a multi-period window (~5 FY + ~8Q), what is definition-honest ROIC "
        "(acquisition-inclusive PRIMARY; tangible companion when required), with NOPAT/IC labels?",
    ),
    (
        "S6-M2",
        "What does incremental ROIC (ΔNOPAT/ΔIC) show across 1Y / 3Y primary / 5Y — "
        "and which meaning class applies? (≠ Stage 5 Incremental OM)",
    ),
    (
        "S6-M3",
        "What is the reinvestment composition (organic CapEx / WC / acquisitions / distributions "
        "separate) and runway evidence label (ample|limited|unclear|not_applicable)?",
    ),
    (
        "S6-M4",
        "What CapEx productivity and WC-mechanism evidence exists (notes, not scores)? "
        "Maint CapEx only if disclosed — else UNKNOWN.",
    ),
    (
        "S6-M5",
        "Which FP-R patterns are material or watchable (flags, not auto-fails)?",
    ),
    (
        "S6-M6",
        "RC1–RC8 evidence labels + WHY (Benchmark ≠ hard gate; Method E).",
    ),
    (
        "S6-M7",
        "Does Stage 6 evidence support, strain, or falsify the Stage 1 capital-destination claim?",
    ),
    (
        "S6-M8",
        "Process outcome (PROCEED / CONDITIONAL / REVIEW_REQUIRED / TOO_HARD) + Stage 7 factual "
        "handoff flags (S6_H7_*). Default: NON-TERMINATING (terminates_later_stages=False).",
    ),
]

SHOULD_QUESTIONS = [
    (
        "S6-S1",
        "Financing-side IC reconciliation gap — escalate SOURCE_CONFLICT when material unexplained.",
    ),
    (
        "S6-S2",
        "Lease / ASC 842 adoption splice honesty for incremental windows.",
    ),
    (
        "S6-S3",
        "Acquisition deal-lag / PPA narrative (A7 dual spine) — not M&A moral grade.",
    ),
    (
        "S6-S4",
        "Distributions / buybacks as separate capital destination (not reinvestment composition).",
    ),
    (
        "S6-S5",
        "Investment-phase vs persistent value-destructive reinvestment ambiguity (D10 path).",
    ),
]

STAGE6_OUTCOMES = frozenset({"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"})

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

RC_DIMENSIONS = [
    ("RC1", "Current ROIC reality (definition-honest, dual when needed)"),
    ("RC2", "Incremental ROIC meaning class"),
    ("RC3", "Reinvestment runway"),
    ("RC4", "Organic vs acquisition capital honesty"),
    ("RC5", "CapEx productivity evidence"),
    ("RC6", "WC / capital-intensity mechanism"),
    ("RC7", "Accounting-distortion honesty"),
    ("RC8", "Thesis coherence on capital destination"),
]

FALSE_POSITIVE_CATALOGUE = [
    ("FP-R1", "Peak-cycle ROIC sold as franchise"),
    ("FP-R2", "CapEx holiday inflating ROIC"),
    ("FP-R3", "Dual-view conflict hidden (ex-GW only headline)"),
    ("FP-R4", "Lease / accounting break distortion"),
    ("FP-R5", "Excess-cash policy distortion"),
    ("FP-R6", "Impairment-improved ROIC"),
    ("FP-R7", "ΔIC≈0 incremental explosion (capital-light pathology)"),
    ("FP-R8", "SBC / NOPAT theatre"),
    ("FP-R9", "Negative WC slogan as quality"),
    ("FP-R10", "PPA / acquisition stub optics"),
    ("FP-R11", "High-ROIC melting ice cube (limited runway)"),
    ("FP-R12", "Investment-phase misread as permanent destruction"),
    ("FP-R13", "Pension / restructuring noise"),
    ("FP-R14", "ROE / leverage confused with ROIC"),
]

RUNWAY_LABELS = frozenset({"ample", "limited", "unclear", "not_applicable"})

INCREMENTAL_MEANING_CLASSES = frozenset(
    {
        "structurally_informative",
        "noisy",
        "distorted",
        "not_meaningful",
        "unknown",
    }
)

STAGE7_HANDOFF_FLAGS = frozenset(
    {
        "S6_H7_ACQ_RETURN_OPACITY",
        "S6_H7_DUAL_VIEW_CONFLICT",
        "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST",
        "S6_H7_CAPEX_PRODUCTIVITY_OPAQUE",
        "S6_H7_DISCLOSURE_QUALITY_CAPITAL",
        "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION",
    }
)

# Capital-efficiency drivers by A1–A11 (Plan §13) — ~1–3 slots
CAPITAL_DRIVERS_BY_ARCHETYPE = {
    "A1": [
        ("tangible_franchise_roic", "Tangible franchise ROIC"),
        ("runway_vs_distribute", "Runway vs distribute logic"),
    ],
    "A2": [
        ("capital_light_optics", "Capital-light ROIC optics"),
        ("sbc_honesty", "SBC / NOPAT honesty"),
        ("ma_deployment", "M&A deployment outlet"),
    ],
    "A3": [
        ("capital_light_outlets", "Capital-light outlets"),
        ("delta_ic_guard", "ΔIC≈0 incremental guard"),
        ("dual_if_deals", "Dual view if acquisitive deals"),
    ],
    "A4": [
        ("fab_capex_lag", "Fab CapEx lag / gestation"),
        ("cycle_peak_roic", "Cycle peak ROIC honesty (FP-R1)"),
    ],
    "A5": [
        ("sustaining_vs_growth_capex", "Sustaining vs growth CapEx"),
        ("lease_capital", "Lease capital in IC"),
    ],
    "A6": [
        ("store_warehouse_capex", "Store / warehouse CapEx"),
        ("wc_mechanism", "WC mechanism"),
        ("ses_interplay", "SES / thin-OP interplay"),
    ],
    "A7": [
        ("dual_spine_mandatory", "Mandatory dual ROIC spine"),
        ("acq_inclusive_honesty", "Acquisition-inclusive honesty"),
        ("deal_lag_ppa", "Deal lag / PPA narrative"),
    ],
    "A8": [
        ("peak_roic_honesty", "Peak ROIC honesty"),
        ("sustaining_replacement_capex", "Sustaining / replacement CapEx"),
    ],
    "A9": [
        ("fleet_capex_roic", "Fleet CapEx ROIC"),
        ("cycle_timing", "Cycle timing"),
    ],
    "A10": [
        ("segment_intensity", "Segment capital intensity"),
        ("hybrid_capex", "Hybrid CapEx mix"),
    ],
    "A11": [
        ("explicit_why", "Explicit WHY required"),
        ("human_bias_if_unclear", "Human bias if capital model unclear"),
    ],
}

from fa.stage4.questions import PRIMARY_ARCHETYPES  # noqa: E402 — reuse locked A1–A11

__all__ = [
    "MUST_QUESTIONS",
    "SHOULD_QUESTIONS",
    "STAGE6_OUTCOMES",
    "BENCHMARK_LABELS",
    "RC_DIMENSIONS",
    "FALSE_POSITIVE_CATALOGUE",
    "RUNWAY_LABELS",
    "INCREMENTAL_MEANING_CLASSES",
    "STAGE7_HANDOFF_FLAGS",
    "CAPITAL_DRIVERS_BY_ARCHETYPE",
    "PRIMARY_ARCHETYPES",
]
