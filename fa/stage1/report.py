"""ADHD markdown renderer for Stage 1 — no color words, no valuation, no numeric pass/fail."""
from __future__ import annotations

from ..models import Stage1Report

_OUTCOME_LABELS = [
    "Pass to financial stages (Stage 2+)",
    "TOO HARD — circle of competence incomplete (core explain)",
    "TOO HARD — no falsifiers",
    "TOO HARD — monitoring commitment absent",
    "TOO HARD — unit of analysis out of scope for v1 OpCo path",
    "REVIEW REQUIRED — Gate 0 incomplete",
    "REVIEW REQUIRED — ban-list one-liner",
    "REVIEW REQUIRED — thesis one-sentence missing",
    "REVIEW REQUIRED — kill-shots empty",
    "REVIEW REQUIRED — incomplete MUST spine",
    "STOP — no ownership thesis (no durable advantage hypothesis)",
]


def render_stage1_markdown(report: Stage1Report) -> str:
    thesis = report.thesis
    one = (thesis.one_sentence if thesis else "") or "(empty)"

    # Checkbox status after gates 1–2 (research template)
    status_boxes = [
        ("Pass to financial stages", report.process_outcome == "PROCEED"),
        (
            "TOO HARD / REVIEW REQUIRED",
            report.process_outcome in {"TOO_HARD", "REVIEW_REQUIRED"},
        ),
        ("No ownership thesis (stop)", report.process_outcome == "STOP_NO_THESIS"),
    ]

    lines = [
        f"# Stage 1 — Gates 0–2 — {report.ticker}",
        f"Date: {report.date}",
        f"Gate 0 class: **{report.gate0_class}**",
        f"Process outcome: **{report.process_outcome}**",
        f"block_stage2: {report.block_stage2}",
        "",
        "## Status after Gates 1–2",
    ]
    for lab, on in status_boxes:
        lines.append(f"- [{'x' if on else ' '}] {lab}")

    lines += [
        "",
        f"## Narrative: {report.narrative_verdict}",
        "",
        "## Ownership thesis — ONE SENTENCE",
        one,
    ]
    if report.ban_list_hits:
        lines.append(f"_Ban-list hits: {report.ban_list_hits}_")

    if thesis:
        lines += [
            "",
            "## Thesis card (summary)",
            f"- Customer job: {thesis.customer_value_job or '(empty)'}",
            f"- Why pay us: {thesis.customer_value_why or '(empty)'}",
            f"- Advantage: {thesis.advantage_type or '(empty)'}",
            f"- Persist: {thesis.advantage_persist or '(empty)'}",
            f"- Runway: {thesis.runway_what or '(empty)'} (confidence={thesis.runway_confidence or 'n/a'})",
            f"- Reinvestment: {thesis.reinvestment_where or '(empty)'}",
            f"- Capital: {thesis.capital_intensity or '(empty)'}",
            f"- Kill-shot primary: {thesis.kill_shot_primary or '(empty)'}",
            f"- Kill-shot secondary: {thesis.kill_shot_secondary or '(empty)'}",
            "- Monitors:",
        ]
        if thesis.monitors:
            for m in thesis.monitors:
                lines.append(f"  - {m}")
        else:
            lines.append("  - (none)")

    lines += ["", "## Question spine (status)"]
    for qa in report.question_answers:
        if qa.question_id.startswith("G1-L"):
            tag = "LEARN"
        elif qa.must:
            tag = "MUST"
        else:
            tag = "SHOULD"
        lines.append(f"- [{tag}] {qa.question_id} ({qa.status}): {qa.answer_summary}")

    if report.warnings:
        lines += ["", "## Warnings (SHOULD / soft)"]
        for w in report.warnings:
            lines.append(f"- {w}")

    if report.block_reasons:
        lines += ["", "## Block / outcome reasons"]
        for b in report.block_reasons:
            lines.append(f"- {b}")

    lines += [
        "",
        f"## Enough to proceed to Stage 2? {report.enough_to_proceed}",
        report.enough_why,
        "",
        "---",
        "_No RED/ORANGE/GREEN. No valuation. No numeric investment thresholds. "
        "LEARNABLE never blockers. Stage 2 refused unless PROCEED. No Stage 3._",
        "",
    ]
    return "\n".join(lines)
