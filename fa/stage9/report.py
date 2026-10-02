"""ADHD markdown renderer for Stage 9 — Plan §0.L 8-block dashboard.

No colors/scores/BUY-SELL/averaged external-risk score/final FA synthesis.
"""
from __future__ import annotations

from ..models import Stage9Report


def render_stage9_markdown(report: Stage9Report) -> str:
    periods = ", ".join(
        f"{p.get('period_key')}@{p.get('version_id')}" for p in report.periods_used
    ) or "(none)"
    sources = ", ".join(report.sources) if report.sources else "(none listed)"

    def bullets(items: list[str], empty: str = "(none)") -> list[str]:
        if not items:
            return [f"- {empty}"]
        return [f"- {x}" for x in items]

    lines = [
        f"# Stage 9 — Industry / Competition / Macro / External Risk — {report.ticker}",
        f"Date: {report.date}",
        f"Normalized versions used: {periods}",
        f"Stage 1 Gate2 hypothesis pointer consumed: {bool(report.gate2_hypothesis_consumed.get('present'))}",
        f"Sources: {sources}",
        "",
        "## Outcome",
        f"**{report.process_outcome}**",
        "(Carry-forward external-risk exhibits for final FA — "
        "Stage 9 does not alone terminate later stages; no final FA color synthesis here)",
        f"terminates_later_stages: {report.terminates_later_stages}",
        f"no_final_fa_synthesis: {report.no_final_fa_synthesis}",
        f"regulatory_posture: {report.regulatory_posture}",
        f"cycle_position_class: {report.cycle_position_class} (descriptive ≠ prediction)",
        f"concentration_labels: {report.concentration_labels}",
        "",
        "## Why",
        *bullets(report.why_bullets),
        "",
        "## Dashboard 1 — Industry structure map (ER1) + archetype",
        *bullets(report.industry_structure_bullets),
    ]
    if report.archetype:
        a = report.archetype
        lines += [
            f"- PRIMARY_ARCHETYPE: {a.primary_archetype} ({a.primary_label})",
            f"- SECONDARY_TRAITS: {a.secondary_traits}",
            f"- Classification: {a.classification_path} (confidence={a.confidence}; provenance={a.provenance})",
            f"- WHY: {a.why}",
        ]

    lines += [
        "",
        "## Dashboard 2 — Moat durability stress vs Gate 2 (ER2)",
        *bullets(report.moat_durability_bullets),
        "",
        "## Dashboard 3 — Disruption mechanism + evidence labels (ER3)",
        *bullets(report.disruption_bullets),
        "",
        "## Dashboard 4 — Concentration map (ER4)",
        *bullets(report.concentration_bullets),
        "",
        "## Dashboard 5 — Regulatory + geopolitical envelope (ER5+ER6)",
        *bullets(report.regulatory_geo_bullets),
        "",
        "## Dashboard 6 — Macro / cycle context + cyclicality honesty (ER7)",
        *bullets(report.macro_cycle_bullets),
        "",
        "## Dashboard 7 — Thesis breakers + monitoring + FP-E (ER8)",
    ]
    if report.thesis_breakers:
        for b in report.thesis_breakers:
            lines.append(
                f"- {b.breaker_id}: mechanism={b.mechanism}; "
                f"indicators={b.observable_indicators}; monitors={b.monitoring_variables}; "
                f"label={b.evidence_label}; linked={b.linked_er_lenses}; "
                f"active_fact={b.active_fact}; source={b.source_tie}"
            )
    else:
        lines.append("- breakers: (none assembled — deepen Gate2 kill-shots / Risk Factors)")
    if report.false_positive_tags:
        for t in report.false_positive_tags:
            lines.append(
                f"- FP {t.get('id')}: {t.get('description')} — severity={t.get('severity')}; "
                f"why={t.get('why')}; counterexample={t.get('counterexample')}"
            )
    else:
        lines.append("- FP-E watches: (none tagged)")
    lines += bullets(report.breaker_fp_bullets, empty="(no additional breaker/FP notes)")

    lines += [
        "",
        "## Dashboard 8 — ER labels + WHY + S1–8 conflicts + outcome + carries",
    ]
    for er in report.er_lenses:
        lines.append(
            f"- {er.lens_id} {er.lens_name}: {er.summary} | WHY: {er.why} | "
            f"evidence_label={er.evidence_label} | labels={er.labels} | "
            f"mechanism={er.mechanism} | exposure={er.exposure} | escalate={er.escalate_to_human}"
        )
    lines += [
        f"- thesis_coherence: {report.thesis_coherence}",
        f"- process_outcome: {report.process_outcome}",
        f"- S1–8 conflicts: {report.s1_8_conflicts or '(none)'}",
        f"- S8_H9 forwarded: {report.s8_h9_carries_forwarded or '(none)'}",
        f"- S9_HFA carries: {report.s9_hfa_carries or '(none)'}",
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
        ]
        if report.semantic.findings:
            lines.append("- findings:")
            for f in report.semantic.findings[:24]:
                lines.append(
                    f"  - {f.topic}: kind={f.evidence_kind}; judgment={f.materiality_judgment}; "
                    f"escalate={f.escalate_to_human}; dim={f.dimension}; er={f.er_lens}; "
                    f"mech={f.mechanism}"
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
        "_No RED/ORANGE/GREEN. No scores / averaged external-risk score / numeric concentration "
        "or regulatory kill gates. Benchmark ≠ hard gate. Method E. No label-count→outcome. "
        "Risk = mechanism + exposure + evidence. "
        "ER2: Gate2/S1/S5 hypotheses only — no S5 pricing-power redo / no S1 thesis restatement. "
        "ER8: 3–7 falsifiers — NOT a giant risk register. "
        "No industry warehouse / news NLP / ESG vendor grades as gates. "
        "No Stage 8 valuation redo. No final FA color synthesis. "
        "NON-TERMINATING. No BUY/SELL. FI out of scope. "
        "FP-E flags are flags-not-auto-fails. Opacity ≠ contradiction (Stage 8 owns that)._",
        "",
    ]
    return "\n".join(lines)
