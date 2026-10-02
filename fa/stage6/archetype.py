"""Stage 6 archetype adaptation — REUSE Stage 4 A1–A11; capital-efficiency drivers.

Prefer Stage 4 PRIMARY_ARCHETYPE + SECONDARY_TRAITS when available.
No casual expand of A1–A11. No ticker hardcoding. A7 → mandatory dual spine.
"""
from __future__ import annotations

from typing import Any

from ..models import ArchetypeAdaptation
from ..stage4.archetype import propose_archetype as stage4_propose_archetype
from .questions import CAPITAL_DRIVERS_BY_ARCHETYPE, PRIMARY_ARCHETYPES


def capital_drivers_for(primary: str, traits: list[str] | None = None) -> list[dict[str, Any]]:
    """~1–3 model-specific capital-efficiency drivers (Plan §13)."""
    traits = traits or []
    slots = CAPITAL_DRIVERS_BY_ARCHETYPE.get(primary) or CAPITAL_DRIVERS_BY_ARCHETYPE["A11"]
    out: list[dict[str, Any]] = []
    for key, label in slots[:3]:
        evidence = []
        if traits:
            evidence.append(f"traits={traits}")
        out.append(
            {
                "id": key,
                "label": label,
                "evidence": evidence
                or ["archetype-default capital slot; confirm with disclosure"],
                "status": "proposed",
            }
        )
    return out[:3]


def dual_view_mandatory_for(primary: str, traits: list[str] | None = None) -> bool:
    """A7 or acquisitive SECONDARY_TRAITS → mandatory both ROIC views."""
    traits = [t.lower() for t in (traits or [])]
    if primary == "A7":
        return True
    return any(
        t in {"acquisitive", "serial_acquirer", "bolt_on", "m&a", "ma_heavy"}
        for t in traits
    )


def adapt_from_stage4(
    stage4_archetype: dict[str, Any] | ArchetypeAdaptation | None,
    *,
    thesis_summary: str | None = None,
    business_notes: str | None = None,
    semantic_text: str | None = None,
    calc_hints: dict[str, Any] | None = None,
    force_primary: str | None = None,
) -> ArchetypeAdaptation:
    """Prefer reuse Stage 4 archetype; swap growth drivers for capital drivers."""
    base: ArchetypeAdaptation | None = None
    if isinstance(stage4_archetype, ArchetypeAdaptation):
        base = stage4_archetype
    elif isinstance(stage4_archetype, dict) and stage4_archetype.get("primary_archetype"):
        base = ArchetypeAdaptation(
            primary_archetype=stage4_archetype["primary_archetype"],
            primary_label=stage4_archetype.get("primary_label")
            or PRIMARY_ARCHETYPES.get(stage4_archetype["primary_archetype"], ""),
            secondary_traits=list(stage4_archetype.get("secondary_traits") or []),
            model_specific_drivers=[],
            model_slot=None,
            model_slot_status="NOT_APPLICABLE",
            classification_path=stage4_archetype.get("classification_path") or "AUTOMATED",
            confidence=stage4_archetype.get("confidence") or "MEDIUM",
            ambiguity_notes=stage4_archetype.get("ambiguity_notes"),
            evidence=list(stage4_archetype.get("evidence") or []),
            provenance=stage4_archetype.get("provenance") or "stage4_reuse",
            why=stage4_archetype.get("why") or "Reused Stage 4 PRIMARY_ARCHETYPE",
        )

    if base is None:
        base = stage4_propose_archetype(
            thesis_summary=thesis_summary,
            business_notes=business_notes,
            semantic_text=semantic_text,
            calc_hints=calc_hints,
            force_primary=force_primary,
        )
        base.provenance = "stage4_heuristic_via_stage6"
    else:
        if force_primary and force_primary in PRIMARY_ARCHETYPES:
            base.primary_archetype = force_primary
            base.primary_label = PRIMARY_ARCHETYPES[force_primary]
            base.provenance = "forced_primary"
        else:
            base.provenance = base.provenance or "stage4_reuse"

    primary = base.primary_archetype
    base.primary_label = base.primary_label or PRIMARY_ARCHETYPES.get(primary, "")
    base.model_specific_drivers = capital_drivers_for(primary, base.secondary_traits)

    # Model slot: dual_spine for A7; else not applicable capital slot
    if primary == "A7":
        base.model_slot = "dual_roic_spine"
        base.model_slot_status = "set"
    else:
        base.model_slot = "capital_efficiency"
        base.model_slot_status = "set"

    dual_note = (
        "dual_view_mandatory=True"
        if dual_view_mandatory_for(primary, base.secondary_traits)
        else "dual_view_when_gw_intangibles"
    )
    if not base.why:
        base.why = (
            f"PRIMARY={primary} ({base.primary_label}); capital drivers="
            f"{[d['id'] for d in base.model_specific_drivers]}; {dual_note}"
        )
    else:
        base.why = (
            f"{base.why} | Stage 6 capital drivers="
            f"{[d['id'] for d in base.model_specific_drivers]}; {dual_note}"
        )
    return base
