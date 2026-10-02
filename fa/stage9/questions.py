"""Stage 9 question spine — FROZEN from STAGE_9_EXTERNAL_RISK_PLAN_v1.md §0.

No scores / colors / BUY-SELL / numeric risk gates / averaged external-risk score.
No industry warehouse. No final FA synthesis. No Stage 5 pricing-power redo /
no Stage 1 thesis restatement. ER8 = 3–7 falsifiers — NOT giant risk register.
"""
from __future__ import annotations

MUST_QUESTIONS = [
    (
        "S9-M1",
        "What industry structure governs value capture (Porter-style semantic map; "
        "who captures surplus; no Porter score)?",
    ),
    (
        "S9-M2",
        "Does the Gate 2 / S1 / S5 moat hypothesis still hold under external attack/"
        "erosion mechanisms only (ER2 locked — no S5 pricing-power redo / no S1 thesis restatement)?",
    ),
    (
        "S9-M3",
        "Is there a real disruption mechanism + exposure + evidence (not headline theatre)?",
    ),
    (
        "S9-M4",
        "Where is concentration material (customer/supplier/geo/product/distribution) — "
        "descriptive labels only; no auto-fail?",
    ),
    (
        "S9-M5",
        "Is regulation a barrier, a sword, or both — with primary-source evidence labels?",
    ),
    (
        "S9-M6",
        "What geopolitical footprint + mechanism matters (UNKNOWN when opaque; no country-risk score)?",
    ),
    (
        "S9-M7",
        "What macro/cycle exposures exist (prepare ≠ predict; A8/A9 mid-cycle honesty; soft-link S8_H9_*)?",
    ),
    (
        "S9-M8",
        "What are the 3–7 observable thesis breakers + monitoring variables (NOT a giant risk register)?",
    ),
    (
        "S9-M9",
        "Any material conflict with Stages 1–8 evidence (surface + explain; no silent override)?",
    ),
    (
        "S9-M10",
        "Process outcome (PROCEED/CONDITIONAL/REVIEW_REQUIRED/TOO_HARD) + FP-E + S9_HFA_* carries. "
        "NON-TERMINATING. Never BUY/SELL/colors. No final FA synthesis.",
    ),
]

SHOULD_QUESTIONS = [
    (
        "S9-S1",
        "Multi-industry / secondary-engine flag when primary economic engine is not sole?",
    ),
    (
        "S9-S2",
        "Capital-cycle / supply-response notes folded into ER1+ER7 (ER9 merged)?",
    ),
    (
        "S9-S3",
        "Windfall ≠ franchise honesty when A8 / peak-cycle optics present?",
    ),
    (
        "S9-S4",
        "Optional disclosed concentration/geo structured fields when present (else semantic)?",
    ),
    (
        "S9-S5",
        "Forward S8_H9_* carries preserved for final FA notes (no Stage 8 redo)?",
    ),
]

STAGE9_OUTCOMES = frozenset({"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"})

ER_LENSES = [
    ("ER1", "Industry Structure Map"),
    ("ER2", "Moat Durability Stress"),
    ("ER3", "Disruption Mechanism"),
    ("ER4", "Concentration Map"),
    ("ER5", "Regulatory / Policy Envelope"),
    ("ER6", "Geopolitical Exposure"),
    ("ER7", "Macro / Cycle Context"),
    ("ER8", "Thesis Breakers & Monitoring"),
]

ER_BENCHMARK_DIMENSIONS = list(ER_LENSES)  # Method E labels+WHY; ≠ hard gate

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

EVIDENCE_LABELS = frozenset({"FACT", "GUIDANCE", "CLAIM", "INFERENCE", "UNKNOWN"})

CONCENTRATION_LABELS = frozenset({"low", "moderate", "high", "extreme", "unknown"})

CYCLE_POSITION_CLASSES = frozenset({"early", "mid", "late", "unknown"})

REGULATORY_POSTURES = frozenset({"barrier", "sword", "both", "unknown"})

