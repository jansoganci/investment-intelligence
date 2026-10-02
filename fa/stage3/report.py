"""ADHD markdown renderer for Stage 3 — Plan §10 template. No color words, no numeric pass/fail."""
from __future__ import annotations

from ..models import Stage3Report


def render_stage3_markdown(report: Stage3Report) -> str:
    periods = ", ".join(
        f"{p.get('period_key')}@{p.get('version_id')}" for p in report.periods_used
    ) or "(none)"
    sources = ", ".join(report.sources) if report.sources else "(none listed)"

    def bullets(items: list[str], empty: str = "(none)") -> list[str]:
        if not items:
            return [f"- {empty}"]
        return [f"- {x}" for x in items]

    lines = [
        f"# Stage 3 — Cash Generation — {report.ticker}",
        f"Date: {report.date}",
        f"Periods used: {periods}",
        f"Sources: {sources}",
        "",
        "## Outcome",
        f"**{report.process_outcome}**",
        "(Carry-forward cash concerns for final FA — Stage 3 does not alone terminate later stages)",
        f"terminates_later_stages: {report.terminates_later_stages}",
        "",
        "## Why",
        *bullets(report.why_bullets),
        "",
        "## Carry-forward concerns (final FA)",
        *bullets(report.carry_forward_concerns, empty="(none listed)"),
        "",
        "## Cash conversion",
        *bullets(report.cash_conversion_bullets),
        "",
        "## Working capital",
        *bullets(report.working_capital_bullets),
        "",
        "## CapEx / reinvestment reality",
        *bullets(report.capex_bullets),
        "",
        "## Cash quality warnings",
        *bullets(report.cash_quality_warnings, empty="(none)"),
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
            f"- maintenance_capex_status: **{report.semantic.maintenance_capex_status}**",
        ]
        if report.semantic.maintenance_capex_evidence:
            lines.append(f"- maintenance evidence: {report.semantic.maintenance_capex_evidence}")
        if report.semantic.findings:
            lines.append("- findings:")
            for f in report.semantic.findings:
                lines.append(
                    f"  - {f.topic}: judgment={f.materiality_judgment}; "
                    f"escalate={f.escalate_to_human}; cite={f.citation}; "
                    f"reason={f.materiality_reason}"
                )

    if report.calc and (report.calc.metrics or {}).get("latest_cfs_reconciliation"):
        b = report.calc.metrics["latest_cfs_reconciliation"]
        lines += [
            "",
            "## Official CFS reconciliation (deterministic)",
            f"- period: {b.get('period_key')} status=**{b.get('status')}**",
            f"- NI_cfs_basis={b.get('net_income_cfs_basis')} ({b.get('net_income_basis')}); "
            f"attributable={b.get('net_income_attributable')}; consolidated={b.get('net_income_consolidated')}",
            f"- reported_OCF={b.get('reported_ocf')}; reconstructed_OCF={b.get('reconstructed_ocf')}; "
            f"unexplained_residual={b.get('unexplained_residual')}",
            f"- interpretation: {b.get('interpretation_categories')}",
            f"- notes: {b.get('notes')}",
        ]
        for c in b.get("components") or []:
            lines.append(
                f"  - FACT {c.get('bucket')}={c.get('amount')} "
                f"(raw={c.get('raw_amount')}×{c.get('sign')}) nature={c.get('nature')}"
            )
        for item in b.get("company_specific_cfs_adjustments") or []:
            lines.append(
                f"  - company_specific {item.get('label')}: amount={item.get('amount')} "
                f"include={item.get('include_in_sum')} src={item.get('tag_or_source')}"
            )
        for s in b.get("semantic_explanations") or []:
            lines.append(
                f"  - semantic {s.get('topic')} kind={s.get('evidence_kind')} "
                f"cite={s.get('citation')} excerpt={(s.get('excerpt') or '')[:160]}"
            )
        for u in (b.get("factual_vs_uncertain") or {}).get("uncertain") or []:
            lines.append(f"  - uncertain: {u}")

    if report.calc and (report.calc.metrics or {}).get("latest_ocf_ni_bridge"):
        b = report.calc.metrics["latest_ocf_ni_bridge"]
        lines += [
            "",
            "## OCF vs NI bridge — legacy proxy (deterministic)",
            f"- period: {b.get('period_key')} gap_ocf_minus_ni={b.get('gap_ocf_minus_ni')}",
            f"- cfs_reconciliation_status: {b.get('cfs_reconciliation_status')}",
            f"- nature_tags: {b.get('nature_tags')}",
            f"- explained_proxy: {b.get('explained_proxy')}; residual_after_proxy: {b.get('residual_after_proxy')}",
            f"- notes: {b.get('notes')}",
        ]
        for c in b.get("components") or []:
            lines.append(
                f"  - FACT {c.get('field')}={c.get('amount')} role={c.get('role')} nature={c.get('nature')}"
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
        "No LLM arithmetic. Maintenance CapEx UNKNOWN unless disclosed evidence. "
        "FI out of scope. Independent of Stage 4. "
        "Stage 3 does not alone mechanically terminate later stages._",
        "",
    ]
    return "\n".join(lines)
