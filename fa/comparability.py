"""SD-W4-C1 dual-series / comparability-break honesty.

Preserve as-reported. Optional disclosed COMPARABLE companion only — never
overwrite, never model-created reconstruction / auto-recast.
"""
from __future__ import annotations

import re
from typing import Any

# Semantic / note cues that a perimeter change may make multi-year levels non-comparable.
_PERIMETER_CUE_RE = re.compile(
    r"(?i)\b("
    r"discontinued\s+operations?"
    r"|continuing\s+operations?"
    r"|spin[- ]?off"
    r"|spin[- ]?separation"
    r"|separation\s+of\s+\w+"
    r"|portfolio\s+change"
    r"|divestiture\s+of\s+the\s+\w+\s+business"
    r"|business\s+as\s+a\s+discontinued\s+operation"
    r")\b"
)

# Explicit Normalized field keys that mark a perimeter / restatement event on a period.
_EXPLICIT_BREAK_FIELDS = (
    "comparability_break",
    "perimeter_change",
    "perimeter_event",
    "spin_separation",
    "discontinued_operations_restated",
    "continuing_ops_restatement",
)


def _num(fields: dict, key: str) -> float | None:
    v = fields.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fy_sorted(periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [p for p in periods if p.get("period_type") == "FY"],
        key=lambda d: d.get("period_key") or "",
    )


def semantic_suggests_perimeter_break(text: str | None) -> bool:
    if not text:
        return False
    return bool(_PERIMETER_CUE_RE.search(text))


def collect_perimeter_cue_text(
    semantic_texts: list[str] | None = None,
    period_notes: list[str] | None = None,
) -> str:
    parts: list[str] = []
    for t in semantic_texts or []:
        if t:
            parts.append(str(t))
    for t in period_notes or []:
        if t:
            parts.append(str(t))
    return "\n".join(parts)


def detect_comparability_breaks(
    periods: list[dict[str, Any]],
    *,
    semantic_texts: list[str] | None = None,
    explicit_breaks: list[dict[str, Any]] | None = None,
    revenue_cliff_fraction: float = 0.15,
) -> list[dict[str, Any]]:
    """Detect AS-REPORTED series breaks — never invent continuing-ops levels.

    Sources (no ticker hardcodes):
    1. ``explicit_breaks`` caller list: {from_period, to_period, reason, ...}
    2. Period-level explicit Normalized flags / fields
    3. Large FY revenue cliff (|Δ| ≥ revenue_cliff_fraction) **only when**
       perimeter semantic/note cues are present (cliff alone ≠ break — e.g. cyclical decline)

    Each break record includes ``series="as_reported"`` and
    ``honesty_flag="COMPARABILITY_BREAK"``. Comparable companion is NEVER synthesized here.
    """
    breaks: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(rec: dict[str, Any]) -> None:
        a, b = str(rec.get("from_period")), str(rec.get("to_period"))
        if (a, b) in seen:
            return
        seen.add((a, b))
        rec.setdefault("series", "as_reported")
        rec.setdefault("honesty_flag", "COMPARABILITY_BREAK")
        rec.setdefault("comparable_companion", None)  # never invent
        rec.setdefault("model_reconstruction", False)
        breaks.append(rec)

    for eb in explicit_breaks or []:
        if eb.get("from_period") and eb.get("to_period"):
            add(dict(eb))

    fy = _fy_sorted(periods)
    # Explicit period flags → break between prior FY and this FY
    for i, doc in enumerate(fy):
        fields = doc.get("fields") or {}
        flagged = any(
            fields.get(k) is True or doc.get(k) is True for k in _EXPLICIT_BREAK_FIELDS
        )
        reason = fields.get("comparability_break_reason") or doc.get("comparability_break_reason")
        if flagged or reason:
            if i == 0:
                continue
            add(
                {
                    "from_period": fy[i - 1].get("period_key"),
                    "to_period": doc.get("period_key"),
                    "reason": reason or "explicit_period_comparability_flag",
                    "detection": "explicit_normalized_flag",
                }
            )

    cue_blob = collect_perimeter_cue_text(semantic_texts)
    # Also scan period review_notes / notes if present
    note_bits: list[str] = []
    for doc in fy:
        for k in ("review_notes", "notes", "comparability_notes"):
            v = doc.get(k)
            if isinstance(v, str):
                note_bits.append(v)
            elif isinstance(v, list):
                note_bits.extend(str(x) for x in v)
        fields = doc.get("fields") or {}
        for k in ("comparability_notes", "perimeter_notes"):
            v = fields.get(k)
            if isinstance(v, str):
                note_bits.append(v)
    cue_blob = collect_perimeter_cue_text([cue_blob], note_bits)
    has_perimeter_cue = semantic_suggests_perimeter_break(cue_blob)

    if has_perimeter_cue and len(fy) >= 2:
        for i in range(1, len(fy)):
            prev, curr = fy[i - 1], fy[i]
            r0 = _num(prev.get("fields") or {}, "revenue")
            r1 = _num(curr.get("fields") or {}, "revenue")
            if r0 is None or r1 is None or r0 == 0:
                continue
            frac = (r1 - r0) / abs(r0)
            if abs(frac) >= revenue_cliff_fraction:
                add(
                    {
                        "from_period": prev.get("period_key"),
                        "to_period": curr.get("period_key"),
                        "reason": "perimeter_cue_plus_revenue_cliff",
                        "detection": "semantic_or_note_cue_with_cliff",
                        "revenue_yoy_fraction_as_reported": frac,
                        "cue_present": True,
                    }
                )

    return breaks


