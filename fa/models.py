"""Dataclasses / TypedDicts for PeriodVersion, lineage, FA list, Stage 1–9."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

Gate0Class = Literal["operating", "financial_institution", "commodity"]
PeriodType = Literal["FY", "Q", "YTD"]
VersionStatus = Literal["draft", "accepted", "superseded", "conflict"]
ReviewStatus = Literal["pending", "accepted", "rejected"]
ChangeReason = Literal[
    "initial", "amendment", "restatement", "mapping_correction"
]
SourceKind = Literal[
    "sec_companyfacts", "sec_filing_manual", "ir_manual", "calculated", "fixture"
]

ProcessOutcome = Literal[
    "PROCEED",
    "CONDITIONAL",
    "REVIEW_REQUIRED",
    "TOO_HARD",
    "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY",
    "STOP_NO_THESIS",  # Stage 1: no ownership thesis on v1 quality path
]
Stage1ProcessOutcome = Literal[
    "PROCEED",
    "TOO_HARD",
    "REVIEW_REQUIRED",
    "STOP_NO_THESIS",
]
Stage3ProcessOutcome = Literal[
    "PROCEED",
    "CONDITIONAL",
    "REVIEW_REQUIRED",
    "TOO_HARD",
]
Stage4ProcessOutcome = Literal[
    "PROCEED",
    "CONDITIONAL",
    "REVIEW_REQUIRED",
    "TOO_HARD",
]
Stage5ProcessOutcome = Literal[
    "PROCEED",
    "CONDITIONAL",
    "REVIEW_REQUIRED",
    "TOO_HARD",
]
Stage6ProcessOutcome = Literal[
    "PROCEED",
    "CONDITIONAL",
    "REVIEW_REQUIRED",
    "TOO_HARD",
]
Stage7ProcessOutcome = Literal[
    "PROCEED",
    "CONDITIONAL",
    "REVIEW_REQUIRED",
    "TOO_HARD",
]
Stage8ProcessOutcome = Literal[
    "PROCEED",
    "CONDITIONAL",
    "REVIEW_REQUIRED",
    "TOO_HARD",
]
Stage9ProcessOutcome = Literal[
    "PROCEED",
    "CONDITIONAL",
    "REVIEW_REQUIRED",
    "TOO_HARD",
]
StalenessClass = Literal["CURRENT", "RECENT", "STALE", "UNKNOWN"]
ExpectationsVocab = Literal[
    "conservative",
    "plausible",
    "demanding",
    "heroic",
    "incoherent_with_evidence",
    "unknown",
]
UncertaintyVocab = Literal[
    "low",
    "moderate",
    "high",
    "extreme",
    "unanalyzable",
]
DiscountClass = Literal[
    "low_uncertainty_franchise",
    "standard_opco",
    "high_uncertainty",
    "cyclical_elevated",
]
ScenarioName = Literal["conservative", "central", "optimistic"]
AlignmentLabel = Literal["aligned", "tension", "opaque", "unknown"]
DebtMotiveTag = Literal[
    "deal_finance",
    "levered_distribution",
    "refi_ops",
    "fortress_build",
    "cyclical_timing",
    "over_conservatism",
    "unclear",
]
CommEvidenceKind = Literal["FACT", "GUIDANCE", "MANAGEMENT_CLAIM", "SYSTEM_INFERENCE"]
ExecutionDeliveryTag = Literal[
    "delivered",
    "partial",
    "missed",
    "goalposts_moved",
    "insufficient_history",
    "unknown",
]
DividendPolicyLabel = Literal[
    "commitment-like", "residual", "special/ad hoc", "none", "unknown"
]
IncrementalROICClass = Literal[
    "structurally_informative",
    "noisy",
    "distorted",
    "not_meaningful",
    "unknown",
]
RunwayEvidenceLabel = Literal[
    "ample",
    "limited",
    "unclear",
    "not_applicable",
]
PricingPowerPosture = Literal[
    "STRONG", "MODERATE", "WEAK", "MIXED", "UNKNOWN", "NOT_APPLICABLE"
]
IncrementalOMClass = Literal[
    "reported", "structurally_informative", "distorted", "unknown"
]
DurabilityConfidence = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
BenchmarkLabel = Literal[
    "ABOVE_REFERENCE",
    "PASS",
    "BELOW_REFERENCE",
    "MIXED",
    "UNKNOWN",
    "NOT_APPLICABLE",
]
RunwayConfidence = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
EvidenceKind = Literal["FACT", "COMPANY_EXPLANATION", "MODEL_INFERENCE"]
PrimaryArchetype = Literal[
    "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11"
]


@dataclass
class FieldLineage:
    field: str
    value: Any
    period_key: str
    version_id: str
    source_kind: SourceKind | str
    source_ref: str | None = None
    source_id: str | None = None
    fetched_or_entered_at: str | None = None
    reviewed_by: str = "none"
    review_status: ReviewStatus = "pending"
    notes: str | None = None
    uncertain: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PeriodVersionMeta:
    ticker: str
    period_key: str
    version_id: str
    period_type: PeriodType
    status: VersionStatus = "draft"
    change_reason: ChangeReason = "initial"
    cik: str | None = None
    entity_name: str | None = None
    gate0_class: Gate0Class = "operating"
    reporting_currency: str = "USD"
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    filed_at: str | None = None
    available_as_of: str | None = None
    accession: str | None = None
    source_id: str | None = None
    accepted_at: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    statement_basis: str = "us-gaap"
    unit_scale: str = "as_reported"
    review_status: ReviewStatus = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FAListEntry:
    ticker: str
    name: str | None = None
    synthetic_demo: bool = False
    gate0_class: Gate0Class = "operating"
    notes: str | None = None


@dataclass
class FAList:
    companies: list[FAListEntry] = field(default_factory=list)
    updated_at: str | None = None
    note: str | None = None
    synthetic_demo: bool = False


@dataclass
class StructuredSemanticReview:
    """Placeholder structured fields for LLM/human semantic review — no silent GAAP rewrite."""

    covenants_notes: str | None = None
    going_concern_language: bool = False
    going_concern_excerpt: str | None = None
    severe_solvency_language: bool = False
    liquidity_mdna_flags: list[str] = field(default_factory=list)
    leverage_optional_vs_required: Literal[
        "optional", "required", "unclear", "not_assessed"
    ] = "not_assessed"
    near_term_liquidity_failure_credible: bool = False
    near_term_liquidity_notes: str | None = None
    off_balance_commitments_notes: str | None = None
    restricted_cash_notes: str | None = None
    undrawn_facilities_notes: str | None = None
    maturity_notes: str | None = None
    other_flags: list[str] = field(default_factory=list)
    review_source: str = "placeholder"  # fixture | human | llm_pending
    filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CalcResult:
    """Deterministic calc output; null values carry reasons."""

    metrics: dict[str, Any] = field(default_factory=dict)
    null_reasons: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"metrics": self.metrics, "null_reasons": self.null_reasons}


@dataclass
class QuestionAnswer:
    question_id: str
    question: str
    status: Literal["answered", "partial", "missing", "blocked"]
    answer_summary: str
    evidence: list[str] = field(default_factory=list)
    must: bool = True


@dataclass
class Stage2Report:
    ticker: str
    date: str
    periods_used: list[dict[str, str]]
    sources: list[str]
    process_outcome: ProcessOutcome
    narrative_verdict: str
    survival_thesis: str
    evidence_bullets: dict[str, list[str]]
    falsifiers: list[str]
    monitors: list[str]
    gaps: list[str]
    enough_to_proceed: Literal["Yes", "No", "Conditional"]
    enough_why: str
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    calc: CalcResult | None = None
    semantic: StructuredSemanticReview | None = None
    block_next: bool = False
    block_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d



@dataclass
class Stage3SemanticFinding:
    """One Notes/MD&A cash-generation finding — no numeric materiality bar."""

    topic: str
    citation: str | None = None
    classification: str = "note"  # note | mdna | cf_footnote | other
    # FACT = filing fact; COMPANY_EXPLANATION = mgmt narrative; MODEL_INFERENCE = our inference
    evidence_kind: str = "COMPANY_EXPLANATION"  # FACT | COMPANY_EXPLANATION | MODEL_INFERENCE
    materiality_judgment: str = "not_assessed"  # material | watchable | immaterial | unclear | not_assessed
    materiality_reason: str = ""
    escalate_to_human: bool = False
    excerpt: str | None = None
    accession: str | None = None
    section: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage3SemanticReview:
    """Structured Stage 3 Notes/MD&A review — heuristic or LLM; never invents amounts."""

    findings: list[Stage3SemanticFinding] = field(default_factory=list)
    maintenance_capex_status: Literal["UNKNOWN", "DISCLOSED_WITH_EVIDENCE"] = "UNKNOWN"
    maintenance_capex_evidence: str | None = None
    maintenance_capex_amount: float | None = None  # only when DISCLOSED_WITH_EVIDENCE
    factoring_or_supplier_finance_notes: str | None = None
    acquisitions_notes: str | None = None
    asset_sales_notes: str | None = None
    restructuring_notes: str | None = None
    capitalized_costs_notes: str | None = None
    unusual_cash_notes: str | None = None
    wc_distortion_notes: str | None = None
    checklist_coverage: list[str] = field(default_factory=list)
    review_source: str = "placeholder"  # fixture | heuristic | human | llm_pending
    filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage3Report:
    """Stage 3 Cash Generation evidence pack — no colors, no thresholds, no Stage 4."""

    ticker: str
    date: str
    periods_used: list[dict[str, str]]
    sources: list[str]
    process_outcome: Stage3ProcessOutcome
    why_bullets: list[str]
    carry_forward_concerns: list[str]
    cash_conversion_bullets: list[str]
    working_capital_bullets: list[str]
    capex_bullets: list[str]
    cash_quality_warnings: list[str]
    what_is_strong: list[str]
    what_can_break: list[str]
    monitors: list[str]
    missing_ambiguous: list[str]
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    calc: CalcResult | None = None
    semantic: Stage3SemanticReview | None = None
    # Stage 3 never mechanically terminates later stages (SPEC_LOCKED §0 / §7)
    terminates_later_stages: bool = False
    refuse_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage1Thesis:
    """Ownership thesis card fields (Stage 1 Gate 2). Valuation deferred."""

    one_sentence: str = ""
    customer_value_job: str = ""
    customer_value_why: str = ""
    advantage_type: str = ""
    advantage_persist: str = ""
    advantage_evidence: str = ""
    runway_what: str = ""
    runway_confidence: str = ""  # high | medium | low | unknown
    reinvestment_where: str = ""
    capital_intensity: str = ""  # capital-light | intensive | hybrid
    margins_note: str = ""
    management_worry: str = ""
    kill_shot_primary: str = ""
    kill_shot_secondary: str = ""
    monitors: list[str] = field(default_factory=list)
    financial_validation_later: list[str] = field(default_factory=list)
    language: str = "EN"  # TR default preferred; language choice TBD §11.4

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage1Report:
    ticker: str
    date: str
    gate0_class: str
    process_outcome: Stage1ProcessOutcome
    narrative_verdict: str
    enough_to_proceed: Literal["Yes", "No"]
    enough_why: str
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    thesis: Stage1Thesis | None = None
    warnings: list[str] = field(default_factory=list)
    block_reasons: list[str] = field(default_factory=list)
    ban_list_hits: list[str] = field(default_factory=list)
    block_stage2: bool = True  # False only when PROCEED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)



@dataclass
class Stage4SemanticFinding:
    """One growth-quality MD&A/Notes finding — FACT | COMPANY_EXPLANATION | MODEL_INFERENCE."""

    topic: str
    citation: str | None = None
    classification: str = "mdna"  # mdna | note | segment | ir | earnings | other
    evidence_kind: str = "COMPANY_EXPLANATION"
    materiality_judgment: str = "not_assessed"
    materiality_reason: str = ""
    escalate_to_human: bool = False
    excerpt: str | None = None
    accession: str | None = None
    section: str | None = None
    dimension: str | None = None  # volume|price|mix|FX|acquisition|geo|product|...

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage4SemanticReview:
    """Structured Stage 4 Notes/MD&A/IR growth review — heuristic or fixture; no invented %. """

    findings: list[Stage4SemanticFinding] = field(default_factory=list)
    organic_acquired_notes: str | None = None
    fx_notes: str | None = None
    volume_price_mix_notes: str | None = None
    geography_product_notes: str | None = None
    runway_claim_notes: str | None = None
    dilution_notes: str | None = None
    ma_notes: str | None = None
    backlog_rpo_notes: str | None = None
    recurring_notes: str | None = None
    cycle_notes: str | None = None
    checklist_coverage: list[str] = field(default_factory=list)
    review_source: str = "placeholder"
    filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArchetypeAdaptation:
    """ONE PRIMARY_ARCHETYPE + SECONDARY_TRAITS + ~1–3 drivers. No score blend."""

    primary_archetype: str  # A1–A11
    primary_label: str = ""
    secondary_traits: list[str] = field(default_factory=list)
    model_specific_drivers: list[dict[str, Any]] = field(default_factory=list)
    model_slot: str | None = None
    model_slot_status: str = "NOT_APPLICABLE"  # set | NOT_APPLICABLE
    classification_path: str = "AUTOMATED"  # AUTOMATED | REVIEW_REQUIRED
    confidence: str = "MEDIUM"  # HIGH | MEDIUM | LOW | UNKNOWN
    ambiguity_notes: str | None = None
    evidence: list[str] = field(default_factory=list)
    provenance: str = "heuristic"
    why: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkDimensionResult:
    """One BD1–BD9 evidence label + WHY. Not a gate."""

    dimension_id: str  # BD1..BD9
    label: str  # BenchmarkLabel
    why: str
    applicability: str = "universal"  # universal | conditional | should | pattern_only
    evidence: list[str] = field(default_factory=list)
    reference_frame: str | None = None  # archetype | company_history | peer_secondary

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GrowthDecomposition:
    """Per-period growth decomposition with evidence tags."""

    period_key: str
    reported_revenue_change: float | None = None
    reported_revenue_change_pct: float | None = None
    components: list[dict[str, Any]] = field(default_factory=list)
    unattributed_or_unknown: str | None = None
    organic_vs_acquired_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunwayAssessment:
    """Runway evidence + confidence — not a score; no fake year precision."""

    summary: str = ""
    lenses_used: list[str] = field(default_factory=list)
    confidence: str = "UNKNOWN"  # HIGH|MEDIUM|LOW|UNKNOWN
    falsifiers: list[str] = field(default_factory=list)
    thesis_link: str | None = None
    fact_evidence: list[str] = field(default_factory=list)
    guidance_evidence: list[str] = field(default_factory=list)
    external_evidence: list[str] = field(default_factory=list)
    inference_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage4Report:
    """Stage 4 Growth Quality / Runway evidence pack — no colors, no thresholds, no Stage 5."""

    ticker: str
    date: str
    periods_used: list[dict[str, str]]
    sources: list[str]
    process_outcome: Stage4ProcessOutcome
    why_bullets: list[str]
    carry_forward_concerns: list[str]
    growth_observed_bullets: list[str]
    decomposition_bullets: list[str]
    runway_bullets: list[str]
    thesis_link_bullets: list[str]
    false_positive_tags: list[dict[str, Any]]
    benchmark_results: list[BenchmarkDimensionResult]
    context_tags: list[str]  # MATURE_FRANCHISE_OK | CHALLENGE_ARCHETYPE | HIGH_GROWTH_QUALITY_RISK
    archetype: ArchetypeAdaptation | None
    runway: RunwayAssessment | None
    decompositions: list[GrowthDecomposition]
    what_is_strong: list[str]
    what_can_break: list[str]
    monitors: list[str]
    missing_ambiguous: list[str]
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    calc: CalcResult | None = None
    semantic: Stage4SemanticReview | None = None
    terminates_later_stages: bool = False
    refuse_reason: str | None = None
    thesis_coherence: str = "unknown"  # supports | strains | falsifies | unknown

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)



@dataclass
class Stage5SemanticFinding:
    """One margin/economics MD&A/Notes finding — FACT | COMPANY_EXPLANATION | MODEL_INFERENCE."""

    topic: str
    citation: str | None = None
    classification: str = "mdna"  # mdna | note | segment | ir | other
    evidence_kind: str = "COMPANY_EXPLANATION"
    materiality_judgment: str = "not_assessed"
    materiality_reason: str = ""
    escalate_to_human: bool = False
    excerpt: str | None = None
    accession: str | None = None
    section: str | None = None
    dimension: str | None = None  # price|mix|volume|input|labor|distribution|SES|accounting|...

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage5SemanticReview:
    """Structured Stage 5 Notes/MD&A economics review — heuristic or fixture; no invented bands."""

    findings: list[Stage5SemanticFinding] = field(default_factory=list)
    pricing_power_notes: str | None = None
    cost_advantage_notes: str | None = None
    margin_bridge_notes: str | None = None
    input_cost_notes: str | None = None
    sbc_nongaap_notes: str | None = None
    ses_notes: str | None = None
    segment_margin_notes: str | None = None
    unit_econ_notes: str | None = None
    cycle_peak_notes: str | None = None
    investment_phase_notes: str | None = None
    checklist_coverage: list[str] = field(default_factory=list)
    review_source: str = "placeholder"
    filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MarginDecomposition:
    """Per-window margin decomposition with evidence tags. Plan §5."""

    period_key: str
    reported_gross_margin: float | None = None
    reported_operating_margin: float | None = None
    delta_vs_prior_gm: float | None = None
    delta_vs_prior_op: float | None = None
    components: list[dict[str, Any]] = field(default_factory=list)
    unattributed_or_unknown: str | None = None
    ses_or_intentional_thin_margin: str = "unknown"  # yes|no|unknown
    ses_why: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IncrementalOMWindow:
    """Descriptive ΔOP/ΔRev window — not a hurdle; ≠ Stage 6 ROIC."""

    window_id: str
    from_period: str | None = None
    to_period: str | None = None
    delta_op: float | None = None
    delta_rev: float | None = None
    incremental_om: float | None = None  # ΔOP/ΔRev when computable
    posture_class: str = "unknown"  # reported|structurally_informative|distorted|unknown
    cause_tag: str | None = None
    honesty_flags: list[str] = field(default_factory=list)
    null_reason: str | None = None
    stage6_handoff: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PricingPowerAssessment:
    """Evidence-of-claim only — STRONG ≠ PROCEED; WEAK ≠ fail."""

    posture: str = "UNKNOWN"  # PricingPowerPosture
    evidence: list[str] = field(default_factory=list)
    falsifiers: list[str] = field(default_factory=list)
    why: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DurabilityAssessment:
    """Economics durability — confidence is not a score; no fake moat width."""

    summary: str = ""
    confidence: str = "UNKNOWN"  # HIGH|MEDIUM|LOW|UNKNOWN
    falsifiers: list[str] = field(default_factory=list)
    thesis_link: str | None = None
    lenses_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage5Report:
    """Stage 5 Margins / Business Economics evidence pack — no colors, no bands, no Stage 6."""

    ticker: str
    date: str
    periods_used: list[dict[str, str]]
    sources: list[str]
    process_outcome: Stage5ProcessOutcome
    why_bullets: list[str]
    carry_forward_concerns: list[str]
    margin_structure_bullets: list[str]
    decomposition_bullets: list[str]
    pricing_cost_bullets: list[str]
    incremental_om_bullets: list[str]
    durability_bullets: list[str]
    thesis_link_bullets: list[str]
    false_positive_tags: list[dict[str, Any]]
    benchmark_results: list[BenchmarkDimensionResult]
    context_tags: list[str]  # closed Stage 5 set only
    archetype: ArchetypeAdaptation | None
    pricing_power: PricingPowerAssessment | None
    durability: DurabilityAssessment | None
    decompositions: list[MarginDecomposition]
    incremental_om_windows: list[IncrementalOMWindow]
    what_is_strong: list[str]
    what_can_break: list[str]
    monitors: list[str]
    missing_ambiguous: list[str]
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    calc: CalcResult | None = None
    semantic: Stage5SemanticReview | None = None
    terminates_later_stages: bool = False
    refuse_reason: str | None = None
    thesis_coherence: str = "unknown"  # supports | strains | falsifies | unknown
    model_specific_slot: str | None = None
    model_specific_slot_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)



@dataclass
class Stage6SemanticFinding:
    """One Notes/MD&A capital/reinvestment finding — FACT | COMPANY_EXPLANATION | MODEL_INFERENCE."""

    topic: str
    citation: str | None = None
    classification: str = "mdna"  # mdna | note | ir | other
    evidence_kind: str = "COMPANY_EXPLANATION"
    materiality_judgment: str = "not_assessed"
    materiality_reason: str = ""
    escalate_to_human: bool = False
    excerpt: str | None = None
    accession: str | None = None
    section: str | None = None
    dimension: str | None = None  # maint_capex|growth_capex|acquisition|runway|distortion|fp|other

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage6SemanticReview:
    """Structured Stage 6 Notes/MD&A capital review — fixture-loadable; no invented thresholds."""

    findings: list[Stage6SemanticFinding] = field(default_factory=list)
    maint_growth_capex_notes: str | None = None
    maint_capex_status: str = "UNKNOWN"  # UNKNOWN | DISCLOSED_WITH_EVIDENCE | NOT_DISCLOSED
    acquisition_context_notes: str | None = None
    runway_notes: str | None = None
    distortion_notes: str | None = None
    fp_explanation_notes: str | None = None
    lease_accounting_notes: str | None = None
    investment_phase_notes: str | None = None
    impairment_notes: str | None = None
    capital_destination_notes: str | None = None
    checklist_coverage: list[str] = field(default_factory=list)
    review_source: str = "placeholder"
    filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IncrementalROICWindow:
    """Descriptive ΔNOPAT/ΔIC window — not a hurdle; ≠ Stage 5 Incremental OM."""

    window_id: str
    from_period: str | None = None
    to_period: str | None = None
    delta_nopat: float | None = None
    delta_ic: float | None = None
    incremental_roic: float | None = None
    meaning_class: str = "unknown"  # IncrementalROICClass
    cause_tag: str | None = None
    honesty_flags: list[str] = field(default_factory=list)
    null_reason: str | None = None
    stage5_boundary: str = "≠ Stage 5 Incremental OM (IOM); separate ROIIC namespace"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DualROICView:
    """Acquisition-inclusive PRIMARY + tangible companion. Tangible ≠ M&A success."""

    period_key: str | None = None
    nopat: float | None = None
    nopat_null: str | None = None
    tax_rate: float | None = None
    tax_rate_source: str | None = None
    ic_inclusive: float | None = None
    ic_tangible: float | None = None
    average_ic_inclusive: float | None = None
    average_ic_tangible: float | None = None
    average_ic_method: str | None = None
    roic_inclusive: float | None = None
    roic_tangible: float | None = None
    dual_view_emitted: bool = False
    dual_view_mandatory: bool = False
    tangible_ne_ma_success: bool = True
    definition_labels: dict[str, Any] = field(default_factory=dict)
    nibol_incomplete: bool = False
    financing_check_gap: float | None = None
    financing_check_flag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage6Report:
    """Stage 6 ROIC / Reinvestment evidence pack — no colors, no numeric hurdles, no Stage 7."""

    ticker: str
    date: str
    periods_used: list[dict[str, str]]
    sources: list[str]
    process_outcome: Stage6ProcessOutcome
    why_bullets: list[str]
    carry_forward_concerns: list[str]
    dual_roic_bullets: list[str]
    incremental_roic_bullets: list[str]
    reinvestment_composition_bullets: list[str]
    runway_bullets: list[str]
    capex_productivity_bullets: list[str]
    wc_mechanism_bullets: list[str]
    false_positive_tags: list[dict[str, Any]]
    benchmark_results: list[BenchmarkDimensionResult]
    archetype: ArchetypeAdaptation | None
    dual_roic: DualROICView | None
    incremental_roic_windows: list[IncrementalROICWindow]
    runway_label: str = "unclear"  # RunwayEvidenceLabel
    stage7_handoff_flags: list[str] = field(default_factory=list)
    what_is_strong: list[str] = field(default_factory=list)
    what_can_break: list[str] = field(default_factory=list)
    monitors: list[str] = field(default_factory=list)
    missing_ambiguous: list[str] = field(default_factory=list)
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    calc: CalcResult | None = None
    semantic: Stage6SemanticReview | None = None
    terminates_later_stages: bool = False
    refuse_reason: str | None = None
    thesis_coherence: str = "unknown"  # supports | strains | falsifies | unknown
    d10_elevated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)




@dataclass
class Stage7SemanticFinding:
    """One Stage 7 semantic finding — FACT | GUIDANCE | MANAGEMENT_CLAIM | SYSTEM_INFERENCE."""

    topic: str
    citation: str | None = None
    classification: str = "proxy"  # proxy | def14a | mdna | 8k | ir | other
    evidence_kind: str = "MANAGEMENT_CLAIM"  # CommEvidenceKind
    materiality_judgment: str = "not_assessed"
    materiality_reason: str = ""
    escalate_to_human: bool = False
    excerpt: str | None = None
    accession: str | None = None
    section: str | None = None
    dimension: str | None = None  # hierarchy|incentives|ma|gov|comm|exec|succession|fp|debt|other
    mg_lens: str | None = None  # MG1..MG9 when mapped

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage7SemanticReview:
    """Structured Stage 7 semantic review — CD&A / hierarchy / gov / comm; fixture-loadable."""

    findings: list[Stage7SemanticFinding] = field(default_factory=list)
    stated_hierarchy_notes: str | None = None
    incentive_metrics_notes: str | None = None
    ownership_guidelines_notes: str | None = None
    governance_structure_notes: str | None = None
    related_party_notes: str | None = None
    deal_criteria_notes: str | None = None
    guidance_delivery_notes: str | None = None
    succession_notes: str | None = None
    buyback_policy_notes: str | None = None
    dividend_policy_notes: str | None = None
    debt_motive_notes: str | None = None
    checklist_coverage: list[str] = field(default_factory=list)
    review_source: str = "placeholder"
    filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MGLensResult:
    """One MG1–MG9 evidence lens — not a score; no weighted average."""

    lens_id: str  # MG1..MG9
    lens_name: str
    summary: str = ""
    why: str = ""
    labels: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    s6_flags_consumed: list[str] = field(default_factory=list)
    escalate_to_human: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage7Report:
    """Stage 7 Management / Allocation evidence pack — no colors, no scores, no Stage 8."""

    ticker: str
    date: str
    periods_used: list[dict[str, str]]
    sources: list[str]
    process_outcome: Stage7ProcessOutcome
    why_bullets: list[str]
    carry_forward_concerns: list[str]
    hierarchy_bullets: list[str]
    s6_handoff_bullets: list[str]
    ma_process_bullets: list[str]
    distribution_bullets: list[str]
    incentive_bullets: list[str]
    communication_execution_bullets: list[str]
    fp_gov_succession_bullets: list[str]
    false_positive_tags: list[dict[str, Any]]
    benchmark_results: list[BenchmarkDimensionResult]
    mg_lenses: list[MGLensResult]
    archetype: ArchetypeAdaptation | None
    alignment_label: str = "unknown"  # AlignmentLabel
    dividend_policy_label: str = "unknown"  # DividendPolicyLabel
    debt_motive_tags: list[str] = field(default_factory=list)
    s6_handoff_flags_consumed: list[str] = field(default_factory=list)
    what_is_strong: list[str] = field(default_factory=list)
    what_can_break: list[str] = field(default_factory=list)
    monitors: list[str] = field(default_factory=list)
    missing_ambiguous: list[str] = field(default_factory=list)
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    calc: CalcResult | None = None
    semantic: Stage7SemanticReview | None = None
    terminates_later_stages: bool = False
    refuse_reason: str | None = None
    thesis_coherence: str = "unknown"  # supports | strains | falsifies | unknown
    a7_mg3_depth_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)



@dataclass
class Stage8SemanticFinding:
    """One Stage 8 semantic finding — FACT | COMPANY_EXPLANATION | MODEL_INFERENCE."""

    topic: str
    citation: str | None = None
    classification: str = "other"
    evidence_kind: str = "MODEL_INFERENCE"
    materiality_judgment: str = "not_assessed"
    materiality_reason: str = ""
    escalate_to_human: bool = False
    excerpt: str | None = None
    dimension: str | None = None  # bridge|norm|dcf|reverse|multiples|mos|fp|conflict|other
    va_lens: str | None = None  # VA1..VA8 when mapped

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage8SemanticReview:
    """Structured Stage 8 semantic review — fixture-loadable; no LLM required."""

    findings: list[Stage8SemanticFinding] = field(default_factory=list)
    normalization_notes: str | None = None
    driver_why_notes: str | None = None
    expectations_notes: str | None = None
    mos_qualitative_notes: str | None = None
    fp_v_notes: str | None = None
    post_period_event_notes: str | None = None
    conflict_notes: str | None = None
    a7_organic_acq_notes: str | None = None
    checklist_coverage: list[str] = field(default_factory=list)
    review_source: str = "placeholder"
    filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VALensResult:
    """One VA1–VA8 evidence lens — not a score; no weighted average."""

    lens_id: str  # VA1..VA8
    lens_name: str
    summary: str = ""
    why: str = ""
    labels: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    escalate_to_human: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage8Report:
    """Stage 8 Valuation / IV / MoS evidence pack — no colors, no scores, no BUY/SELL."""

    ticker: str
    date: str
    periods_used: list[dict[str, str]]
    sources: list[str]
    process_outcome: Stage8ProcessOutcome
    why_bullets: list[str]
    carry_forward_concerns: list[str]
    market_bridge_bullets: list[str]
    normalized_base_bullets: list[str]
    iv_range_bullets: list[str]
    reverse_dcf_bullets: list[str]
    multiples_bullets: list[str]
    dilution_cs_bullets: list[str]
    mos_uncertainty_bullets: list[str]
    false_positive_tags: list[dict[str, Any]]
    benchmark_results: list[BenchmarkDimensionResult]
    va_lenses: list[VALensResult]
    archetype: ArchetypeAdaptation | None
    staleness_class: str = "UNKNOWN"  # StalenessClass
    expectations_label: str = "unknown"  # ExpectationsVocab
    uncertainty_label: str = "unanalyzable"  # UncertaintyVocab
    uncertainty_drivers: list[str] = field(default_factory=list)
    discount_class: str = "standard_opco"  # DiscountClass
    price_sensitive_suppressed: bool = False
    a7_dual_exhibits: bool = False
    dual_terminal_note: str | None = None
    stage4_6_7_conflicts: list[str] = field(default_factory=list)
    s6_handoff_flags_consumed: list[str] = field(default_factory=list)
    s7_h8_carries: list[str] = field(default_factory=list)
    s8_h9_carries: list[str] = field(default_factory=list)
    what_is_strong: list[str] = field(default_factory=list)
    what_can_break: list[str] = field(default_factory=list)
    monitors: list[str] = field(default_factory=list)
    missing_ambiguous: list[str] = field(default_factory=list)
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    calc: CalcResult | None = None
    semantic: Stage8SemanticReview | None = None
    terminates_later_stages: bool = False
    refuse_reason: str | None = None
    thesis_coherence: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)



@dataclass
class Stage9SemanticFinding:
    """One Stage 9 semantic finding — FACT | GUIDANCE | CLAIM | INFERENCE | UNKNOWN."""

    topic: str
    citation: str | None = None
    classification: str = "other"  # business|competition|risk_factors|legal|geo|macro|handoff|other
    evidence_kind: str = "INFERENCE"  # EvidenceLabel
    materiality_judgment: str = "not_assessed"
    materiality_reason: str = ""
    escalate_to_human: bool = False
    excerpt: str | None = None
    accession: str | None = None
    section: str | None = None
    dimension: str | None = None  # structure|moat|disruption|concentration|regulatory|geo|macro|breaker|fp|conflict|other
    er_lens: str | None = None  # ER1..ER8 when mapped
    mechanism: str | None = None
    exposure: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage9SemanticReview:
    """Structured Stage 9 semantic review — filings heuristic + fixture-loadable."""

    findings: list[Stage9SemanticFinding] = field(default_factory=list)
    industry_structure_notes: str | None = None
    competition_notes: str | None = None
    moat_stress_notes: str | None = None
    disruption_notes: str | None = None
    concentration_notes: str | None = None
    regulatory_notes: str | None = None
    geopolitical_notes: str | None = None
    macro_cycle_notes: str | None = None
    breaker_notes: str | None = None
    conflict_notes: str | None = None
    checklist_coverage: list[str] = field(default_factory=list)
    review_source: str = "placeholder"
    filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ERLensResult:
    """One ER1–ER8 evidence lens — not a score; no weighted average."""

    lens_id: str  # ER1..ER8
    lens_name: str
    summary: str = ""
    why: str = ""
    labels: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    mechanism: str | None = None
    exposure: str | None = None
    evidence_label: str = "UNKNOWN"  # FACT|GUIDANCE|CLAIM|INFERENCE|UNKNOWN
    escalate_to_human: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ThesisBreaker:
    """One observable falsifier + monitoring variables — ER8 item (not kitchen-sink)."""

    breaker_id: str
    mechanism: str
    observable_indicators: list[str] = field(default_factory=list)
    monitoring_variables: list[str] = field(default_factory=list)
    evidence_label: str = "UNKNOWN"
    linked_er_lenses: list[str] = field(default_factory=list)
    active_fact: bool = False
    source_tie: str | None = None  # e.g. Gate2 kill-shot / semantic

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage9Report:
    """Stage 9 External Risk evidence pack — no colors, scores, BUY/SELL, or final FA synthesis."""

    ticker: str
    date: str
    periods_used: list[dict[str, str]]
    sources: list[str]
    process_outcome: Stage9ProcessOutcome
    why_bullets: list[str]
    carry_forward_concerns: list[str]
    industry_structure_bullets: list[str]
    moat_durability_bullets: list[str]
    disruption_bullets: list[str]
    concentration_bullets: list[str]
    regulatory_geo_bullets: list[str]
    macro_cycle_bullets: list[str]
    breaker_fp_bullets: list[str]
    false_positive_tags: list[dict[str, Any]]
    er_lenses: list[ERLensResult]
    thesis_breakers: list[ThesisBreaker]
    archetype: ArchetypeAdaptation | None = None
    concentration_labels: dict[str, str] = field(default_factory=dict)  # axis -> low|moderate|high|extreme|unknown
    cycle_position_class: str = "unknown"  # early|mid|late|unknown — descriptive NOT prediction
    regulatory_posture: str = "unknown"  # barrier|sword|both|unknown
    s1_8_conflicts: list[str] = field(default_factory=list)
    s8_h9_carries_forwarded: list[str] = field(default_factory=list)
    s9_hfa_carries: list[str] = field(default_factory=list)
    gate2_hypothesis_consumed: dict[str, Any] = field(default_factory=dict)
    what_is_strong: list[str] = field(default_factory=list)
    what_can_break: list[str] = field(default_factory=list)
    monitors: list[str] = field(default_factory=list)
    missing_ambiguous: list[str] = field(default_factory=list)
    question_answers: list[QuestionAnswer] = field(default_factory=list)
    calc: CalcResult | None = None
    semantic: Stage9SemanticReview | None = None
    terminates_later_stages: bool = False
    refuse_reason: str | None = None
    thesis_coherence: str = "unknown"
    no_final_fa_synthesis: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)



@dataclass
class AnalyzeResult:
    ticker: str
    ok: bool
    refused: bool = False
    refuse_reason: str | None = None
    stage1: Stage1Report | None = None
    stage2: Stage2Report | None = None
    stage3: Stage3Report | None = None
    stage4: Stage4Report | None = None
    stage5: Stage5Report | None = None
    stage6: Stage6Report | None = None
    stage7: Stage7Report | None = None
    stage8: Stage8Report | None = None
    stage9: Stage9Report | None = None
    markdown: str | None = None
    company_dir: str | None = None
    stage2_blocked: bool = False
    stage2_block_reason: str | None = None
