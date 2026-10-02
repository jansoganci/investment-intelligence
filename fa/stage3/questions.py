"""Stage 3 question spine — FROZEN from STAGE_3_CASH_GENERATION_PLAN_v1.md §0.2 / §1.

Do not invent new questions here.
"""
from __future__ import annotations

# MUST — S3-M1 … S3-M8 (SPEC_LOCKED)
MUST_QUESTIONS = [
    (
        "S3-M1",
        "Over a multi-period window (annual + relevant YoY quarters), do reported earnings "
        "convert into operating cash flow — or is there a persistent, unexplained earnings–cash gap?",
    ),
    (
        "S3-M2",
        "After CapEx (with lineage honesty), what does calculated FCF (OCF − CapEx) show — "
        "and is CapEx classification clear enough to trust the figure?",
    ),
    (
        "S3-M3",
        "What is our owner-earnings posture: can we support a note-backed maintenance view, "
        "or is maintenance CapEx UNKNOWN — and therefore must we refuse false precision?",
    ),
    (
        "S3-M4",
        "Is working capital (receivables, inventory, payables, deferred revenue where relevant) "
        "a converter, a growth sponge, or a trap relative to the sales/earnings narrative?",
    ),
    (
        "S3-M5",
        "Are material cash-flow distortions present or plausibly material "
        "(factoring, supplier finance, acquisitions, asset sales, capitalized costs, "
        "serial restructuring, SBC optics)?",
    ),
    (
        "S3-M6",
        "Is observed cash generation consistent with the Gate 1–2 economic engine "
        "(or does cash reality falsify / strain the thesis)?",
    ),
    (
        "S3-M7",
        "Is cash generation sustainable enough that we are not mistaking a CapEx holiday, "
        "cyclical peak, WC release, or one-time inflow for franchise cash power?",
    ),
    (
        "S3-M8",
        "Given evidence quality, what is the Stage 3 process outcome "
        "(PROCEED / CONDITIONAL / REVIEW_REQUIRED / TOO_HARD), and what cash-quality concerns "
        "must carry into the final fundamental assessment? "
        "(Stage 3 does not alone mechanically terminate later stages.)",
    ),
]

# SHOULD — S3-S1 … S3-S5 (SPEC_LOCKED)
SHOULD_QUESTIONS = [
    ("S3-S1", "Cash taxes paid vs book tax expense — timing story material?"),
    ("S3-S2", "Pension / OPEB cash contributions vs P&L expense material?"),
    (
        "S3-S3",
        "Deferred revenue / customer advances: quality of prepaid demand vs future service burden?",
    ),
    ("S3-S4", "Seasonal path: is the OCF pattern normal for this model, or window-shopping?"),
    (
        "S3-S5",
        "Controllable near-term cash levers (defer discretionary CapEx, cut buybacks/dividends) — "
        "do they buy time without killing the thesis? (Bridge to Stage 2 levers; not valuation.)",
    ),
]

STAGE3_OUTCOMES = frozenset({"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"})
