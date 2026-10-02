"""ADHD markdown renderer for Stage 7 — Plan §0.K 8-block dashboard. No colors/scores."""
from __future__ import annotations

from ..models import Stage7Report


def render_stage7_markdown(report: Stage7Report) -> str:
    periods = ", ".join(
        f"{p.get('period_key')}@{p.get('version_id')}" for p in report.periods_used
    ) or "(none)"
    sources = ", ".join(report.sources) if report.sources else "(none listed)"

    def bullets(items: list[str], empty: str = "(none)") -> list[str]:
        if not items:
            return [f"- {empty}"]
        return [f"- {x}" for x in items]

    lines = [
        f"# Stage 7 — Management / Capital Allocation — {report.ticker}",
        f"Date: {report.date}",
        f"Normalized versions used: {periods}",
        f"Stage 1 thesis pointer: coherence={report.thesis_coherence}",
        f"Sources: {sources}",
        "",
        "## Outcome",
        f"**{report.process_outcome}**",
        "(Carry-forward allocation/governance concerns for final FA / Stage 8 — "
        "Stage 7 does not alone terminate later stages)",
        f"terminates_later_stages: {report.terminates_later_stages}",
        f"alignment_label: {report.alignment_label}",
        f"dividend_policy_label: {report.dividend_policy_label}",
        f"debt_motive_tags: {report.debt_motive_tags}",
        f"a7_mg3_depth_required: {report.a7_mg3_depth_required}",
        "",
        "## Why",
        *bullets(report.why_bullets),
        "",
        "## Dashboard 1 — Stated vs revealed allocation hierarchy + cash-use composition",
        *bullets(report.hierarchy_bullets),
        "",
        "## Dashboard 2 — Stage 6 handoff flags (S6_H7_*) + allocation implication notes",
        *bullets(report.s6_handoff_bullets),
        f"- flags_consumed: {report.s6_handoff_flags_consumed or '(none)'}",
        "",
        "## Dashboard 3 — M&A process / accountability exhibit",
        *bullets(report.ma_process_bullets),
        "",
        "## Dashboard 4 — Distributions (buybacks + dividends) + net share / SBC honesty",
        *bullets(report.distribution_bullets),
        "",
        "## Dashboard 5 — Incentives snapshot (metrics, dilution, ownership guidelines)",
        *bullets(report.incentive_bullets),
        "",
        "## Dashboard 6 — Communication & execution (FACT/GUIDANCE/CLAIM/INFERENCE)",
        *bullets(report.communication_execution_bullets),
        "",
        "## Dashboard 7 — FP-M tags + governance/related-party + succession (MG9)",
    ]
    if report.false_positive_tags:
        for t in report.false_positive_tags:
            lines.append(
                f"- FP {t.get('id')}: {t.get('description')} — severity={t.get('severity')}; "
                f"why={t.get('why')}; counterexample={t.get('counterexample')}"
            )
    else:
        lines.append("- FP watches: (none tagged)")
    lines += bullets(report.fp_gov_succession_bullets, empty="(no additional gov/succession notes)")

    lines += ["", "## Dashboard 8 — Benchmark labels + WHY (MG lenses) + archetype + outcome + carries"]
    if report.archetype:
        a = report.archetype
        lines += [
            f"- PRIMARY_ARCHETYPE: {a.primary_archetype} ({a.primary_label})",
            f"- SECONDARY_TRAITS: {a.secondary_traits}",
            f"- Allocation emphasis: {[d.get('id') for d in a.model_specific_drivers]}",
            f"- Model slot / status: {a.model_slot} / {a.model_slot_status}",
            f"- Classification: {a.classification_path} (confidence={a.confidence}; provenance={a.provenance})",
            f"- WHY: {a.why}",
        ]
    for b in report.benchmark_results:
        lines.append(f"- {b.dimension_id} **{b.label}**: {b.why}")
    lines += [
        f"- thesis_coherence: {report.thesis_coherence}",
        f"- process_outcome: {report.process_outcome}",
        *bullets(report.carry_forward_concerns, empty="(none listed)"),
        "",
        "## MG lenses (evidence, not scored average)",
    ]
    for mg in report.mg_lenses:
        lines.append(
            f"- {mg.lens_id} {mg.lens_name}: {mg.summary} | WHY: {mg.why} | "
            f"labels={mg.labels} | S6_consumed={mg.s6_flags_consumed}"
        )

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
            for f in report.semantic.findings[:24]:
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
        "_No RED/ORANGE/GREEN. No scores / averaged MG score / numeric pay/buyback/ownership gates. "
        "Benchmark ≠ hard gate. Method E. No label-count→outcome. "
        "No ROIC/ROIIC/WACC recompute (Stage 6 owns returns math). "
        "S6_H7_* consumed factually only — no mechanical guilt conversion. "
        "No ISS/Glass Lewis production gates. No Stage 8 valuation / BUY-SELL. "
        "FI out of scope. Stage 7 does not alone mechanically terminate later stages. "
        "FACT/GUIDANCE/MANAGEMENT_CLAIM/SYSTEM_INFERENCE taxonomy mandatory. "
        "FP-M flags are flags-not-auto-fails._",
        "",
    ]
    return "\n".join(lines)
