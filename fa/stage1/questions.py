"""Gate 0/1/2 question IDs and text — from OWNERSHIP_PHILOSOPHY_RESEARCH_v1 / STAGE_1_GATES_v1.

Do not invent new questions here.
"""
from __future__ import annotations

# Gate 0 — unit of analysis
GATE0_MUST = [
    (
        "G0-M1",
        "What is the unit of analysis? (operating | financial_institution | commodity)",
    ),
]

# Gate 1 MUST
GATE1_MUST = [
    ("G1-M1", "In plain language (TR or EN), what does the company sell, and to whom?"),
    ("G1-M2", "Why does the customer pay — what job is being done?"),
    ("G1-M3", "Where does revenue primarily come from (product/segment/geography mix at a coarse level)?"),
    ("G1-M4", "What is the economic engine in one sentence (how the firm turns inputs into cash over time)?"),
    ("G1-M5", "What are the 2–4 variables that most determine success or failure in this industry?"),
    ("G1-M6", "Who are the important competitors or substitutes, at least at category level?"),
    ("G1-M7", "Can I name what would make me update or abandon the thesis (falsifiers)?"),
    ("G1-M8", "Am I willing and able to keep following those variables over years within my time budget?"),
]

# Gate 1 SHOULD (warnings only)
GATE1_SHOULD = [
    ("G1-S1", "What drives growth (volume, price, mix, new products, geography)?"),
    ("G1-S2", "What drives the major cost blocks?"),
    ("G1-S3", "How does the industry's competitive structure roughly work (fragmented, oligopoly, regulated, commodity)?"),
    ("G1-S4", "What accounting or industry quirks could mislead a casual reader?"),
    ("G1-S5", "Do I need specialized domain knowledge I lack (e.g. biotech trial design, bank credit cycles)?"),
]

# Gate 1 LEARNABLE (never blockers)
GATE1_LEARNABLE = [
    ("G1-L1", "Detailed org chart / every SKU"),
    ("G1-L2", "Perfect competitor market-share tables"),
    ("G1-L3", "Ability to forecast next quarter's EPS"),
    ("G1-L4", "Meeting management (nice-to-have)"),
]

# Gate 2 MUST
GATE2_MUST = [
    (
        "G2-M1",
        "What valuable job does this business do for customers that alternatives do worse or costlier?",
    ),
    (
        "G2-M2",
        "What is the hypothesized durable advantage (if any): switching costs, network, brand, "
        "scale/cost, unique asset, regulation, process, data, etc.?",
    ),
    ("G2-M3", "Why might that advantage persist for 5–15 years?"),
    (
        "G2-M4",
        "What is the growth runway (what expands: users, usage, geography, products)? How long is \"long\"?",
    ),
    (
        "G2-M5",
        "What does the firm do with incremental capital — reinvest at high returns, bolt-on M&A, "
        "buybacks, dividends, empire-build?",
    ),
    (
        "G2-M6",
        "Is the model capital-light or capital-intensive, and is that consistent with the story "
        "(including Sleep-style \"low margin by design\")?",
    ),
    (
        "G2-M7",
        "How could the thesis fail (competition, disruption, regulation, customer power, tech change, "
        "commodity mean-reversion, key-person)?",
    ),
    (
        "G2-M8",
        "Separately: what would financial statements need to show over time to validate the story? "
        "(bridge to later stages — not thresholds yet)",
    ),
]

# Gate 2 SHOULD
GATE2_SHOULD = [
    ("G2-S1", "Management incentives aligned with per-share intrinsic value?"),
    ("G2-S2", "Industry structure helpful or hostile?"),
    ("G2-S3", "Is \"growth\" dilutive (Fisher point on equity issuance)?"),
    ("G2-S4", "Are we mistaking a cyclical/commodity upswing for a franchise?"),
]

# Ban list for thesis one-sentence (research §6) — lowercase match substrings
THESIS_ONE_SENTENCE_BAN_LIST = [
    "growing revenues",
    "good margins",
    "high roic",
    "cheap stock",
    "hot sector",
    "capex means future",
]

GATE0_ALLOWED = frozenset({"operating", "financial_institution", "commodity"})

# Critical Gate 1 MUST that empty/handwave → TOO_HARD
G1_TOO_HARD_CORE = frozenset({"G1-M1", "G1-M2", "G1-M3", "G1-M4"})
