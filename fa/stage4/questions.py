"""Stage 4 question spine — FROZEN from STAGE_4_GROWTH_QUALITY_PLAN_v1.md §3.

Do not invent new questions here.
"""
from __future__ import annotations

# MUST — S4-M1 … S4-M8 (SPEC_LOCKED)
MUST_QUESTIONS = [
    (
        "S4-M1",
        "Over a multi-period window (prefer architecture default ~5 FY + ~8Q when available), "
        "what did revenue (and, where disclosed, units/volume proxies) do — with explicit "
        "base-effect honesty?",
    ),
    (
        "S4-M2",
        "Can growth be decomposed into organic vs acquired (and residual UNATTRIBUTED/UNKNOWN)? "
        "What FACT vs COMPANY_EXPLANATION vs MODEL_INFERENCE supports the split?",
    ),
    (
        "S4-M3",
        "Where disclosure allows, what roles did volume / price / mix / FX / geo / product / "
        "capacity / share / industry / accounting-other play? (Complete attribution not required; "
        "honesty is.)",
    ),
    (
        "S4-M4",
        "Is growth directionally economically valuable for owners (Buffett: growth can be negative) "
        "— or does evidence suggest capital-bought, dilutive, or value-destructive growth theatre — "
        "without completing Stage 6 ROIC math?",
    ),
    (
        "S4-M5",
        "What is the runway claim now (users, usage, geo, product, capacity, share, category) "
        "and what is confidence (HIGH/MEDIUM/LOW/UNKNOWN)? No fake-precision forecast.",
    ),
    (
        "S4-M6",
        "Does observed growth support, strain, or falsify the Stage 1 / Gate 2 ownership thesis "
        "(esp. G2-M4)?",
    ),
    (
        "S4-M7",
        "Which false-positive patterns are material or plausibly material (cyclical rebound, "
        "FX/inflation nominal, acquisition optics, dilution, accounting, cannibalization, "
        "vanity SaaS metrics, etc.)?",
    ),
    (
        "S4-M8",
        "Given evidence quality, what is the Stage 4 process outcome "
        "(PROCEED / CONDITIONAL / REVIEW_REQUIRED / TOO_HARD), and which growth-quality concerns "
        "must carry into the final fundamental assessment? "
        "(Stage 4 does not alone mechanically terminate later stages.)",
    ),
]

# SHOULD — S4-S1 … S4-S6 (SPEC_LOCKED)
SHOULD_QUESTIONS = [
    ("S4-S1", "Company growth vs category/industry growth — share gains or rising tide?"),
    (
        "S4-S2",
        "Cannibalization / geo-product expansion: is “new” growth net-additive after core impact?",
    ),
    (
        "S4-S3",
        "Dilution path: share count, SBC, issuance vs NI and revenue growth (Fisher) — "
        "deeper than M4 posture.",
    ),
    (
        "S4-S4",
        "Mature compounder exception: is low headline growth still thesis-consistent "
        "(pricing/mix/share + durable demand)?",
    ),
    (
        "S4-S5",
        "Unit-economics / cohort clues that growth is valuable (hand deep work to Stage 5).",
    ),
    (
        "S4-S6",
        "Backlog / RPO / bookings / book-to-bill quality where model-relevant "
        "(industrial, semi, SaaS) — disclosure-dependent.",
    ),
]

STAGE4_OUTCOMES = frozenset({"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"})

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

CONTEXT_TAGS = frozenset(
    {"MATURE_FRANCHISE_OK", "CHALLENGE_ARCHETYPE", "HIGH_GROWTH_QUALITY_RISK"}
)

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

FALSE_POSITIVE_CATALOGUE = [
    ("FP1", "Acquired growth sold as organic"),
    ("FP2", "Cyclical rebound as structural growth"),
    ("FP3", "FX-driven reported growth"),
    ("FP4", "Inflation-only price growth"),
    ("FP5", "Easy base-effect comps"),
    ("FP6", "Channel stuffing / pull-forward"),
    ("FP7", "EPS up via share shrink / accounting while NI flat"),
    ("FP8", "Capital-bought top-line (M&A or low-return CapEx)"),
    ("FP9", "SaaS logo growth with poor retention"),
    ("FP10", "Semi/industrial boom as franchise"),
    ("FP11", "Retail footage binge"),
    ("FP12", "Ignoring cannibalization"),
    ("FP13", "“Low growth = fail” for mature compounders"),
    ("FP14", "Organic but value-destructive volume"),
]
