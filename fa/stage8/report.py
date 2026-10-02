"""ADHD markdown renderer for Stage 8 — Plan §0.M 8-block dashboard. No colors/scores/BUY-SELL."""
from __future__ import annotations

from ..models import Stage8Report


def render_stage8_markdown(report: Stage8Report) -> str:
    periods = ", ".join(
        f"{p.get('period_key')}@{p.get('version_id')}" for p in report.periods_used
    ) or "(none)"
    sources = ", ".join(report.sources) if report.sources else "(none listed)"

    def bullets(items: list[str], empty: str = "(none)") -> list[str]:
        if not items:
            return [f"- {empty}"]
        return [f"- {x}" for x in items]

    lines = [
        f"# Stage 8 — Valuation / IV / MoS — {report.ticker}",
        f"Date: {report.date}",
        f"Normalized versions used: {periods}",
        f"Stage 1 thesis pointer: coherence={report.thesis_coherence}",
        f"Sources: {sources}",
        "",
        "## Outcome",
        f"**{report.process_outcome}**",
        "(Carry-forward valuation uncertainty for final FA / Stage 9 notes — "
        "Stage 8 does not alone terminate later stages)",
        f"terminates_later_stages: {report.terminates_later_stages}",
        f"staleness_class: {report.staleness_class}",
        f"expectations_label: {report.expectations_label}",
        f"uncertainty_label: {report.uncertainty_label}",
        f"uncertainty_drivers: {report.uncertainty_drivers}",
        f"discount_class: {report.discount_class}",
        f"price_sensitive_suppressed: {report.price_sensitive_suppressed}",
        f"a7_dual_exhibits: {report.a7_dual_exhibits}",
        "",
        "## Why",
        *bullets(report.why_bullets),
        "",
        "## Dashboard 1 — Market-value bridge + as-of / session-aware freshness",
        *bullets(report.market_bridge_bullets),
        "",
        "## Dashboard 2 — Normalized base + uncertainty + archetype (+ A7 dual when applicable)",
        *bullets(report.normalized_base_bullets),
        "",
        "## Dashboard 3 — IV range (FCFF/OE scenarios) or N/A + WHY",
        *bullets(report.iv_range_bullets),
        f"- dual_terminal_note: {report.dual_terminal_note or '(n/a)'}",
        "",
        "## Dashboard 4 — Reverse DCF / expectations vocabulary + WHY",
        *bullets(report.reverse_dcf_bullets),
        "",
        "## Dashboard 5 — Multiples + own-history context (+ selective peers or N/A)",
        *bullets(report.multiples_bullets),
        "",
        "## Dashboard 6 — Dilution / SBC / capital-structure honesty (Stage 7 consume)",
        *bullets(report.dilution_cs_bullets),
        "",
        "## Dashboard 7 — MoS evidence + uncertainty + FP-V + method disagreement",
    ]
    if report.false_positive_tags:
        for t in report.false_positive_tags:
            lines.append(
                f"- FP {t.get('id')}: {t.get('description')} — severity={t.get('severity')}; "
                f"why={t.get('why')}; counterexample={t.get('counterexample')}"
            )
    else:
        lines.append("- FP watches: (none tagged)")
    lines += bullets(report.mos_uncertainty_bullets, empty="(no MoS/uncertainty notes)")

    lines += [
        "",
        "## Dashboard 8 — VA labels + WHY + S1–7 conflicts + outcome + carries",
    ]
    if report.archetype:
        a = report.archetype
        lines += [
            f"- PRIMARY_ARCHETYPE: {a.primary_archetype} ({a.primary_label})",
            f"- SECONDARY_TRAITS: {a.secondary_traits}",
            f"- Valuation emphasis: {[d.get('id') for d in a.model_specific_drivers]}",
            f"- Model slot / status: {a.model_slot} / {a.model_slot_status}",
            f"- Classification: {a.classification_path} (confidence={a.confidence}; provenance={a.provenance})",
            f"- WHY: {a.why}",
        ]
    for b in report.benchmark_results:
        lines.append(f"- {b.dimension_id} **{b.label}**: {b.why}")
    lines += [
        f"- thesis_coherence: {report.thesis_coherence}",
        f"- process_outcome: {report.process_outcome}",
        f"- S1–7 conflicts: {report.stage4_6_7_conflicts or '(none)'}",
        f"- S6_H7 consumed: {report.s6_handoff_flags_consumed or '(none)'}",
        f"- S7_H8 carries: {report.s7_h8_carries or '(none)'}",
        f"- S8_H9 carries: {report.s8_h9_carries or '(none)'}",
        *bullets(report.carry_forward_concerns, empty="(none listed)"),
        "",
        "## VA lenses (evidence, not scored average)",
    ]
    for va in report.va_lenses:
        lines.append(
            f"- {va.lens_id} {va.lens_name}: {va.summary} | WHY: {va.why} | "
            f"labels={va.labels} | escalate={va.escalate_to_human}"
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
                    f"escalate={f.escalate_to_human}; dim={f.dimension}; va={f.va_lens}"
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
        "_No RED/ORANGE/GREEN. No scores / averaged valuation score / universal P/E or MoS% gates. "
        "Benchmark ≠ hard gate. Method E. No label-count→outcome. "
        "No CAPM β engine. No mechanical method averaging. Dual terminals = CROSS-CHECKS only. "
        "Quality ⊥ valuation. Reverse DCF first-class; expectations ≠ cheap/expensive. "
        "Session-aware freshness; filing-period CS; currency reconcile. "
        "A7 recurring M&A = reinvestment; no free-organic acquired growth; no deal-by-deal DCF. "
        "SBC never ignore. NON-TERMINATING. No BUY/SELL. No Stage 9. FI out of scope._",
        "",
    ]
    return "\n".join(lines)
