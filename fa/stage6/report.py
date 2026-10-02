"""ADHD markdown renderer for Stage 6 — Plan §0.M 9-item dashboard. No color words, no thresholds."""
from __future__ import annotations

from ..models import Stage6Report


def render_stage6_markdown(report: Stage6Report) -> str:
    periods = ", ".join(
        f"{p.get('period_key')}@{p.get('version_id')}" for p in report.periods_used
    ) or "(none)"
    sources = ", ".join(report.sources) if report.sources else "(none listed)"

    def bullets(items: list[str], empty: str = "(none)") -> list[str]:
        if not items:
            return [f"- {empty}"]
        return [f"- {x}" for x in items]

    lines = [
        f"# Stage 6 — ROIC / Reinvestment — {report.ticker}",
        f"Date: {report.date}",
        f"Normalized versions used: {periods}",
        f"Stage 1 thesis pointer: coherence={report.thesis_coherence}",
        f"Sources: {sources}",
        "",
        "## Outcome",
        f"**{report.process_outcome}**",
        "(Carry-forward capital concerns for final FA / Stage 7 — Stage 6 does not alone terminate later stages)",
        f"terminates_later_stages: {report.terminates_later_stages}",
        f"d10_elevated: {report.d10_elevated}",
        f"runway_label: {report.runway_label}",
        "",
        "## Why",
        *bullets(report.why_bullets),
        "",
        "## Dashboard 1 — ROIC dual view (acquisition-inclusive PRIMARY + tangible companion)",
        *bullets(report.dual_roic_bullets),
        "",
        "## Dashboard 2 — Incremental ROIC exhibit + meaning class (1Y / 3Y primary / 5Y)",
        *bullets(report.incremental_roic_bullets),
        "",
        "## Dashboard 3 — Reinvestment composition",
        *bullets(report.reinvestment_composition_bullets),
        "",
        "## Dashboard 4 — Reinvestment runway label",
        *bullets(report.runway_bullets),
        "",
        "## Dashboard 5 — CapEx productivity evidence notes",
        *bullets(report.capex_productivity_bullets),
        "",
        "## Dashboard 6 — WC mechanism notes",
        *bullets(report.wc_mechanism_bullets),
        "",
        "## Dashboard 7 — FP-R tags + accounting-distortion flags",
    ]
    if report.false_positive_tags:
        for t in report.false_positive_tags:
            lines.append(
                f"- FP {t.get('id')}: {t.get('description')} — severity={t.get('severity')}; "
                f"why={t.get('why')}; counterexample={t.get('counterexample')}"
            )
    else:
        lines.append("- FP watches: (none tagged)")

    lines += ["", "## Dashboard 8 — Benchmark labels + WHY (RC1–RC8) + archetype frame"]
    if report.archetype:
        a = report.archetype
        lines += [
            f"- PRIMARY_ARCHETYPE: {a.primary_archetype} ({a.primary_label})",
            f"- SECONDARY_TRAITS: {a.secondary_traits}",
            f"- Capital drivers: {[d.get('id') for d in a.model_specific_drivers]}",
            f"- Model slot / status: {a.model_slot} / {a.model_slot_status}",
            f"- Classification: {a.classification_path} (confidence={a.confidence}; provenance={a.provenance})",
            f"- WHY: {a.why}",
        ]
    for b in report.benchmark_results:
        lines.append(f"- {b.dimension_id} **{b.label}**: {b.why}")

    lines += [
        "",
        "## Dashboard 9 — Thesis coherence + Stage 7 handoff flags + process outcome",
        f"- thesis_coherence: {report.thesis_coherence}",
        f"- process_outcome: {report.process_outcome}",
        f"- S6_H7 flags: {report.stage7_handoff_flags or '(none)'}",
        *bullets(report.carry_forward_concerns, empty="(none listed)"),
        "",
        "## What is strong",
        *bullets(report.what_is_strong, empty="(none listed)"),
        "",
        "## What can break",
        *bullets(report.what_can_break),
        "",
        "## Monitors",
        *bullets(report.monitors, empty="(none)"),
        "",
        "## Missing / ambiguous",
        *bullets(report.missing_ambiguous, empty="(none listed)"),
        "",
        "## Question spine (status)",
    ]
    for qa in report.question_answers:
        tag = "MUST" if qa.must else "SHOULD"
        lines.append(f"- [{tag}] {qa.question_id} ({qa.status}): {qa.answer_summary}")

    if report.semantic:
        lines += [
            "",
            "## Semantic review",
            f"- source: {report.semantic.review_source}; filled={report.semantic.filled}",
            f"- maint_capex_status: {report.semantic.maint_capex_status}",
        ]
        if report.semantic.findings:
            lines.append("- findings:")
            for f in report.semantic.findings:
                lines.append(
                    f"  - {f.topic}: kind={f.evidence_kind}; judgment={f.materiality_judgment}; "
                    f"escalate={f.escalate_to_human}; dim={f.dimension}; cite={f.citation}"
                )

    if report.calc and report.calc.null_reasons:
        lines += ["", "## Calc null reasons"]
        for k, v in report.calc.null_reasons.items():
            lines.append(f"- {k}: {v}")

    if report.refuse_reason:
        lines += ["", "## Refuse reason", report.refuse_reason]

    lines += [
        "",
        "## Sources",
        f"- {sources}",
        f"- Period versions: {periods}",
        "",
        "---",
        "_No RED/ORANGE/GREEN. No numeric ROIC/ROIIC/WACC thresholds as decisions. "
        "No scores / blended capital scores / universal ROIC hurdles. "
        "Benchmark ≠ hard gate. Method E. No label-count→outcome. "
        "Incremental ROIC ≠ Stage 5 IOM. No forced maint CapEx. "
        "No LLM arithmetic. Tangible companion ≠ M&A success. "
        "No Stage 7 management grade / valuation / BUY-SELL / R-O-G. FI out of scope. "
        "Stage 6 does not alone mechanically terminate later stages. "
        "S6_H7_* are factual handoff flags only._",
        "",
    ]
    return "\n".join(lines)
