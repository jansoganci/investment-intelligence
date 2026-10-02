"""Ingest Stages 1–8 artifacts as hypotheses / soft context for Stage 9.

Consume — do not rewrite. Surface conflicts. Soft-link S8_H9_*.
ER2: Gate2/S1/S5 as hypotheses only — no pricing-power redo / no thesis restatement.
"""
from __future__ import annotations

from typing import Any

from .questions import S8_H9_FORWARDABLE


def _arch_from(artifact: dict[str, Any] | None) -> dict[str, Any] | None:
    if not artifact:
        return None
    a = artifact.get("archetype")
    if isinstance(a, dict) and a.get("primary_archetype"):
        return dict(a)
    return None


def extract_gate2_hypothesis(stage1: dict[str, Any] | None) -> dict[str, Any]:
    """Pull Gate 2 moat / kill-shot / monitoring as *hypothesis* only — do not restate thesis as S9 deliverable."""
    out: dict[str, Any] = {
        "advantage_type": None,
        "advantage_evidence": None,
        "kill_shot_primary": None,
        "kill_shot_secondary": None,
        "monitoring_variables": [],
        "industry_drivers_sketch": None,
        "one_sentence_pointer": None,  # pointer only — not a Stage 9 restatement
        "present": False,
    }
    if not stage1:
        return out
    th = stage1.get("thesis") or {}
    if not isinstance(th, dict):
        return out
    out["advantage_type"] = th.get("advantage_type")
    out["advantage_evidence"] = th.get("advantage_evidence")
    out["kill_shot_primary"] = th.get("kill_shot_primary")
    out["kill_shot_secondary"] = th.get("kill_shot_secondary")
    monitors = th.get("monitoring_variables") or th.get("monitors") or []
    if isinstance(monitors, str):
        monitors = [monitors]
    out["monitoring_variables"] = [str(m) for m in monitors if m]
    out["industry_drivers_sketch"] = th.get("industry_drivers") or th.get(
        "industry_structure_sketch"
    )
    # Keep pointer for conflict checks — evaluate must NOT emit as Stage 9 thesis prose
    out["one_sentence_pointer"] = th.get("one_sentence")
    out["present"] = bool(
        out["advantage_type"]
        or out["kill_shot_primary"]
        or out["kill_shot_secondary"]
        or out["monitoring_variables"]
    )
    return out


def extract_s5_durability_hypothesis(stage5: dict[str, Any] | None) -> dict[str, Any]:
    """Soft-consume Stage 5 returns/durability as hypothesis support — NEVER redo pricing power."""
    out: dict[str, Any] = {
        "process_outcome": None,
        "pricing_power_pointer": None,  # pointer only — forbidden to re-analyze
        "margin_notes_pointer": None,
        "present": False,
        "no_pricing_power_redo": True,
    }
    if not stage5:
        return out
    out["process_outcome"] = stage5.get("process_outcome")
    # Do not copy Stage 5 pricing-power exhibits into Stage 9 as re-analysis
    out["pricing_power_pointer"] = "consumed_as_hypothesis_only"
    out["margin_notes_pointer"] = "soft_support_only"
    out["present"] = True
    return out


def extract_s8_h9(stage8: dict[str, Any] | None) -> list[str]:
    if not stage8:
        return []
    raw = stage8.get("s8_h9_carries") or []
    return [c for c in raw if c in S8_H9_FORWARDABLE]


def build_prior_handoff(
    *,
    stage1: dict[str, Any] | None = None,
    stage2: dict[str, Any] | None = None,
    stage3: dict[str, Any] | None = None,
    stage4: dict[str, Any] | None = None,
    stage5: dict[str, Any] | None = None,
    stage6: dict[str, Any] | None = None,
    stage7: dict[str, Any] | None = None,
    stage8: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble Stages 1–8 soft pack for Stage 9 evaluate."""
    # Prefer newest archetype provenance
    prior_arch = None
    provenance = None
    for art, tag in (
        (stage8, "stage8_reuse"),
        (stage7, "stage7_reuse"),
        (stage6, "stage6_reuse"),
        (stage5, "stage5_reuse"),
        (stage4, "stage4_reuse"),
    ):
        a = _arch_from(art)
        if a:
            prior_arch = a
            prior_arch["provenance"] = a.get("provenance") or tag
            provenance = prior_arch["provenance"]
            break

    s6_flags = []
    if stage6:
        s6_flags = list(stage6.get("stage7_handoff_flags") or [])

    conflicts: list[str] = []
    # Soft conflict surface: Stage 8 REVIEW + Stage 6 REVIEW with opposing archetypes — note only
    outcomes = {
        "s1": (stage1 or {}).get("process_outcome") if stage1 else None,
        "s4": (stage4 or {}).get("process_outcome") if stage4 else None,
        "s5": (stage5 or {}).get("process_outcome") if stage5 else None,
        "s6": (stage6 or {}).get("process_outcome") if stage6 else None,
        "s7": (stage7 or {}).get("process_outcome") if stage7 else None,
        "s8": (stage8 or {}).get("process_outcome") if stage8 else None,
    }

    return {
        "gate2_hypothesis": extract_gate2_hypothesis(stage1),
        "s5_durability_hypothesis": extract_s5_durability_hypothesis(stage5),
        "prior_archetype": prior_arch,
        "archetype_provenance": provenance,
        "primary_archetype": (prior_arch or {}).get("primary_archetype"),
        "secondary_traits": list((prior_arch or {}).get("secondary_traits") or []),
        "s6_handoff_flags": s6_flags,
        "s8_h9_carries": extract_s8_h9(stage8),
        "s8_expectations_label": (stage8 or {}).get("expectations_label") if stage8 else None,
        "s8_uncertainty_label": (stage8 or {}).get("uncertainty_label") if stage8 else None,
        "prior_outcomes": outcomes,
        "stage2_present": bool(stage2),
        "stage3_present": bool(stage3),
        "conflicts_seed": conflicts,
        "no_rewrite_s1_8": True,
        "no_stage5_pricing_power_redo": True,
        "no_stage1_thesis_restatement": True,
        "no_stage8_valuation_redo": True,
    }


__all__ = [
    "build_prior_handoff",
    "extract_gate2_hypothesis",
    "extract_s5_durability_hypothesis",
    "extract_s8_h9",
]