def attach_disclosed_comparable_companion(
    break_rec: dict[str, Any],
    *,
    companion_series: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Attach disclosed continuing-ops/recast companion — never invent levels.

    ``companion_series`` items: {period_key, revenue, source, statement_basis}
    Only attaches when provided by caller from authoritative disclosure.
    """
    out = dict(break_rec)
    if companion_series:
        out["comparable_companion"] = {
            "series": "comparable_continuing_ops_disclosed",
            "points": companion_series,
            "model_reconstruction": False,
        }
    else:
        out["comparable_companion"] = None
    return out


def annotate_yoy_rows_with_breaks(
    yoy_rows: list[dict[str, Any]],
    breaks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mark YoY rows that cross a comparability break; preserve as-reported arithmetic."""
    break_pairs = {
        (str(b.get("from_period")), str(b.get("to_period"))): b for b in breaks
    }
    out: list[dict[str, Any]] = []
    for row in yoy_rows:
        r = dict(row)
        key = (str(r.get("from_period")), str(r.get("to_period")))
        r.setdefault("series", "as_reported")
        if key in break_pairs:
            b = break_pairs[key]
            r["comparability_break"] = True
            r["honesty_flag"] = "COMPARABILITY_BREAK"
            r["comparability_reason"] = b.get("reason")
            r["comparable_companion"] = b.get("comparable_companion")
            # Do not null the as-reported fraction — keep arithmetic, label honesty.
            # Consumers must not treat as clean organic YoY.
            if r.get("null_reason") is None:
                r["null_reason"] = None  # keep number
            r["clean_organic_yoy"] = False
            r["series_note"] = (
                "as_reported crosses COMPARABILITY_BREAK — not clean organic; "
                "no model-created recast"
            )
        else:
            r.setdefault("comparability_break", False)
        out.append(r)
    return out


def window_crosses_break(
    from_period: str | None,
    to_period: str | None,
    breaks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """True if a multi-year window spans any break pair (inclusive span)."""
    if not from_period or not to_period or not breaks:
        return None
    # Period keys FY2021 style — lexicographic works for FY#### 
    for b in breaks:
        a, c = str(b.get("from_period")), str(b.get("to_period"))
        # Window crosses break if break segment overlaps [from, to]
        if from_period <= a and c <= to_period:
            return b
        if from_period <= c and a <= to_period and a >= from_period:
            return b
    return None
