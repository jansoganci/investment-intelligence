"""Stage 8 archetype reuse — A1–A11 from Stage 4/6/7; valuation emphasis notes only."""
from __future__ import annotations

from typing import Any

from ..models import ArchetypeAdaptation
from ..stage4.archetype import propose_archetype as stage4_propose_archetype
from .questions import PRIMARY_ARCHETYPES, VALUATION_EMPHASIS_BY_ARCHETYPE


def a7_or_acquisitive(primary: str, traits: list[str] | None = None) -> bool:
    traits = [t.lower() for t in (traits or [])]
    if primary == "A7":
        return True
    return any(
        t in {"acquisitive", "serial_acquirer", "bolt_on", "m&a", "ma_heavy"}
        for t in traits
    )


def a8_or_a9(primary: str) -> bool:
    return primary in {"A8", "A9"}


def adapt_from_prior(
    prior_archetype: dict[str, Any] | ArchetypeAdaptation | None,
    *,
    thesis_summary: str | None = None,
    business_notes: str | None = None,
    semantic_text: str | None = None,
    force_primary: str | None = None,
) -> ArchetypeAdaptation:
    """Prefer Stage 7/6/4 archetype; valuation emphasis replaces allocation drivers."""
    base: ArchetypeAdaptation | None = None
    if isinstance(prior_archetype, ArchetypeAdaptation):
        base = prior_archetype
    elif isinstance(prior_archetype, dict) and prior_archetype.get("primary_archetype"):
        base = ArchetypeAdaptation(
            primary_archetype=prior_archetype["primary_archetype"],
            primary_label=prior_archetype.get("primary_label")
            or PRIMARY_ARCHETYPES.get(prior_archetype["primary_archetype"], ""),
            secondary_traits=list(prior_archetype.get("secondary_traits") or []),
            model_specific_drivers=[],
            model_slot=None,
            model_slot_status="NOT_APPLICABLE",
            classification_path=prior_archetype.get("classification_path") or "AUTOMATED",
            confidence=prior_archetype.get("confidence") or "MEDIUM",
            ambiguity_notes=prior_archetype.get("ambiguity_notes"),
            evidence=list(prior_archetype.get("evidence") or []),
            provenance=prior_archetype.get("provenance") or "prior_stage_reuse",
            why=prior_archetype.get("why") or "Reused prior-stage PRIMARY_ARCHETYPE",
        )

    if base is None:
        base = stage4_propose_archetype(
            thesis_summary=thesis_summary,
            business_notes=business_notes,
            semantic_text=semantic_text,
            force_primary=force_primary,
        )
        base.provenance = "stage4_heuristic_via_stage8"
    else:
        if force_primary and force_primary in PRIMARY_ARCHETYPES:
            base.primary_archetype = force_primary
            base.primary_label = PRIMARY_ARCHETYPES[force_primary]
            base.provenance = "forced_primary"
        else:
            base.provenance = base.provenance or "prior_stage_reuse"

    primary = base.primary_archetype
    base.primary_label = base.primary_label or PRIMARY_ARCHETYPES.get(primary, "")
    emphasis = VALUATION_EMPHASIS_BY_ARCHETYPE.get(primary) or VALUATION_EMPHASIS_BY_ARCHETYPE[
        "A11"
    ]
    base.model_specific_drivers = [
        {
            "id": e,
            "label": e.replace("_", " "),
            "evidence": [f"archetype={primary} valuation emphasis"],
            "status": "proposed",
        }
        for e in emphasis[:4]
    ]
    base.model_slot = "valuation_method_emphasis"
    base.model_slot_status = "set"
    a7_note = (
        "a7_dual_organic_acq=True; recurring_ma=reinvestment"
        if a7_or_acquisitive(primary, base.secondary_traits)
        else "a7_dual=False"
    )
    mid = "mid_cycle_mandatory=True" if a8_or_a9(primary) else "mid_cycle_mandatory=False"
    if not base.why:
        base.why = (
            f"PRIMARY={primary} ({base.primary_label}); valuation emphasis="
            f"{[d['id'] for d in base.model_specific_drivers]}; {a7_note}; {mid}"
        )
    else:
        base.why = (
            f"{base.why} | Stage 8 valuation emphasis="
            f"{[d['id'] for d in base.model_specific_drivers]}; {a7_note}; {mid}"
        )
    return base
