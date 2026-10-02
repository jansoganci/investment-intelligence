"""Stage 5 question spine — FROZEN from STAGE_5_BUSINESS_ECONOMICS_PLAN_v1.md §4 / §0.

Do not invent new questions or BE9 here. No numeric GM/OP/IM bands.
"""
from __future__ import annotations

# MUST — S5-M1 … S5-M8 (SPEC_LOCKED)
MUST_QUESTIONS = [
    (
        "S5-M1",
        "Over a multi-period window (prefer ~5 FY + ~8Q), what is the margin structure "
        "(gross, operating, and any disclosed intermediate), with definition honesty?",
    ),
    (
        "S5-M2",
        "Can margin changes be decomposed into drivers (price / mix / volume absorption / "
        "inputs / labor / distribution / scale-shared giveback / accounting / other) with "
        "FACT vs COMPANY_EXPLANATION vs MODEL_INFERENCE?",
    ),
    (
        "S5-M3",
        "What is the best evidence for pricing power and/or cost advantage — or for their absence?",
    ),
    (
        "S5-M4",
        "What do incremental operating margins / operating-leverage evidence say (descriptive) — "
        "investment phase, durable leverage, mix, or deterioration? (≠ Stage 6 ROIC)",
    ),
    (
        "S5-M5",
        "How durable are the economics, and what is durability confidence "
        "(HIGH/MEDIUM/LOW/UNKNOWN)? Name falsifiers.",
    ),
    (
        "S5-M6",
        "Which false-positive patterns are material or plausibly material?",
    ),
    (
        "S5-M7",
        "Do observed economics support, strain, or falsify the Stage 1 ownership thesis?",
    ),
    (
        "S5-M8",
        "Process outcome (PROCEED / CONDITIONAL / REVIEW_REQUIRED / TOO_HARD) and which "
        "economics concerns must carry (esp. into Stage 6)? Default: Stage 5 does not alone "
        "mechanically terminate later stages.",
    ),
]

# SHOULD — S5-S1 … S5-S6 (SPEC_LOCKED)
SHOULD_QUESTIONS = [
    (
        "S5-S1",
        "Segment / geo / product margin splits when disclosed — does the blend hide a weak engine?",
    ),
    (
        "S5-S2",
        "Disclosed unit economics / cohort / contribution clues (hand capital bridge to Stage 6).",
    ),
    (
        "S5-S3",
        "SBC-aware / non-GAAP honesty: do “adjusted” margins change the story?",
    ),
    (
        "S5-S4",
        "Input / commodity / labor / FX sensitivity vs pass-through ability.",
    ),
    (
        "S5-S5",
        "SES / intentional thin-margin test: is low OP designed customer surplus + scale, "
        "or structural weakness?",
    ),
    (
        "S5-S6",
        "Competitive / category margin context (secondary; never peer-percentile primary).",
    ),
]

STAGE5_OUTCOMES = frozenset({"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"})

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

# Closed context-tag set — Plan §0.C / D14 (NOT process outcomes; NOT countable scores)
CONTEXT_TAGS = frozenset(
    {
        "SCALE_ECONOMIES_SHARED_OK",
        "MATURE_FRANCHISE_ECONOMICS_OK",
        "CYCLE_PEAK_MARGIN_RISK",
        "CHALLENGE_ARCHETYPE",
        "ACCOUNTING_MARGIN_DISTORTION",
        "HIGH_MARGIN_QUALITY_RISK",
    }
)

PRICING_POWER_POSTURES = frozenset(
    {"STRONG", "MODERATE", "WEAK", "MIXED", "UNKNOWN", "NOT_APPLICABLE"}
)

INCREMENTAL_OM_CLASSES = frozenset(
    {"reported", "structurally_informative", "distorted", "unknown"}
)

# BE1–BE8 only — NO BE9 ROIC
BE_DIMENSIONS = [
    ("BE1", "Margin structure reality (multi-period GM/OP + definition honesty)", "universal"),
    ("BE2", "Driver decomposition honesty", "universal"),
    ("BE3", "Pricing-power evidence", "near_universal"),
    ("BE4", "Cost advantage / scale / operating leverage (P&L)", "near_universal"),
    ("BE5", "Incremental OM / leverage (descriptive)", "conditional"),
    ("BE6", "Durability of economics + confidence + falsifiers", "universal"),
    ("BE7", "False-positive load (FP catalogue; no FP score average)", "universal"),
    ("BE8", "Thesis / economics coherence vs Stage 1", "universal"),
]

