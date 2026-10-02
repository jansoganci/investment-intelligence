"""Stage 5 archetype adaptation — REUSE Stage 4 A1–A11; economics drivers.

Prefer Stage 4 PRIMARY_ARCHETYPE + SECONDARY_TRAITS when available.
No casual expand of A1–A11. No ticker hardcoding. No score blend.
"""
from __future__ import annotations

from typing import Any

from ..models import ArchetypeAdaptation
from ..stage4.archetype import propose_archetype as stage4_propose_archetype
from .questions import (
    ECONOMICS_DRIVERS_BY_ARCHETYPE,
    MODEL_SLOT_BY_ARCHETYPE,
    PRIMARY_ARCHETYPES,
)


def economics_drivers_for(primary: str, traits: list[str] | None = None) -> list[dict[str, Any]]:
    """~1–3 model-specific economics drivers (Plan §3.3)."""
    traits = traits or []
    slots = ECONOMICS_DRIVERS_BY_ARCHETYPE.get(primary) or ECONOMICS_DRIVERS_BY_ARCHETYPE["A11"]
    out: list[dict[str, Any]] = []
    for key, label in slots[:3]:
        evidence = []
        if traits:
            evidence.append(f"traits={traits}")
        out.append(
            {
                "id": key,
                "label": label,
                "evidence": evidence or ["archetype-default economics slot; confirm with disclosure"],
                "status": "proposed",
            }
        )
    return out[:3]


def adapt_from_stage4(
    stage4_archetype: dict[str, Any] | ArchetypeAdaptation | None,
    *,
    thesis_summary: str | None = None,
    business_notes: str | None = None,
    semantic_text: str | None = None,
    calc_hints: dict[str, Any] | None = None,
    force_primary: str | None = None,
) -> ArchetypeAdaptation:
    """
    Prefer reuse Stage 4 archetype; else propose via Stage 4 heuristic.
    Swap growth drivers for economics drivers; keep PRIMARY + traits.
    """
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
        base.provenance = "stage4_heuristic_via_stage5"
    else:
        if force_primary and force_primary in PRIMARY_ARCHETYPES:
            base.primary_archetype = force_primary
            base.primary_label = PRIMARY_ARCHETYPES[force_primary]
            base.provenance = "forced_primary"
        else:
            base.provenance = base.provenance or "stage4_reuse"

    primary = base.primary_archetype
    base.primary_label = base.primary_label or PRIMARY_ARCHETYPES.get(primary, "")
    base.model_specific_drivers = economics_drivers_for(primary, base.secondary_traits)
    slot = MODEL_SLOT_BY_ARCHETYPE.get(primary)
    if slot and slot != "explicit_or_not_applicable":
        base.model_slot = slot
        base.model_slot_status = "set"
    else:
        base.model_slot = slot
        base.model_slot_status = "NOT_APPLICABLE"

    if not base.why:
        base.why = (
            f"PRIMARY={primary} ({base.primary_label}); economics drivers="
            f"{[d['id'] for d in base.model_specific_drivers]}; Stage 4 reuse preferred"
        )
    else:
        base.why = (
            f"{base.why} | Stage 5 economics drivers="
            f"{[d['id'] for d in base.model_specific_drivers]}"
        )
    return base
