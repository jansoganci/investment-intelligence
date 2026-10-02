"""ADHD markdown renderer for Final FA Synthesis — Plan §0.N / §0.L.

State first; why; supports; challenges; unresolved; queue; thesis; provenance.
No emoji traffic lights. No BUY/SELL / scores / weights.
"""
from __future__ import annotations

from .models import FinalFaSynthesis


def render_final_fa_markdown(doc: FinalFaSynthesis | dict) -> str:
    if isinstance(doc, FinalFaSynthesis):
        d = doc.to_dict()
    else:
        d = doc

    ticker = d.get("ticker") or "?"
    as_of = d.get("as_of") or ""
    state = d.get("final_state") or "?"
    tech = d.get("technical_eligible")
    why = d.get("why_bullets") or []
    supports = d.get("supports") or []
    challenges = d.get("challenges") or []
    unresolved = d.get("unresolved") or []
    conflicts = d.get("conflicts") or []
    queue = d.get("human_review_queue") or []
    thesis = d.get("thesis") or {}
    carries = d.get("carries_consumed") or {}
    outcomes = d.get("stage_outcomes") or {}
    monitors = d.get("monitors") or []
    falsifiers = d.get("falsifiers") or []
    prov = d.get("provenance") or {}
    acks = d.get("acknowledgements") or {}
    soft_chips = d.get("soft_missing_chips") or []

    def bullets(items: list, empty: str = "(none)") -> list[str]:
        if not items:
            return [f"- {empty}"]
        out = []
        for x in items:
            if isinstance(x, dict):
                text = x.get("text") or x.get("summary") or str(x)
                sev = x.get("severity_level")
                prefix = f"[{sev}] " if sev else ""
                out.append(f"- {prefix}{text}")
            else:
                out.append(f"- {x}")
        return out

    lines = [
        f"# Final FA Synthesis — {ticker}",
        f"As of: {as_of}",
        "",
        "## 1. Final state + technical_eligible",
        f"**final_state:** {state}",
        f"**technical_eligible:** {tech}",
        f"(GREEN ≠ BUY; ORANGE never TA/watchlist; Missing ≠ RED; TOO_HARD ≠ RED)",
        "",
        "## 2. Why (≤5)",
        *bullets(why),
        "",
        "## 3. Supports",
        *bullets(supports),
        "",
        "## 4. Challenges (severity chips)",
        *bullets(challenges),
    ]
    if soft_chips:
        lines += ["", f"Soft-missing chips: {soft_chips}"]

    lines += [
        "",
        "## 5. Conflicts / unresolved",
        "### Conflicts (≤5)",
        *bullets(conflicts),
        "### Unresolved",
        *bullets(unresolved),
        "",
        "## 6. Human review queue (0–5)",
    ]
    if not queue:
        lines.append("- (empty — allowed)")
    else:
        for h in queue:
            if isinstance(h, dict):
                lines.append(
                    f"- {h.get('id')}: {h.get('why_human')} "
                    f"(blocks_color={h.get('blocks_color')}; "
                    f"options={h.get('decision_options')})"
                )
            else:
                lines.append(f"- {h}")

    lines += [
        "",
        "## 7. Handoff strip",
        f"- stage_outcomes: {outcomes}",
        f"- carries s6_h7: {carries.get('s6_h7') or []}",
        f"- carries s7_h8: {carries.get('s7_h8') or []}",
        f"- carries s8_h9: {carries.get('s8_h9') or []}",
        f"- carries s9_hfa: {carries.get('s9_hfa') or []}",
        "### Monitors",
        *bullets(monitors),
        "### Falsifiers",
    ]
    if not falsifiers:
        lines.append("- (none)")
    else:
        for f in falsifiers:
            if isinstance(f, dict):
                lines.append(
                    f"- {f.get('breaker_id')}: active_fact={f.get('active_fact')}; "
                    f"source={f.get('source')}; {f.get('mechanism') or ''}"
                )
            else:
                lines.append(f"- {f}")

    lines += [
        "",
        "## Thesis",
        f"- one_liner: {thesis.get('one_liner')}",
        f"- economic_engine: {thesis.get('economic_engine')}",
        f"- durable_advantage_hypothesis: {thesis.get('durable_advantage_hypothesis')}",
        f"- capital_destination_posture: {thesis.get('capital_destination_posture')}",
        "### Key supports",
        *bullets(thesis.get("key_supports") or []),
        "### Key challenges",
        *bullets(thesis.get("key_challenges") or []),
        "",
        "## Provenance",
        f"- stage_versions: {prov.get('stage_versions')}",
        f"- carries_frozen_at: {prov.get('carries_frozen_at')}",
        f"- acknowledgements: {acks}",
        "",
        "---",
        "No BUY/SELL. No weights/averaging. No watchlist rank. Reconciliation only.",
    ]
    return "\n".join(lines) + "\n"
