"""ADHD markdown renderer for Stage 2 — no color words, no numeric pass/fail."""
from __future__ import annotations

from ..models import Stage2Report

# Map process outcome → checkbox narrative label (from Stage 2 plan template)
_OUTCOME_CHECK = {
    "PROCEED": "Strong enough BS to proceed",
    "CONDITIONAL": "Fragile / elevated survival risk — proceed only with eyes open + monitors",
    "REVIEW_REQUIRED": "Monitor-heavy — incomplete or mixed; continue only if listed monitors are watchable",
    "TOO_HARD": "Not enough evidence to proceed (REVIEW / TOO HARD)",
    "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY": "Not enough evidence to proceed (REVIEW / TOO HARD)",
}


def render_stage2_markdown(report: Stage2Report) -> str:
    periods = ", ".join(
        f"{p.get('period_key')}@{p.get('version_id')}" for p in report.periods_used
    ) or "(none)"
    sources = ", ".join(report.sources) if report.sources else "(none listed)"

    labels = [
        "Strong enough BS to proceed",
        "Fragile / elevated survival risk — proceed only with eyes open + monitors",
        "Monitor-heavy — incomplete or mixed; continue only if listed monitors are watchable",
        "Not enough evidence to proceed (REVIEW / TOO HARD)",
    ]
    chosen = report.narrative_verdict
    verdict_lines = []
    for lab in labels:
        mark = "x" if lab == chosen or lab == _OUTCOME_CHECK.get(report.process_outcome) else " "
        # prefer exact narrative match
        if lab == report.narrative_verdict:
            mark = "x"
        elif lab != report.narrative_verdict and mark == "x" and report.narrative_verdict not in labels:
            mark = "x" if lab == _OUTCOME_CHECK.get(report.process_outcome) else " "
        verdict_lines.append(f"- [{mark}] {lab}")

    # Fix: only one checked
    target = report.narrative_verdict
    if target not in labels:
        target = _OUTCOME_CHECK.get(report.process_outcome, labels[-1])
    verdict_lines = [f"- [{'x' if lab == target else ' '}] {lab}" for lab in labels]

    def bullets(key: str) -> str:
        items = report.evidence_bullets.get(key) or []
        return "\n".join(f"  - {x}" for x in items) if items else "  - (none)"

    lines = [
        f"# Stage 2 — Balance Sheet — {report.ticker}",
        f"Date: {report.date}",
        f"Periods used: {periods}",
        f"Sources: {sources}",
        f"Process outcome: **{report.process_outcome}**",
        f"block_next (Stage 3+): {report.block_next}",
        "",
        "## Verdict (pick one narrative label — NOT a color)",
        *verdict_lines,
        "",
        "## One-paragraph survival thesis",
        report.survival_thesis,
        "",
        "## Evidence (facts only)",
        f"- Liquidity (cash, restricted, facilities):",
        bullets("liquidity"),
        f"- Contractual leverage (debt, leases, current portion):",
        bullets("contractual_leverage"),
        f"- Maturities:",
        bullets("maturities"),
        f"- WC signals:",
        bullets("wc_signals"),
        f"- Soft equity (goodwill/intangibles):",
        bullets("soft_equity"),
        f"- Note flags (going-concern, covenants, other):",
        bullets("note_flags"),
        "",
        "## What would change my mind (falsifiers)",
    ]
    for f in report.falsifiers:
        lines.append(f"- {f}")

    lines += ["", "## Monitors (if proceeding)"]
    if report.monitors:
        for m in report.monitors:
            lines.append(f"- {m}")
    else:
        lines.append("- (none)")

    lines += ["", "## Gaps / contract fields still null"]
    if report.gaps:
        for g in report.gaps:
            lines.append(f"- {g}")
    else:
        lines.append("- (none listed)")

    if report.calc and report.calc.null_reasons:
        lines.append("- Calc null reasons:")
        for k, v in report.calc.null_reasons.items():
            lines.append(f"  - {k}: {v}")

    lines += [
        "",
        f"## Enough to proceed? {report.enough_to_proceed} — why",
        report.enough_why,
        "",
        "## Question spine (status)",
    ]
    for qa in report.question_answers:
        tag = "MUST" if qa.must else "SHOULD"
        lines.append(f"- [{tag}] {qa.question_id} ({qa.status}): {qa.answer_summary}")

    if report.block_reasons:
        lines += ["", "## Block reasons (process-level)"]
        for b in report.block_reasons:
            lines.append(f"- {b}")

    lines.append("")
    lines.append("---")
    lines.append(
        "_No RED/ORANGE/GREEN. No numeric investment thresholds. "
        "Ratios are descriptive evidence only. FI out of scope. No Stage 3+ in this report._"
    )
    lines.append("")
    return "\n".join(lines)
