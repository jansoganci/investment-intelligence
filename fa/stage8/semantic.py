"""Stage 8 semantic layer — fixture/heuristic path like Stage 7.

Driver WHY, expectations interpretation, MoS qualitative, FP-V flags,
post-period event notes, FACT vs inference. No LLM required in dry-run.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Stage8SemanticFinding, Stage8SemanticReview


def placeholder_stage8_semantic() -> Stage8SemanticReview:
    return Stage8SemanticReview(review_source="placeholder", filled=False)


def load_stage8_semantic_from_fixture(path: Path) -> Stage8SemanticReview:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    findings = []
    for f in raw.get("findings") or []:
        findings.append(Stage8SemanticFinding(**{k: v for k, v in f.items() if k in Stage8SemanticFinding.__dataclass_fields__}))
    return Stage8SemanticReview(
        findings=findings,
        normalization_notes=raw.get("normalization_notes"),
        driver_why_notes=raw.get("driver_why_notes"),
        expectations_notes=raw.get("expectations_notes"),
        mos_qualitative_notes=raw.get("mos_qualitative_notes"),
        fp_v_notes=raw.get("fp_v_notes"),
        post_period_event_notes=raw.get("post_period_event_notes"),
        conflict_notes=raw.get("conflict_notes"),
        a7_organic_acq_notes=raw.get("a7_organic_acq_notes"),
        checklist_coverage=list(raw.get("checklist_coverage") or []),
        review_source=raw.get("review_source") or "fixture",
        filled=bool(raw.get("filled", True)),
    )


def build_heuristic_semantic(
    *,
    ticker: str,
    primary_archetype: str | None,
    norm: dict[str, Any] | None,
    reverse: dict[str, Any] | None,
    dcf: dict[str, Any] | None,
    staleness: str,
    price_suppressed: bool,
    s6_flags: list[str] | None = None,
    post_period_events: list[str] | None = None,
    conflicts: list[str] | None = None,
) -> Stage8SemanticReview:
    """Deterministic heuristic semantic pack — MODEL_INFERENCE labeled."""
    findings: list[Stage8SemanticFinding] = []
    norm = norm or {}
    reverse = reverse or {}
    dcf = dcf or {}
    s6_flags = s6_flags or []

    findings.append(
        Stage8SemanticFinding(
            topic="freshness",
            evidence_kind="FACT",
            classification="market",
            materiality_judgment="material" if price_suppressed else "watchable",
            materiality_reason=f"staleness={staleness}; suppressed={price_suppressed}",
            dimension="bridge",
            va_lens="VA1",
            excerpt=f"staleness_class={staleness}",
        )
    )

    if norm.get("notes"):
        findings.append(
            Stage8SemanticFinding(
                topic="normalization_base",
                evidence_kind="MODEL_INFERENCE",
                classification="heuristic",
                materiality_judgment="watchable",
                materiality_reason="normalization_uncertainty exposed; no aggressive norm",
                dimension="norm",
                va_lens="VA2",
                excerpt="; ".join(norm.get("notes") or [])[:500],
            )
        )

    if primary_archetype == "A7":
        findings.append(
            Stage8SemanticFinding(
                topic="a7_organic_vs_acq",
                evidence_kind="MODEL_INFERENCE",
                classification="heuristic",
                materiality_judgment="material",
                materiality_reason="Recurring M&A = reinvestment; no free-organic acquired growth",
                dimension="norm",
                va_lens="VA2",
                excerpt=(
                    "A7 dual exhibits: organic cash base vs acquisition reinvestment; "
                    f"S6 flags={s6_flags}"
                ),
            )
        )

    if reverse.get("expectations_label"):
        findings.append(
            Stage8SemanticFinding(
                topic="embedded_expectations",
                evidence_kind="MODEL_INFERENCE",
                classification="heuristic",
                materiality_judgment="watchable",
                materiality_reason=reverse.get("expectations_why") or "",
                dimension="reverse",
                va_lens="VA4",
                excerpt=f"expectations={reverse.get('expectations_label')}",
            )
        )

    if dcf.get("dual_terminal_note"):
        findings.append(
            Stage8SemanticFinding(
                topic="dual_terminal_cross_checks",
                evidence_kind="MODEL_INFERENCE",
                classification="heuristic",
                materiality_judgment="watchable",
                materiality_reason="Dual terminals never averaged",
                dimension="dcf",
                va_lens="VA3",
                excerpt=str(dcf.get("dual_terminal_note"))[:500],
            )
        )

    for ev in post_period_events or []:
        findings.append(
            Stage8SemanticFinding(
                topic="post_period_event",
                evidence_kind="COMPANY_EXPLANATION",
                classification="8k_or_note",
                materiality_judgment="material",
                materiality_reason="Post-period material event vs filing-period CS",
                dimension="bridge",
                va_lens="VA1",
                excerpt=str(ev)[:400],
            )
        )

    for c in conflicts or []:
        findings.append(
            Stage8SemanticFinding(
                topic="s1_7_conflict",
                evidence_kind="MODEL_INFERENCE",
                classification="handoff",
                materiality_judgment="material",
                materiality_reason="Surface conflict — no silent override of S1–7",
                dimension="conflict",
                excerpt=str(c)[:400],
            )
        )

    a7_notes = None
    if primary_archetype == "A7":
        org = norm.get("organic_exhibit") or {}
        acq = norm.get("acq_exhibit") or {}
        a7_notes = (
            f"organic={org.get('note')}; acq={acq.get('note')}; "
            f"recurring_ma={acq.get('recurring_ma_as_reinvestment')}"
        )

    mos_notes = (
        "MoS = range position + scenario spread + qualitative posture — "
        "no universal MoS% pass/fail; descriptive upside/downside only when shown."
    )
    if price_suppressed:
        mos_notes = (
            "Price-sensitive MoS suppressed due to freshness/currency failure — "
            "exception queue; no silent MoS-as-if-fresh."
        )

    return Stage8SemanticReview(
        findings=findings,
        normalization_notes="; ".join(norm.get("notes") or []) or None,
        driver_why_notes=(
            dcf.get("growth_note")
            if dcf
            else "Drivers grounded thinly in S3–6 cash/growth scale — no oversized forecast engine"
        ),
        expectations_notes=reverse.get("expectations_why") if reverse else None,
        mos_qualitative_notes=mos_notes,
        fp_v_notes="FP-V flags are flags-not-auto-fails; no FP score; no count→outcome",
        post_period_event_notes="; ".join(post_period_events or []) or None,
        conflict_notes="; ".join(conflicts or []) or None,
        a7_organic_acq_notes=a7_notes,
        checklist_coverage=[
            "freshness",
            "normalization",
            "iv_range",
            "reverse_dcf",
            "mos",
            "uncertainty",
        ],
        review_source="heuristic",
        filled=True,
    )


def semantic_text_blob(semantic: Stage8SemanticReview | None) -> str:
    if not semantic:
        return ""
    parts = [
        semantic.normalization_notes,
        semantic.driver_why_notes,
        semantic.expectations_notes,
        semantic.mos_qualitative_notes,
        semantic.a7_organic_acq_notes,
        semantic.conflict_notes,
        semantic.post_period_event_notes,
    ]
    return " ".join(p for p in parts if p)
