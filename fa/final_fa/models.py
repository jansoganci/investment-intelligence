"""Final FA Synthesis models — Plan §0.L schema (LOCKED)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

FinalState = Literal[
    "INCOMPLETE",
    "TOO_HARD",
    "STOP_NO_THESIS",
    "REVIEW_REQUIRED",
    "RED",
    "ORANGE",
    "GREEN",
]

SeverityLevel = Literal["S0", "S1", "S2", "S3", "S4"]

OUTSIDE_COLOR = frozenset(
    {"INCOMPLETE", "TOO_HARD", "STOP_NO_THESIS", "REVIEW_REQUIRED"}
)
INSIDE_COLOR = frozenset({"RED", "ORANGE", "GREEN"})

# Completeness classes (Plan §0.E)
SPINE_STAGE = 1
CORE_REQUIRED_STAGES = (2, 3, 6, 8, 9)
SOFT_IF_MISSING_STAGES = (4, 5, 7)

S6_H7_LOCKED = frozenset(
    {
        "S6_H7_ACQ_RETURN_OPACITY",
        "S6_H7_DUAL_VIEW_CONFLICT",
        "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST",
        "S6_H7_CAPEX_PRODUCTIVITY_OPAQUE",
        "S6_H7_DISCLOSURE_QUALITY_CAPITAL",
        "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION",
        # additional factual flags already emitted by Stage 6/8
        "S6_H7_ROIIC_DETERIORATION",
        "S6_H7_RUNWAY_LIMITED_DISTRIBUTE",
        "S6_H7_IC_BRIDGE_OPAQUE",
        "S6_H7_INCREMENTAL_NOT_MEANINGFUL",
    }
)
S7_H8_LOCKED = frozenset(
    {
        "S7_H8_DILUTION_MATERIAL",
        "S7_H8_BUYBACK_PRICE_DISCIPLINE_OPAQUE",
        "S7_H8_ALLOCATION_UNCERTAINTY_FOR_VALUATION",
    }
)
S8_H9_LOCKED = frozenset(
    {
        "S8_H9_CYCLE_SENSITIVE_VALUATION",
        "S8_H9_EXPECTATIONS_DEMANDING",
    }
)
S9_HFA_LOCKED = frozenset(
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

MAX_CONFLICTS = 5
MAX_HUMAN_QUEUE = 5
MAX_WHY = 5


@dataclass
class ProvenancedBullet:
    text: str
    provenance: list[str] = field(default_factory=list)
    evidence_label: str | None = None  # FACT|GUIDANCE|CLAIM|INFERENCE|UNKNOWN
    severity_level: SeverityLevel | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d.get("severity_level") is None:
            d.pop("severity_level", None)
        if d.get("evidence_label") is None:
            d.pop("evidence_label", None)
        return d


@dataclass
class ConflictRecord:
    conflict_id: str
    family: int
    summary: str
    resolution_action: str
    evidence_ptrs: list[str] = field(default_factory=list)
    human_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HumanItem:
    id: str
    why_human: str
    evidence_ptrs: list[str] = field(default_factory=list)
    decision_options: list[str] = field(default_factory=list)
    blocks_color: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BreakerRef:
    breaker_id: str
    source: str = "stage9_er8"
    active_fact: bool = False
    mechanism: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FinalThesisBlock:
    one_liner: str | None = None
    economic_engine: str | None = None
    durable_advantage_hypothesis: str | None = None
    capital_destination_posture: str | None = None
    key_supports: list[str] = field(default_factory=list)
    key_challenges: list[str] = field(default_factory=list)
    falsifiers: list[str] = field(default_factory=list)
    monitors: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProvenanceBlock:
    final_fa_version: str | None = None
    stage_versions: dict[str, str | None] = field(default_factory=dict)
    stage_paths: dict[str, str | None] = field(default_factory=dict)
    carries_frozen_at: str | None = None
    human_decision_log: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FinalFaSynthesis:
    """Plan §0.L FinalFaSynthesis artifact."""

    ticker: str
    as_of: str
    final_state: FinalState
    technical_eligible: bool
    why_bullets: list[str]
    supports: list[ProvenancedBullet]
    challenges: list[ProvenancedBullet]
    unresolved: list[str]
    conflicts: list[ConflictRecord]
    human_review_queue: list[HumanItem]
    thesis: FinalThesisBlock
    carries_consumed: dict[str, list[str]]
    stage_outcomes: dict[str, str]
    monitors: list[str]
    falsifiers: list[BreakerRef]
    provenance: ProvenanceBlock
    acknowledgements: dict[str, bool] = field(
        default_factory=lambda: {
            "no_buy_sell": True,
            "no_weights": True,
            "no_watchlist_rank": True,
            "green_ne_buy": True,
        }
    )
    soft_missing_chips: list[str] = field(default_factory=list)
    orange_ceiling: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "as_of": self.as_of,
            "final_state": self.final_state,
            "technical_eligible": self.technical_eligible,
            "why_bullets": list(self.why_bullets),
            "supports": [s.to_dict() for s in self.supports],
            "challenges": [c.to_dict() for c in self.challenges],
            "unresolved": list(self.unresolved),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "human_review_queue": [h.to_dict() for h in self.human_review_queue],
            "thesis": self.thesis.to_dict(),
            "carries_consumed": {
                k: list(v) for k, v in self.carries_consumed.items()
            },
            "stage_outcomes": dict(self.stage_outcomes),
            "monitors": list(self.monitors),
            "falsifiers": [f.to_dict() for f in self.falsifiers],
            "provenance": self.provenance.to_dict(),
            "acknowledgements": dict(self.acknowledgements),
            "soft_missing_chips": list(self.soft_missing_chips),
            "orange_ceiling": self.orange_ceiling,
        }
