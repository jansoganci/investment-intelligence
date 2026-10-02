"""ADHD markdown renderer for Stage 4 — Plan §15 template. No color words, no numeric pass/fail."""
from __future__ import annotations

from ..models import Stage4Report


def render_stage4_markdown(report: Stage4Report) -> str:
    periods = ", ".join(
        f"{p.get('period_key')}@{p.get('version_id')}" for p in report.periods_used
    ) or "(none)"
    sources = ", ".join(report.sources) if report.sources else "(none listed)"

    def bullets(items: list[str], empty: str = "(none)") -> list[str]:
        if not items:
            return [f"- {empty}"]
        return [f"- {x}" for x in items]

    lines = [
        f"# Stage 4 — Growth Quality / Runway — {report.ticker}",
        f"Date: {report.date}",
        f"Normalized versions used: {periods}",
        f"Stage 1 thesis pointer: coherence={report.thesis_coherence}",
        f"Sources: {sources}",
        "",
        "## Outcome",
        f"**{report.process_outcome}**",
        "(Carry-forward growth-quality concerns for final FA — Stage 4 does not alone terminate later stages)",
        f"terminates_later_stages: {report.terminates_later_stages}",
        "",
        "## Why",
        *bullets(report.why_bullets),
        "",
        "## Growth observed",
        *bullets(report.growth_observed_bullets),
        "",
        "## Decomposition",
        *bullets(report.decomposition_bullets),
        "",
        "## Runway",
        *bullets(report.runway_bullets),
        "",
        "## Thesis link (Gate 2 / G2-M4)",
        *bullets(report.thesis_link_bullets),
        "",
        "## False-positive watches",
    ]
    if report.false_positive_tags:
        for t in report.false_positive_tags:
            lines.append(
                f"- {t.get('id')}: {t.get('description')} — severity={t.get('severity')}; "
                f"why={t.get('why')}; counterexample={t.get('counterexample')}"
            )
    else:
        lines.append("- (none tagged)")

    lines += ["", "## Benchmark Layer (evidence — not a gate)"]
    if report.archetype:
        a = report.archetype
        lines += [
            f"- PRIMARY_ARCHETYPE: {a.primary_archetype} ({a.primary_label})",
            f"- SECONDARY_TRAITS: {a.secondary_traits}",
            f"- Model-specific drivers: {[d.get('id') for d in a.model_specific_drivers]}",
            f"- Model slot / status: {a.model_slot} / {a.model_slot_status}",
            f"- Classification: {a.classification_path} (confidence={a.confidence})",
            f"- WHY: {a.why}",
        ]
    lines.append(f"- Context tags: {report.context_tags or '(none)'} "
                 "(NOT process outcomes; MATURE_FRANCHISE_OK ≠ buy signal)")
    for b in report.benchmark_results:
        lines.append(f"- {b.dimension_id} **{b.label}**: {b.why}")

    lines += [
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
        "## Carry into final FA",
        *bullets(report.carry_forward_concerns, empty="(none listed)"),
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
        "_No RED/ORANGE/GREEN. No numeric investment thresholds or pass/fail bars. "
        "No scores / blended scores / universal CAGR hurdles. NC* NOT LOCKED. "
        "Benchmark ≠ hard gate. No label-count→outcome. No LLM arithmetic. "
        "No Stage 5/6/valuation/BUY-SELL/R-O-G. FI out of scope. "
        "Stage 4 does not alone mechanically terminate later stages._",
        "",
    ]
    return "\n".join(lines)