# Locked S9_HFA_* carries (Plan §0.J) — trim-ready
S9_HFA_CARRIES = frozenset(
    {
        "S9_HFA_THESIS_BREAKER_ACTIVE",
        "S9_HFA_MOAT_DURABILITY_STRESSED",
        "S9_HFA_REGULATORY_MATERIAL",
        "S9_HFA_GEO_MATERIAL",
        "S9_HFA_CYCLE_PEAK_RISK",
        "S9_HFA_CONCENTRATION_EXTREME",
        "S9_HFA_DISRUPTION_MECHANISM",
    }
)

# Forward from Stage 8 (consume; do not recompute valuation)
S8_H9_FORWARDABLE = frozenset(
    {
        "S8_H9_CYCLE_SENSITIVE_VALUATION",
        "S8_H9_EXPECTATIONS_DEMANDING",
    }
)

# FP-E1–E12 catalogue (Research §15) — flags not auto-fails
FALSE_POSITIVE_CATALOGUE = [
    ("FP-E1", "Scary headline = risk", "high"),
    ("FP-E2", "High margins = durable moat", "high"),
    ("FP-E3", "AI will disrupt X without economics", "high"),
    ("FP-E4", "Regulated industry = safe moat", "high"),
    ("FP-E5", "Low beta / defensive sector = low external risk", "medium"),
    ("FP-E6", "Diversified GICS = low concentration", "medium"),
    ("FP-E7", "Peak-cycle earnings = franchise quality", "high"),
    ("FP-E8", "Many competitors named in 10-K = intense rivalry always", "medium"),
    ("FP-E9", "ESG/vendor risk grade = Stage 9 conclusion", "high"),
    ("FP-E10", "Geopolitical fear without footprint", "high"),
    ("FP-E11", "Stage 8 cheapness cures industry risk", "high"),
    ("FP-E12", "No news = no external risk", "medium"),
]

# Soft emphases by archetype — notes only, not grades
EXTERNAL_RISK_EMPHASIS_BY_ARCHETYPE = {
    "A1": ["franchise_erosion", "category_regulation", "substitute_mechanisms"],
    "A2": ["platform_rivalry", "attention_competition", "ai_substitute_honesty"],
    "A3": ["network_structure", "antitrust_sword_shield", "fintech_disruption_honesty"],
    "A4": ["semi_cycle", "customer_concentration", "export_controls_geo"],
    "A5": ["buyer_power", "supply_chain_concentration"],
    "A6": ["rate_regulation", "policy_envelope", "barrier_vs_sword"],
    "A7": ["roll_up_industry_dynamics", "consolidation_neq_moat"],
    "A8": ["capital_cycle", "windfall_neq_franchise", "china_geo_demand"],
    "A9": ["volume_cycle", "shock_exposure", "fuel_macro"],
    "A10": ["uncertainty_first", "too_hard_bias"],
    "A11": ["explicit_why_or_too_hard", "structure_unclear"],
}

PRIMARY_ARCHETYPES = {
    "A1": "Capital-light compounder",
    "A2": "SBC / dilution-sensitive growth",
    "A3": "Mature cash cow / network",
    "A4": "Heavy CapEx / project",
    "A5": "Working-capital intensive",
    "A6": "Regulated / utility-like",
    "A7": "Acquisitive compounder",
    "A8": "Commodity / price-taker cyclical",
    "A9": "Volume / capacity cyclical",
    "A10": "Turnaround / restructuring",
    "A11": "Hard-to-classify / special situation",
}

__all__ = [
    "MUST_QUESTIONS",
    "SHOULD_QUESTIONS",
    "STAGE9_OUTCOMES",
    "ER_LENSES",
    "ER_BENCHMARK_DIMENSIONS",
    "BENCHMARK_LABELS",
    "EVIDENCE_LABELS",
    "CONCENTRATION_LABELS",
    "CYCLE_POSITION_CLASSES",
    "REGULATORY_POSTURES",
    "S9_HFA_CARRIES",
    "S8_H9_FORWARDABLE",
    "FALSE_POSITIVE_CATALOGUE",
    "EXTERNAL_RISK_EMPHASIS_BY_ARCHETYPE",
    "PRIMARY_ARCHETYPES",
]
