"""Final FA Synthesis evaluate — Plan §0 locked operating model.

Completeness → Stage1 map → contradiction ≤5 → hard constraints →
soft challenges → human queue 0–5 → color/state.

Does NOT rewrite Stages 1–9. Does NOT average / score / BUY-SELL.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import (
    CORE_REQUIRED_STAGES,
    MAX_CONFLICTS,
    MAX_HUMAN_QUEUE,
    MAX_WHY,
    S6_H7_LOCKED,
    S7_H8_LOCKED,
    S8_H9_LOCKED,
    S9_HFA_LOCKED,
    SOFT_IF_MISSING_STAGES,
    SPINE_STAGE,
    BreakerRef,
    ConflictRecord,
    FinalFaSynthesis,
    FinalThesisBlock,
    HumanItem,
    ProvenanceBlock,
    ProvenancedBullet,
)

_CARRY_RE = re.compile(r"\b(S6_H7_[A-Z0-9_]+|S7_H8_[A-Z0-9_]+|S8_H9_[A-Z0-9_]+|S9_HFA_[A-Z0-9_]+)\b")


def _outcome(art: dict[str, Any] | None) -> str:
    if art is None:
        return "missing"
    return str(art.get("process_outcome") or "missing")


def _stage_key(n: int) -> str:
    return f"s{n}"


def extract_carries(stages: dict[int, dict[str, Any] | None]) -> dict[str, list[str]]:
    """Consume locked carry IDs from stage CURRENT artifacts only."""
    s6 = stages.get(6) or {}
    s7 = stages.get(7) or {}
    s8 = stages.get(8) or {}
    s9 = stages.get(9) or {}

    s6_h7: list[str] = []
    raw6 = list(s6.get("stage7_handoff_flags") or [])
    raw6 += list(s7.get("s6_handoff_flags_consumed") or [])
    raw6 += list(s8.get("s6_handoff_flags_consumed") or [])
    for item in raw6:
        if isinstance(item, str) and item in S6_H7_LOCKED:
            s6_h7.append(item)
    # also scan carry_forward text for locked IDs
    for art in (s6, s7, s8):
        for line in art.get("carry_forward_concerns") or []:
            for m in _CARRY_RE.findall(str(line)):
                if m in S6_H7_LOCKED:
                    s6_h7.append(m)

    s7_h8: list[str] = []
    for item in s8.get("s7_h8_carries") or []:
        if item in S7_H8_LOCKED:
            s7_h8.append(item)
    for line in (s7.get("carry_forward_concerns") or []) + (s8.get("carry_forward_concerns") or []):
        for m in _CARRY_RE.findall(str(line)):
            if m in S7_H8_LOCKED:
                s7_h8.append(m)

    s8_h9: list[str] = []
    for item in s8.get("s8_h9_carries") or []:
        if item in S8_H9_LOCKED:
            s8_h9.append(item)
    for item in s9.get("s8_h9_carries_forwarded") or []:
        if item in S8_H9_LOCKED:
            s8_h9.append(item)

    s9_hfa: list[str] = []
    for item in s9.get("s9_hfa_carries") or []:
        if item in S9_HFA_LOCKED:
            s9_hfa.append(item)
    for line in s9.get("carry_forward_concerns") or []:
        for m in _CARRY_RE.findall(str(line)):
            if m in S9_HFA_LOCKED:
                s9_hfa.append(m)

    def _uniq(xs: list[str]) -> list[str]:
        return list(dict.fromkeys(xs))

    return {
        "s6_h7": _uniq(s6_h7),
        "s7_h8": _uniq(s7_h8),
        "s8_h9": _uniq(s8_h9),
        "s9_hfa": _uniq(s9_hfa),
    }


def _active_fact_breakers(s9: dict[str, Any] | None) -> list[BreakerRef]:
    out: list[BreakerRef] = []
    if not s9:
        return out
    for b in s9.get("thesis_breakers") or []:
        if not isinstance(b, dict):
            continue
        out.append(
            BreakerRef(
                breaker_id=str(b.get("breaker_id") or "unknown"),
                source="stage9_er8",
                active_fact=bool(b.get("active_fact")),
                mechanism=b.get("mechanism"),
            )
        )
    return out


def _has_active_fact_breaker(carries: dict[str, list[str]], s9: dict[str, Any] | None) -> bool:
    if "S9_HFA_THESIS_BREAKER_ACTIVE" not in carries.get("s9_hfa", []):
        return False
    for b in _active_fact_breakers(s9):
        if b.active_fact:
            return True
    # Carry present without structured breaker: still treat as FACT-grade hard-review
    # when carry text / concerns explicitly say Active FACT
    if s9:
        for line in s9.get("carry_forward_concerns") or []:
            if "Active FACT breaker" in str(line) or "active_fact=True" in str(line):
                return True
        # If carry is present and any breaker has active_fact, already returned.
        # If carry present but no breaker objects: prefer REVIEW (Plan U4).
        breakers = s9.get("thesis_breakers") or []
        if not breakers:
            return True
        # carry present + breakers all non-active → still REVIEW if carry says THESIS_BREAKER_ACTIVE
        # Plan: S9_HFA_THESIS_BREAKER_ACTIVE + active_fact=True → REVIEW
        # Without active_fact True, soft unless paired with hard criteria.
        return any(bool(b.get("active_fact")) for b in breakers if isinstance(b, dict))
    return True


def build_contradictions(
    stages: dict[int, dict[str, Any] | None],
    carries: dict[str, list[str]],
) -> list[ConflictRecord]:
    """Contradiction engine ≤5 (Plan §0.I)."""
    conflicts: list[ConflictRecord] = []
    s9 = stages.get(9) or {}
    s6 = stages.get(6) or {}
    s7 = stages.get(7) or {}

    # Family 1/2: claim-level / FACT↔FACT from Stage 9 s1_8_conflicts
    for i, c in enumerate(s9.get("s1_8_conflicts") or []):
        text = str(c)
        human = bool(
            re.search(r"FACT\s*(?:↔|vs|vs\.|versus)\s*FACT", text, re.I)
            or "FACT↔FACT" in text
            or "FACT vs FACT" in text.upper()
        )
        conflicts.append(
            ConflictRecord(
                conflict_id=f"C_S9_{i+1}",
                family=2 if human else 1,
                summary=text[:240],
                resolution_action="human_required" if human else "CONFLICT",
                evidence_ptrs=["stage9.s1_8_conflicts"],
                human_required=human,
            )
        )

    # Family 5: later stage stresses earlier (Stage 9 surface)
    for line in s9.get("moat_durability_bullets") or []:
        if "conflict" in str(line).lower() or "stress" in str(line).lower():
            conflicts.append(
                ConflictRecord(
                    conflict_id=f"C_STRESS_{len(conflicts)+1}",
                    family=5,
                    summary=str(line)[:240],
                    resolution_action="record_both_no_silent_override",
                    evidence_ptrs=["stage9.moat_durability"],
                    human_required=False,
                )
            )

    # Family 8: capital opacity vs allocation coexistence
    if "S6_H7_DUAL_VIEW_CONFLICT" in carries.get("s6_h7", []) and stages.get(7):
        conflicts.append(
            ConflictRecord(
                conflict_id="C_CAP_OPACITY_S6_S7",
                family=8,
                summary=(
                    "S6_H7_DUAL_VIEW_CONFLICT coexists with Stage 7 allocation exhibits — "
                    "dual exhibits; not average; soft unless hard criteria"
                ),
                resolution_action="dual_exhibits_soft",
                evidence_ptrs=["stage6.stage7_handoff_flags", "stage7"],
                human_required=False,
            )
        )

    # Family 6: missing stage ≠ assent — recorded via soft chips elsewhere; light conflict note
    for n in SOFT_IF_MISSING_STAGES:
        if stages.get(n) is None:
            conflicts.append(
                ConflictRecord(
                    conflict_id=f"C_MISSING_S{n}",
                    family=6,
                    summary=f"Stage {n} CURRENT missing — missing ≠ assent",
                    resolution_action="missing_ne_assent",
                    evidence_ptrs=[f"stage{n}"],
                    human_required=False,
                )
            )

    # Family 7: valuation demanding ≠ moat falsification
    if "S8_H9_EXPECTATIONS_DEMANDING" in carries.get("s8_h9", []):
        conflicts.append(
            ConflictRecord(
                conflict_id="C_VAL_DEMANDING_NE_MOAT",
                family=7,
                summary=(
                    "S8_H9_EXPECTATIONS_DEMANDING is soft valuation stress — "
                    "≠ moat falsification; challenge not RED"
                ),
                resolution_action="challenge_not_red",
                evidence_ptrs=["stage8.s8_h9_carries"],
                human_required=False,
            )
        )

    # suppress unused locals for lint calm
    _ = (s6, s7)

    return conflicts[:MAX_CONFLICTS]


def _thesis_from_stage1(s1: dict[str, Any] | None) -> FinalThesisBlock:
    th = FinalThesisBlock()
    if not s1:
        return th
    thesis = s1.get("thesis") or {}
    if not isinstance(thesis, dict):
        return th
    th.one_liner = thesis.get("one_sentence") or thesis.get("one_liner")
    th.economic_engine = thesis.get("economic_engine") or thesis.get("how_makes_money")
    th.durable_advantage_hypothesis = thesis.get("advantage_type") or thesis.get(
        "advantage_evidence"
    )
    th.capital_destination_posture = thesis.get("capital_destination") or thesis.get(
        "capital_allocation"
    )
    return th


def _collect_supports(stages: dict[int, dict[str, Any] | None]) -> list[ProvenancedBullet]:
    supports: list[ProvenancedBullet] = []
    for n in range(1, 10):
        art = stages.get(n)
        if not art:
            continue
        for key in ("what_is_strong", "why_bullets"):
            for line in art.get(key) or []:
                text = str(line)
                if not text or text.startswith("Final-FA carry"):
                    continue
                supports.append(
                    ProvenancedBullet(
                        text=text[:300],
                        provenance=[f"stage{n}.{key}"],
                    )
                )
                if len(supports) >= 7:
                    return supports
    return supports


def evaluate_final_fa(
    ticker: str,
    stages: dict[int, dict[str, Any] | None],
    *,
    as_of: str | None = None,
    stage_paths: dict[str, str | None] | None = None,
) -> FinalFaSynthesis:
    """
    Deterministic Final FA synthesis from Stage CURRENT artifacts.

    ``stages`` maps 1..9 → artifact dict or None (missing).
    """
    as_of = as_of or date.today().isoformat()
    stage_paths = stage_paths or {}

    stage_outcomes = {_stage_key(n): _outcome(stages.get(n)) for n in range(1, 10)}
    carries = extract_carries(stages)
    soft_missing = [n for n in SOFT_IF_MISSING_STAGES if stages.get(n) is None]
    soft_chips = [f"S{n}_MISSING" for n in soft_missing]
    orange_ceiling = bool(soft_missing)

    challenges: list[ProvenancedBullet] = []
    unresolved: list[str] = []
    monitors: list[str] = []
    why: list[str] = []
    queue: list[HumanItem] = []
    conflicts = build_contradictions(stages, carries)

    # Soft-missing chips (S2 material soft)
    for chip in soft_chips:
        challenges.append(
            ProvenancedBullet(
                text=f"{chip}: soft-if-missing stage absent — GREEN forbidden; ORANGE max (§0.E)",
                provenance=["completeness"],
                severity_level="S2",
            )
        )
        unresolved.append(chip)

    # --- Completeness / Stage1 spine (Plan §0.E / §0.G) ---
    s1 = stages.get(SPINE_STAGE)
    s1_out = stage_outcomes["s1"]

    final_state: str | None = None

    # Missing required core → INCOMPLETE (never invent; never RED-for-absence)
    missing_core = [n for n in CORE_REQUIRED_STAGES if stages.get(n) is None]
    if s1 is None:
        missing_core = [1] + missing_core

    if missing_core:
        final_state = "INCOMPLETE"
        why.append(
            "INCOMPLETE: required stage CURRENT missing: "
            + ", ".join(f"S{n}" for n in missing_core)
        )
        for n in missing_core:
            unresolved.append(f"S{n}_REQUIRED_MISSING")

    # Required-stage TOO_HARD → Final FA TOO_HARD (not RED)
    if final_state is None:
        too_hard_required = []
        if s1 is not None and s1_out == "TOO_HARD":
            too_hard_required.append(1)
        for n in CORE_REQUIRED_STAGES:
            if stages.get(n) is not None and stage_outcomes[_stage_key(n)] == "TOO_HARD":
                too_hard_required.append(n)
        if too_hard_required:
            final_state = "TOO_HARD"
            why.append(
                "TOO_HARD: required stage unevaluable: "
                + ", ".join(f"S{n}" for n in too_hard_required)
            )

    # Stage 1 outside-color map (don't paint RED)
    if final_state is None and s1 is not None and s1_out != "PROCEED":
        if s1_out == "STOP_NO_THESIS":
            final_state = "STOP_NO_THESIS"
            why.append("Stage 1 STOP_NO_THESIS — no v1 ownership thesis")
        elif s1_out == "REVIEW_REQUIRED":
            final_state = "REVIEW_REQUIRED"
            why.append("Stage 1 REVIEW_REQUIRED — thesis spine blocked")
        elif s1_out == "TOO_HARD":
            final_state = "TOO_HARD"
            why.append("Stage 1 TOO_HARD")
        else:
            # unexpected non-PROCEED → prefer REVIEW over casual RED
            final_state = "REVIEW_REQUIRED"
            why.append(f"Stage 1 process_outcome={s1_out} — prefer REVIEW over casual RED")

    # Soft-missing stage TOO_HARD (not required) → challenge only
    for n in soft_missing:
        pass  # already chipped
    for n in SOFT_IF_MISSING_STAGES:
        if stages.get(n) is not None and stage_outcomes[_stage_key(n)] == "TOO_HARD":
            challenges.append(
                ProvenancedBullet(
                    text=f"Stage {n} TOO_HARD (soft-if-missing) — unevaluable soft lens",
                    provenance=[f"stage{n}"],
                    severity_level="S2",
                )
            )
            orange_ceiling = True

    # --- Hard-review: FACT breaker (Plan U4) ---
    s9 = stages.get(9)
    falsifiers = _active_fact_breakers(s9)
    fact_breaker_active = _has_active_fact_breaker(carries, s9)

    if fact_breaker_active and final_state is None:
        final_state = "REVIEW_REQUIRED"
        why.append(
            "REVIEW_REQUIRED: S9_HFA_THESIS_BREAKER_ACTIVE with active_fact — "
            "FACT breaker until cleared (not auto-RED)"
        )
        queue.append(
            HumanItem(
                id="HR_FACT_BREAKER",
                why_human=(
                    "Clear or confirm-falsify active FACT thesis breaker "
                    "(RED only if human confirms falsify)"
                ),
                evidence_ptrs=["stage9.thesis_breakers", "S9_HFA_THESIS_BREAKER_ACTIVE"],
                decision_options=["clear_breaker", "confirm_falsify_RED", "defer"],
                blocks_color=True,
            )
        )
        challenges.append(
            ProvenancedBullet(
                text="Active FACT thesis breaker — hard-review (S3)",
                provenance=["stage9"],
                evidence_label="FACT",
                severity_level="S3",
            )
        )

    # FACT↔FACT conflicts → REVIEW
    fact_fact = [c for c in conflicts if c.human_required and c.family == 2]
    if fact_fact and final_state is None:
        final_state = "REVIEW_REQUIRED"
        why.append("REVIEW_REQUIRED: unresolved FACT↔FACT contradiction on thesis-critical claim")
        queue.append(
            HumanItem(
                id="HR_FACT_FACT",
                why_human="Resolve FACT↔FACT contradiction before color emission",
                evidence_ptrs=[p for c in fact_fact for p in c.evidence_ptrs],
                decision_options=["prefer_exhibit_a", "prefer_exhibit_b", "defer"],
                blocks_color=True,
            )
        )

    # HE6 candidate without human confirm → REVIEW (prefer REVIEW over casual RED)
    if (
        "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST" in carries.get("s6_h7", [])
        and final_state is None
    ):
        queue.append(
            HumanItem(
                id="HR_HE6",
                why_human=(
                    "HE6 candidate: S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST — "
                    "human confirm hard-elim before RED"
                ),
                evidence_ptrs=["stage6.stage7_handoff_flags"],
                decision_options=["confirm_hard_elim_RED", "downgrade_soft", "defer"],
                blocks_color=True,
            )
        )
        final_state = "REVIEW_REQUIRED"
        why.append(
            "REVIEW_REQUIRED: HE6 candidate needs human confirm — prefer REVIEW over casual RED"
        )
        challenges.append(
            ProvenancedBullet(
                text="S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST — hard-elim candidate (HE6)",
                provenance=["stage6"],
                severity_level="S3",
            )
        )

    # Open blocking queue → force REVIEW if somehow still coloring
    if any(h.blocks_color for h in queue) and final_state in (None, "GREEN", "ORANGE", "RED"):
        final_state = "REVIEW_REQUIRED"
        if not any("blocks_color" in w for w in why):
            why.append("REVIEW_REQUIRED: open blocks_color human queue item")

    # --- Soft challenges assembly ---
    # Stage CONDITIONAL → soft S1
    for n in range(1, 10):
        art = stages.get(n)
        if not art:
            continue
        out = stage_outcomes[_stage_key(n)]
        if out == "CONDITIONAL":
            challenges.append(
                ProvenancedBullet(
                    text=f"Stage {n} CONDITIONAL — soft residual (not auto-RED)",
                    provenance=[f"stage{n}"],
                    severity_level="S1",
                )
            )
        elif out == "REVIEW_REQUIRED" and n != 1:
            # Stage RR alone ≠ Final FA REVIEW — surface as soft unless hard criteria already hit
            challenges.append(
                ProvenancedBullet(
                    text=(
                        f"Stage {n} process REVIEW_REQUIRED — ingest carries/why; "
                        "not auto Final FA REVIEW"
                    ),
                    provenance=[f"stage{n}"],
                    severity_level="S1",
                )
            )
        for line in art.get("what_can_break") or []:
            challenges.append(
                ProvenancedBullet(
                    text=str(line)[:300],
                    provenance=[f"stage{n}.what_can_break"],
                    severity_level="S1",
                )
            )
        for m in art.get("monitors") or []:
            monitors.append(str(m))

    # Soft carries
    for cid in carries.get("s6_h7", []):
        if cid == "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST":
            continue  # already hard-review path
        sev = "S2" if cid in {
            "S6_H7_DUAL_VIEW_CONFLICT",
            "S6_H7_ACQ_RETURN_OPACITY",
            "S6_H7_THESIS_CAPITAL_DESTINATION_TENSION",
        } else "S1"
        challenges.append(
            ProvenancedBullet(
                text=f"Carry {cid}",
                provenance=["stage6"],
                severity_level=sev,  # type: ignore[arg-type]
            )
        )
        if sev == "S2":
            orange_ceiling = True
    for cid in carries.get("s7_h8", []):
        challenges.append(
            ProvenancedBullet(
                text=f"Carry {cid}",
                provenance=["stage7/stage8"],
                severity_level="S1",
            )
        )
    for cid in carries.get("s8_h9", []):
        challenges.append(
            ProvenancedBullet(
                text=f"Carry {cid} — soft valuation stress (≠ RED/SELL)",
                provenance=["stage8"],
                severity_level="S1",
            )
        )
    for cid in carries.get("s9_hfa", []):
        if cid == "S9_HFA_THESIS_BREAKER_ACTIVE":
            continue
        challenges.append(
            ProvenancedBullet(
                text=f"Carry {cid}",
                provenance=["stage9"],
                severity_level="S1",
            )
        )

    # Dedup challenges / monitors
    seen_c: set[str] = set()
    uniq_ch: list[ProvenancedBullet] = []
    for c in challenges:
        if c.text in seen_c:
            continue
        seen_c.add(c.text)
        uniq_ch.append(c)
    challenges = uniq_ch[:40]
    monitors = list(dict.fromkeys(monitors))[:30]
    unresolved = list(dict.fromkeys(unresolved))

    # Material soft S2 (beyond soft-missing) also caps at ORANGE
    if any(c.severity_level == "S2" for c in challenges):
        orange_ceiling = True

    # --- Color decision (only if not already outside) ---
    if final_state is None:
        # Inside color universe — no hard blockers
        if orange_ceiling:
            final_state = "ORANGE"
            why.append(
                "ORANGE: sufficiently complete but soft conditions/gaps block GREEN "
                "(incl. soft-missing and/or material soft carries)"
            )
        else:
            # Soft-only S0/S1 challenges may remain while GREEN
            final_state = "GREEN"
            why.append(
                "GREEN: hard constraints clear; soft challenges documented; "
                "GREEN ≠ BUY; eligible for technical-universe consideration"
            )

    # Cap queue
    queue = queue[:MAX_HUMAN_QUEUE]
    why = why[:MAX_WHY]

    # technical_eligible iff GREEN ∧ no open blocks_color
    open_block = any(h.blocks_color for h in queue)
    technical_eligible = final_state == "GREEN" and not open_block

    # Supports / thesis
    supports = _collect_supports(stages)
    thesis = _thesis_from_stage1(s1)
    thesis.key_supports = [s.text for s in supports[:7]]
    thesis.key_challenges = [c.text for c in challenges[:7]]
    thesis.falsifiers = [
        f"{b.breaker_id}: {b.mechanism or ''}".strip(": ")
        for b in falsifiers
    ][:7]
    thesis.monitors = monitors[:10]
    thesis.unresolved = unresolved[:10]
    thesis.conflicts = [c.summary for c in conflicts][:5]

    if not falsifiers and s1:
        th = s1.get("thesis") or {}
        if isinstance(th, dict):
            for k in ("kill_shot_primary", "kill_shot_secondary"):
                if th.get(k):
                    falsifiers.append(
                        BreakerRef(
                            breaker_id=k,
                            source="gate2",
                            active_fact=False,
                            mechanism=str(th.get(k)),
                        )
                    )

    provenance = ProvenanceBlock(
        stage_versions={
            _stage_key(n): (
                (stages[n] or {}).get("version_id") if stages.get(n) else None
            )
            for n in range(1, 10)
        },
        stage_paths={
            _stage_key(n): stage_paths.get(_stage_key(n))
            or stage_paths.get(f"stage{n}")
            for n in range(1, 10)
        },
        carries_frozen_at=as_of,
    )

    return FinalFaSynthesis(
        ticker=ticker,
        as_of=as_of,
        final_state=final_state,  # type: ignore[arg-type]
        technical_eligible=technical_eligible,
        why_bullets=why,
        supports=supports,
        challenges=challenges,
        unresolved=unresolved,
        conflicts=conflicts,
        human_review_queue=queue,
        thesis=thesis,
        carries_consumed=carries,
        stage_outcomes=stage_outcomes,
        monitors=monitors,
        falsifiers=falsifiers,
        provenance=provenance,
        soft_missing_chips=soft_chips,
        orange_ceiling=orange_ceiling,
    )
