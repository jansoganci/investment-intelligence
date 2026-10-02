"""ADHD markdown renderer for Stage 5 — Plan §0.J dashboard. No color words, no numeric bands."""
from __future__ import annotations

from ..models import Stage5Report


def render_stage5_markdown(report: Stage5Report) -> str:
    periods = ", ".join(
        f"{p.get('period_key')}@{p.get('version_id')}" for p in report.periods_used
    ) or "(none)"
    sources = ", ".join(report.sources) if report.sources else "(none listed)"

    def bullets(items: list[str], empty: str = "(none)") -> list[str]:
        if not items:
            return [f"- {empty}"]
        return [f"- {x}" for x in items]

    lines = [
        f"# Stage 5 — Margins / Business Economics — {report.ticker}",
        f"Date: {report.date}",
        f"Normalized versions used: {periods}",
        f"Stage 1 thesis pointer: coherence={report.thesis_coherence}",
        f"Sources: {sources}",
        "",
        "## Outcome",
        f"**{report.process_outcome}**",
        "(Carry-forward economics concerns for final FA / Stage 6 — Stage 5 does not alone terminate later stages)",
        f"terminates_later_stages: {report.terminates_later_stages}",
        "",
        "## Why",
        *bullets(report.why_bullets),
        "",
        "## Dashboard 1 — Margin structure exhibit",
        *bullets(report.margin_structure_bullets),
        "",
        "## Dashboard 2 — Decomposition + pricing/cost evidence (BE2–BE4)",
        *bullets(report.decomposition_bullets),
        *bullets(report.pricing_cost_bullets),
        "",
        "## Dashboard 3 — Archetype + reference frame",
    ]
    if report.archetype:
        a = report.archetype
        lines += [
            f"- PRIMARY_ARCHETYPE: {a.primary_archetype} ({a.primary_label})",
            f"- SECONDARY_TRAITS: {a.secondary_traits}",
            f"- Economics drivers: {[d.get('id') for d in a.model_specific_drivers]}",
            f"- Model slot / status: {a.model_slot} / {a.model_slot_status}",
            f"- Classification: {a.classification_path} (confidence={a.confidence}; provenance={a.provenance})",
            f"- WHY: {a.why}",
        ]
    lines.append(
        f"- Context tags: {report.context_tags or '(none)'} "
        "(NOT process outcomes; SES/mature ≠ buy signal; closed set only)"
    )
    if report.model_specific_slot:
        lines.append(
            f"- Optional model-specific slot: {report.model_specific_slot} "
            f"({report.model_specific_slot_note})"
        )

    lines += ["", "## Dashboard 4 — Benchmark labels + WHY (BE1–BE8; not a gate)"]
    for b in report.benchmark_results:
        lines.append(f"- {b.dimension_id} **{b.label}**: {b.why}")

    lines += [
        "",
        "## Dashboard 5 — Durability + thesis link + FP watches",
        *bullets(report.durability_bullets),
        *bullets(report.thesis_link_bullets),
    ]
    if report.false_positive_tags:
        for t in report.false_positive_tags:
            lines.append(
                f"- FP {t.get('id')}: {t.get('description')} — severity={t.get('severity')}; "
                f"why={t.get('why')}; counterexample={t.get('counterexample')}"
            )
    else:
        lines.append("- FP watches: (none tagged)")

    lines += [
        "",
        "## Incremental OM exhibits (descriptive; ≠ ROIIC)",
        *bullets(report.incremental_om_bullets),
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
        "## Carry into final FA / Stage 6",
        *bullets(report.carry_forward_concerns, empty="(none listed)"),
        "",
        "## Question spine (status)",
    ]
    for qa in report.question_answers:
        tag = "MUST" if qa.must else "SHOULD"
        lines.append(f"- [{tag}] {qa.question_id} ({qa.status}): {qa.answer_summary}")

    if report.pricing_power:
        lines += [
            "",
            "## Pricing-power posture (evidence-of-claim)",
            f"- posture: {report.pricing_power.posture}",
            f"- why: {report.pricing_power.why}",
        ]

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
        "_No RED/ORANGE/GREEN. No numeric GM/OP/IM bands as decisions. "
        "No scores / blended scores / universal margin hurdles. "
        "Benchmark ≠ hard gate. Method E. No label-count→outcome. No BE9 ROIC. "
        "Incremental OM ≠ ROIIC. No LLM arithmetic. "
        "No Stage 6/valuation/BUY-SELL/R-O-G. FI out of scope. "
        "Stage 5 does not alone mechanically terminate later stages._",
        "",
    ]
    return "\n".join(lines)