PRIMARY_ARCHETYPES = {
    "A1": "Mature branded consumer",
    "A2": "SaaS / recurring software",
    "A3": "Network / payments platform",
    "A4": "Semiconductor",
    "A5": "Industrial / capital-intensive manufacturer",
    "A6": "Retailer",
    "A7": "Acquisitive compounder",
    "A8": "Cyclical / commodity-sensitive OpCo",
    "A9": "Travel / capacity-based cyclical",
    "A10": "Hybrid manufacturer / technology platform",
    "A11": "Other / mixed",
}

# Economics driver slots by archetype (Plan §3.3) — pick ~1–3
ECONOMICS_DRIVERS_BY_ARCHETYPE: dict[str, list[tuple[str, str]]] = {
    "A1": [
        ("brand_pricing_power", "Brand pricing power"),
        ("controllable_opex_unit", "Controllable opex per unit"),
        ("mix_premium_vs_value", "Mix premium vs value"),
    ],
    "A2": [
        ("gm_durability", "GM durability"),
        ("sm_rd_intensity_path", "S&M/R&D intensity path"),
        ("sbc_aware_op", "SBC-aware OP"),
    ],
    "A3": [
        ("take_rate_vs_volume", "Take-rate vs volume"),
        ("network_opex_leverage", "Network opex leverage"),
    ],
    "A4": [
        ("product_mix_margin", "Product-mix margin"),
        ("cycle_adjusted_posture", "Cycle-adjusted posture"),
    ],
    "A5": [
        ("absorption_backlog", "Absorption / backlog pricing"),
        ("fixed_cost_leverage", "Fixed-cost leverage"),
    ],
    "A6": [
        ("gross_vs_sga", "Gross vs SG&A"),
        ("ses_vs_specialty", "SES vs specialty posture"),
    ],
    "A7": [
        ("organic_vs_acquired_margin", "Organic vs acquired margin"),
        ("ppa_integration_drag", "PPA / integration drag"),
    ],
    "A8": [
        ("cash_cost_through_cycle", "Cash-cost / margin through cycle"),
        ("windfall_honesty", "Windfall honesty"),
    ],
    "A9": [
        ("yield_load", "Yield / load / occupancy"),
        ("cost_per_capacity", "Cost per capacity unit"),
    ],
    "A10": [
        ("segment_economics_honesty", "Segment economics honesty"),
    ],
    "A11": [
        ("explicit_custom_drivers", "Explicit custom drivers + WHY"),
    ],
}

# Optional one model-specific dashboard slot (Plan §0.J) — not all forever
MODEL_SLOT_BY_ARCHETYPE: dict[str, str] = {
    "A1": "mix_or_brand_pricing_slot",
    "A2": "contribution_or_sbc_aware_slot",
    "A3": "take_rate",
    "A4": "cycle_adjusted_margin_slot",
    "A5": "absorption_slot",
    "A6": "gross_vs_sga_slot",
    "A7": "organic_vs_acquired_margin_slot",
    "A8": "through_cycle_cash_cost_slot",
    "A9": "yield_load",
    "A10": "segment_margins",
    "A11": "explicit_or_not_applicable",
}

FALSE_POSITIVE_CATALOGUE = [
    ("FP1", "Cyclical / commodity peak margins as franchise"),
    ("FP2", "CapEx holiday / deferred opex inflating OP"),
    ("FP3", "Mix theatre (high-margin stub / one-time mix)"),
    ("FP4", "Acquisition / PPA optics (amort, stub margins)"),
    ("FP5", "SBC-blind or heavy non-GAAP “adjusted” margins"),
    ("FP6", "Promo / discounting bought share → temporary GM"),
    ("FP7", "Cost-cut OP expansion with demand decay"),
    ("FP8", "Low margin auto-read as bad (misses SES)"),
    ("FP9", "High margin auto-read as moat (misses windfall/monopoly rent at risk)"),
    ("FP10", "Accounting reclass / calendar / one-offs"),
    ("FP11", "Platform blended OP hides weak segment"),
    ("FP12", "Investment-phase negative incremental OM misread as permanent"),
]
