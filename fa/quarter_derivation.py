"""Deterministic fiscal Q4 derivation for quarterly *flow* metrics.

US issuers rarely file a separate Q4 10-Q. When FY + Q1 + Q2 + Q3 exist and are
comparable, reconstruct discrete Q4 flow values.

**Discrete quarters** (duration ~90d or additive identity):

    Q4 = FY - Q1 - Q2 - Q3

**YTD cumulative interims** (duration ~180d/~270d or nested YTD shape):

    Q2d = Q2YTD - Q1YTD
    Q3d = Q3YTD - Q2YTD
    Q4d = FY - Q3YTD

NEVER use FY-(Q1+Q2YTD+Q3YTD) when inputs are YTD — that double-subtracts and
can yield absurd negative CapEx (F-DERIVE-YTD-Q4-01 / A2).

Fiscal label alone is NOT proof of discrete quarter. If start/end duration and
arithmetic basis are ambiguous → block with UNKNOWN/MAPPING_AMBIGUOUS (do not
fabricate). Balance-sheet snapshots are never derived. Derived values are tagged
calculated — never presented as reported FACT.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from .contract import (
    BS_CORE_FIELDS,
    BS_STAGE2_EXTENSIONS,
    BS_STAGE3_EXTENSIONS,
    CF_FIELDS,
    CF_STAGE3_BRIDGE_HELPERS,
    CF_STAGE3_EXTENSIONS,
    IS_FIELDS,
    blank_period_document,
)
from .ids import period_key_fy, period_key_q
from .lineage import attach_field_with_lineage

# Exact method markers required in lineage / period meta.
DERIVED_Q4_METHOD = "DERIVED_Q4_FROM_FY_MINUS_Q1_Q2_Q3"
DERIVED_Q4_METHOD_YTD = "DERIVED_Q4_FROM_FY_MINUS_Q3YTD"
FLOW_BASIS_DISCRETE = "DISCRETE"
FLOW_BASIS_YTD = "YTD"
FLOW_BASIS_UNKNOWN = "UNKNOWN"

# Duration windows (days) — architecture prefers duration-aware periods.
_DUR_DISCRETE_Q = (70, 110)
_DUR_YTD_Q2 = (150, 210)
_DUR_YTD_Q3 = (230, 300)
_DUR_FY = (300, 400)

# Income-statement additive flows. Exclude EPS (not additive).
_NON_ADDITIVE_IS = frozenset({"diluted_eps"})
DERIVABLE_FLOW_FIELDS: tuple[str, ...] = tuple(
    f for f in IS_FIELDS if f not in _NON_ADDITIVE_IS
) + tuple(CF_FIELDS) + tuple(CF_STAGE3_EXTENSIONS)

# Explicit denylist — never derive with FY−Q1−Q2−Q3.
NON_DERIVABLE_FIELDS: frozenset[str] = frozenset(
    list(BS_CORE_FIELDS)
    + list(BS_STAGE2_EXTENSIONS)
    + list(BS_STAGE3_EXTENSIONS)
    + list(CF_STAGE3_BRIDGE_HELPERS)
    + list(_NON_ADDITIVE_IS)
    + [
        "shares_diluted_weighted",
        "shares_basic_weighted",
        "shares_outstanding",
        "diluted_eps",
        "revenue_organic_growth_yoy",
        "revenue_acquired_impact_yoy",
        "constant_currency_revenue_growth_yoy",
        "volume_metric",
        "same_store_sales_yoy",
        "backlog_or_rpo",
    ]
)

_BLOCK_MISSING = "UNKNOWN"
_BLOCK_AMBIGUOUS = "MAPPING_AMBIGUOUS"
_BLOCK_CONFLICT = "SOURCE_CONFLICT"

_PERIOD_KEY_RE = re.compile(r"^(?:FY(\d{4})|(\d{4})Q([1-4]))$")


def parse_period_key(period_key: str) -> tuple[str, int, int | None]:
    """Return (kind, fiscal_year, quarter_or_None). kind in {'FY','Q'}."""
    m = _PERIOD_KEY_RE.fullmatch(period_key or "")
    if not m:
        raise ValueError(f"unrecognized period_key: {period_key}")
    if m.group(1):
        return "FY", int(m.group(1)), None
    return "Q", int(m.group(2)), int(m.group(3))


def economic_quarter_index(fiscal_year: int, quarter: int) -> int:
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"invalid quarter: {quarter}")
    return int(fiscal_year) * 4 + (int(quarter) - 1)


def index_to_fy_q(idx: int) -> tuple[int, int]:
    fy, rem = divmod(idx, 4)
    return fy, rem + 1


def step_quarter_back(fy: int, q: int) -> tuple[int, int]:
    if q == 1:
        return fy - 1, 4
    return fy, q - 1


def step_quarter_forward(fy: int, q: int) -> tuple[int, int]:
    if q == 4:
        return fy + 1, 1
    return fy, q + 1


def _num(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _null_code(reason: Any) -> str | None:
    if reason is None:
        return None
    if isinstance(reason, dict):
        return reason.get("code") or reason.get("reason_code")
    text = str(reason)
    for code in (
        _BLOCK_CONFLICT,
        _BLOCK_AMBIGUOUS,
        "NOT_DISCLOSED",
        "NOT_APPLICABLE",
        "UNKNOWN",
    ):
        if text.startswith(code) or f"{code}:" in text:
            return code
    return None


def _lineage_tag(doc: dict[str, Any], field: str) -> str | None:
    for L in doc.get("lineage") or []:
        if L.get("field") != field:
            continue
        ref = L.get("source_ref") or L.get("source_ref") or ""
        if ":" in str(ref):
            return str(ref).split(":")[-1].split()[0]
        notes = str(L.get("notes") or "")
        m = re.search(r"(?:tag|us-gaap|us-gaap)[=:\s]+([A-Za-z0-9]+)", notes, re.I)
        if m:
            return m.group(1)
        if ref:
            return str(ref)
    return None


def _field_unit(doc: dict[str, Any], field: str) -> str | None:
    units = doc.get("field_units") or doc.get("field_units") or {}
    if field in units and units[field] is not None:
        return str(units[field])
    for L in doc.get("lineage") or []:
        if L.get("field") == field:
            notes = str(L.get("notes") or "")
            m = re.search(r"unit[=:\s]+([A-Za-z0-9_]+)", notes, re.I)
            if m:
                return m.group(1)
    if field.startswith("shares_") or field.endswith("_shares"):
        return "shares"
    if field == "diluted_eps":
        return "USD/shares"
    return "USD"


def _null_reasons_map(doc: dict[str, Any]) -> dict:
    return doc.get("null_reasons") or doc.get("null_reasons") or {}


def _uncertainty_map(doc: dict[str, Any]) -> dict:
    return doc.get("field_uncertainty") or doc.get("field_uncertainty") or {}


def _docs_perimeter_comparable(docs: list[dict[str, Any]]) -> tuple[bool, str | None]:
    cik = {str(d.get("cik") or "") for d in docs}
    cik.discard("")
    if len(cik) > 1:
        return False, "reporting perimeter / CIK differs across FY/Q1/Q2/Q3"
    names = {
        str(d.get("entity_name") or d.get("entity_name") or "").strip().lower()
        for d in docs
    }
    names.discard("")
    if len(names) > 1:
        return False, "entity_name differs across FY/Q1/Q2/Q3 (perimeter change)"
    currency = {
        str(d.get("reporting_currency") or d.get("reporting_currency") or "USD")
        for d in docs
    }
    if len(currency) > 1:
        return False, "reporting_currency mismatch across FY/Q1/Q2/Q3"
    basis = {
        str(d.get("statement_basis") or d.get("statement_basis") or "us-gaap")
        for d in docs
    }
    if len(basis) > 1:
        return False, "statement_basis mismatch across FY/Q1/Q2/Q3"
    return True, None


def _version_conflict(docs: list[dict[str, Any]]) -> tuple[bool, str | None]:
    for d in docs:
        if d.get("status") == "conflict":
            return True, f"{d.get('period_key')}: status=conflict"
        if d.get("change_reason") == "restatement" and d.get("status") not in (
            "accepted",
            None,
        ):
            if d.get("review_status") == "pending" and d.get("status") == "draft":
                return True, f"{d.get('period_key')}: restatement draft not accepted"
    return False, None



def _duration_days(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        a = date.fromisoformat(str(start)[:10])
        b = date.fromisoformat(str(end)[:10])
        return (b - a).days
    except ValueError:
        return None


def _doc_duration_days(doc: dict[str, Any] | None) -> int | None:
    if not doc:
        return None
    return _duration_days(doc.get("period_start"), doc.get("period_end"))


def _field_duration_days(doc: dict[str, Any] | None, field: str) -> int | None:
    """Prefer field-lineage duration_days=N; fall back to document period_start/end."""
    if not doc:
        return None
    for L in doc.get("lineage") or []:
        if L.get("field") != field:
            continue
        notes = str(L.get("notes") or "")
        m = re.search(r"duration_days\s*=\s*(-?\d+)", notes, re.I)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        m = re.search(r"flow_basis\s*=\s*(YTD|DISCRETE|UNKNOWN)", notes, re.I)
        # duration may still be absent; continue to doc-level
    return _doc_duration_days(doc)


def _field_flow_basis_hint(doc: dict[str, Any] | None, field: str) -> str | None:
    if not doc:
        return None
    explicit = (doc.get("field_flow_basis") or {}).get(field)
    if explicit in (FLOW_BASIS_DISCRETE, FLOW_BASIS_YTD, FLOW_BASIS_UNKNOWN):
        return explicit
    for L in doc.get("lineage") or []:
        if L.get("field") != field:
            continue
        notes = str(L.get("notes") or "")
        m = re.search(r"flow_basis\s*=\s*(YTD|DISCRETE|UNKNOWN)", notes, re.I)
        if m:
            return m.group(1).upper()
    return None


def _basis_from_duration(days: int | None, fiscal_period: str | None) -> str | None:
    """Classify a single interim duration. None if inconclusive."""
    if days is None:
        return None
    if _DUR_DISCRETE_Q[0] <= days <= _DUR_DISCRETE_Q[1]:
        return FLOW_BASIS_DISCRETE
    fp = (fiscal_period or "").upper()
    if fp == "Q2" and _DUR_YTD_Q2[0] <= days <= _DUR_YTD_Q2[1]:
        return FLOW_BASIS_YTD
    if fp == "Q3" and _DUR_YTD_Q3[0] <= days <= _DUR_YTD_Q3[1]:
        return FLOW_BASIS_YTD
    if fp == "Q1" and _DUR_DISCRETE_Q[0] <= days <= _DUR_DISCRETE_Q[1]:
        return FLOW_BASIS_DISCRETE
    # Q1 YTD is same as discrete (~90d). Longer Q1 → ambiguous.
    if days > _DUR_DISCRETE_Q[1] and days < _DUR_FY[0]:
        return FLOW_BASIS_YTD
    return None


def _additive_tol(fy_v: float) -> float:
    return max(1.0, abs(fy_v) * 1e-6, abs(fy_v) * 1e-9)


def discrete_quarters_from_ytd(
    q1_ytd: float,
    q2_ytd: float,
    q3_ytd: float,
    fy_v: float,
) -> dict[str, float]:
    """Convert YTD cumulative interims to discrete quarters.

    Q1d = Q1YTD; Q2d = Q2YTD−Q1YTD; Q3d = Q3YTD−Q2YTD; Q4d = FY−Q3YTD.
    """
    q1d = q1_ytd
    q2d = q2_ytd - q1_ytd
    q3d = q3_ytd - q2_ytd
    q4d = fy_v - q3_ytd
    return {"Q1": q1d, "Q2": q2d, "Q3": q3d, "Q4": q4d}


def classify_quarterly_flow_basis(
    q1_v: float,
    q2_v: float,
    q3_v: float,
    fy_v: float,
    *,
    q1_dur: int | None = None,
    q2_dur: int | None = None,
    q3_dur: int | None = None,
    q1_hint: str | None = None,
    q2_hint: str | None = None,
    q3_hint: str | None = None,
) -> dict[str, Any]:
    """Classify Q1/Q2/Q3+FY stack as DISCRETE, YTD, or UNKNOWN.

    Fiscal label alone is never sufficient for DISCRETE. Prefer start/end
    duration; use arithmetic only as supporting evidence. Ambiguity → UNKNOWN.
    """
    hints = [h for h in (q1_hint, q2_hint, q3_hint) if h]
    if hints:
        if FLOW_BASIS_UNKNOWN in hints:
            return {
                "basis": FLOW_BASIS_UNKNOWN,
                "reason": "explicit flow_basis=UNKNOWN on an interim input",
            }
        if FLOW_BASIS_YTD in hints and FLOW_BASIS_DISCRETE in hints:
            return {
                "basis": FLOW_BASIS_UNKNOWN,
                "reason": "mixed explicit flow_basis YTD vs DISCRETE across interims",
            }
        if all(h == FLOW_BASIS_YTD for h in hints) or (
            FLOW_BASIS_YTD in hints and FLOW_BASIS_DISCRETE not in hints
        ):
            # Q1 may be DISCRETE(=Q1YTD) while Q2/Q3 are YTD — treat stack as YTD
            if FLOW_BASIS_YTD in hints:
                return {
                    "basis": FLOW_BASIS_YTD,
                    "reason": "explicit flow_basis=YTD on interim input(s)",
                }
        if all(h == FLOW_BASIS_DISCRETE for h in hints):
            return {
                "basis": FLOW_BASIS_DISCRETE,
                "reason": "explicit flow_basis=DISCRETE on interim inputs",
            }

    dur_bases = []
    for dur, fp in ((q1_dur, "Q1"), (q2_dur, "Q2"), (q3_dur, "Q3")):
        b = _basis_from_duration(dur, fp)
        if b is not None:
            dur_bases.append((fp, b, dur))

    if dur_bases:
        kinds = {b for _fp, b, _d in dur_bases}
        if FLOW_BASIS_YTD in kinds and FLOW_BASIS_DISCRETE in kinds:
            # Q1 discrete + Q2/Q3 YTD is the common companyfacts pattern → YTD stack
            q2q3 = [b for fp, b, _d in dur_bases if fp in ("Q2", "Q3")]
            if q2q3 and all(x == FLOW_BASIS_YTD for x in q2q3):
                return {
                    "basis": FLOW_BASIS_YTD,
                    "reason": (
                        "duration: Q2/Q3 YTD cumulative "
                        f"({', '.join(f'{fp}={d}d/{b}' for fp, b, d in dur_bases)})"
                    ),
                }
            return {
                "basis": FLOW_BASIS_UNKNOWN,
                "reason": (
                    "duration conflict across Q1/Q2/Q3: "
                    f"{', '.join(f'{fp}={d}d/{b}' for fp, b, d in dur_bases)}"
                ),
            }
        if kinds == {FLOW_BASIS_YTD}:
            return {
                "basis": FLOW_BASIS_YTD,
                "reason": (
                    "duration indicates YTD cumulative interims "
                    f"({', '.join(f'{fp}={d}d' for fp, b, d in dur_bases)})"
                ),
            }
        if kinds == {FLOW_BASIS_DISCRETE}:
            return {
                "basis": FLOW_BASIS_DISCRETE,
                "reason": (
                    "duration indicates discrete quarters "
                    f"({', '.join(f'{fp}={d}d' for fp, b, d in dur_bases)})"
                ),
            }

    tol = _additive_tol(fy_v)
    additive_err = abs((q1_v + q2_v + q3_v) - fy_v)
    if additive_err <= tol:
        return {
            "basis": FLOW_BASIS_DISCRETE,
            "reason": (
                f"arithmetic additive identity |Q1+Q2+Q3−FY|={additive_err}≤{tol}"
            ),
        }

    # Existing narrow guard: Q3≈FY with non-zero Q1/Q2 → YTD mix
    if abs(q3_v - fy_v) <= max(1.0, abs(fy_v) * 1e-9) and abs(q1_v) > 0 and abs(q2_v) > 0:
        return {
            "basis": FLOW_BASIS_YTD,
            "reason": "arithmetic Q3≈FY suggests YTD cumulative mix",
        }

    # Overshoot: sum of interims exceeds FY (typical when YTD values are
    # wrongly treated as discrete CapEx/OCF slices) → YTD.
    if (q1_v + q2_v + q3_v) > fy_v + tol and fy_v >= 0 and q1_v >= 0 and q2_v >= 0 and q3_v >= 0:
        return {
            "basis": FLOW_BASIS_YTD,
            "reason": (
                f"arithmetic overshoot Q1+Q2+Q3={q1_v + q2_v + q3_v} > FY={fy_v} "
                "(YTD cumulative nested in labeled quarters)"
            ),
        }

    # Strict nested monotonic toward FY without additive identity → YTD shape.
    nested_up = q1_v < q2_v < q3_v < fy_v
    nested_down = q1_v > q2_v > q3_v > fy_v
    if nested_up or nested_down:
        return {
            "basis": FLOW_BASIS_YTD,
            "reason": (
                "arithmetic nested monotonic Q1⊄Q2⊄Q3⊄FY without additive "
                "identity — YTD cumulative shape (fiscal label not treated as discrete)"
            ),
        }

    return {
        "basis": FLOW_BASIS_UNKNOWN,
        "reason": (
            "ambiguous YTD vs discrete: no reliable duration; not additive; "
            "not nested YTD — refuse fabrication"
        ),
    }


def assess_field_derivation(
    field: str,
    fy_doc: dict[str, Any],
    q1_doc: dict[str, Any],
    q2_doc: dict[str, Any],
    q3_doc: dict[str, Any],
) -> dict[str, Any]:
    """Assess whether `field` may be derived for Q4."""
    if field in NON_DERIVABLE_FIELDS or field not in DERIVABLE_FLOW_FIELDS:
        return {
            "ok": False,
            "value": None,
            "reason_code": "NOT_APPLICABLE",
            "detail": f"{field}: not an additive quarterly flow; FY−Q1−Q2−Q3 blocked",
        }

    docs = [fy_doc, q1_doc, q2_doc, q3_doc]
    labels = ["FY", "Q1", "Q2", "Q3"]

    for lab, doc in zip(labels, docs):
        if doc is None:
            return {
                "ok": False,
                "value": None,
                "reason_code": _BLOCK_MISSING,
                "detail": f"{field}: missing {lab} period document",
            }

    ok_peri, peri_detail = _docs_perimeter_comparable(docs)
    if not ok_peri:
        return {
            "ok": False,
            "value": None,
            "reason_code": _BLOCK_AMBIGUOUS,
            "detail": f"{field}: {peri_detail}",
        }

    conflict, conflict_detail = _version_conflict(docs)
    if conflict:
        return {
            "ok": False,
            "value": None,
            "reason_code": _BLOCK_CONFLICT,
            "detail": f"{field}: restatement/version conflict — {conflict_detail}",
        }

    vals: list[float] = []
    tags: list[str | None] = []
    units: list[str | None] = []
    for lab, doc in zip(labels, docs):
        fields = doc.get("fields") or {}
        raw = fields.get(field)
        n = _num(raw)
        if n is None:
            nr = _null_reasons_map(doc).get(field)
            code = _null_code(nr) or _BLOCK_MISSING
            return {
                "ok": False,
                "value": None,
                "reason_code": code
                if code
                in (_BLOCK_AMBIGUOUS, _BLOCK_CONFLICT, _BLOCK_MISSING, "NOT_DISCLOSED")
                else _BLOCK_MISSING,
                "detail": f"{field}: {lab} value missing ({code})",
            }
        nr = _null_reasons_map(doc).get(field)
        code = _null_code(nr)
        if code in (_BLOCK_CONFLICT, _BLOCK_AMBIGUOUS):
            return {
                "ok": False,
                "value": None,
                "reason_code": code,
                "detail": f"{field}: {lab} marked {code}",
            }
        unc = _uncertainty_map(doc).get(field)
        if unc:
            return {
                "ok": False,
                "value": None,
                "reason_code": _BLOCK_AMBIGUOUS,
                "detail": f"{field}: {lab} uncertain — {unc}",
            }
        vals.append(n)
        tags.append(_lineage_tag(doc, field))
        units.append(_field_unit(doc, field))

    unit_set = {u for u in units if u}
    if len(unit_set) > 1:
        return {
            "ok": False,
            "value": None,
            "reason_code": _BLOCK_AMBIGUOUS,
            "detail": f"{field}: unit mismatch across FY/Q1/Q2/Q3: {sorted(unit_set)}",
        }

    tag_set = {t for t in tags if t}
    if len(tag_set) > 1:
        return {
            "ok": False,
            "value": None,
            "reason_code": _BLOCK_AMBIGUOUS,
            "detail": (
                f"{field}: annual vs Q definitions inconsistent — "
                f"lineage tags {sorted(tag_set)}"
            ),
        }

    fy_v, q1_v, q2_v, q3_v = vals

    q1_dur = _field_duration_days(q1_doc, field)
    q2_dur = _field_duration_days(q2_doc, field)
    q3_dur = _field_duration_days(q3_doc, field)
    q1_hint = _field_flow_basis_hint(q1_doc, field)
    q2_hint = _field_flow_basis_hint(q2_doc, field)
    q3_hint = _field_flow_basis_hint(q3_doc, field)

    classification = classify_quarterly_flow_basis(
        q1_v,
        q2_v,
        q3_v,
        fy_v,
        q1_dur=q1_dur,
        q2_dur=q2_dur,
        q3_dur=q3_dur,
        q1_hint=q1_hint,
        q2_hint=q2_hint,
        q3_hint=q3_hint,
    )
    basis = classification["basis"]

    if basis == FLOW_BASIS_UNKNOWN:
        return {
            "ok": False,
            "value": None,
            "reason_code": _BLOCK_AMBIGUOUS,
            "detail": f"{field}: {classification['reason']}",
            "flow_basis": basis,
        }

    if basis == FLOW_BASIS_YTD:
        parts = discrete_quarters_from_ytd(q1_v, q2_v, q3_v, fy_v)
        q4_v = parts["Q4"]
        formula = "Q4 = FY - Q3YTD"
        method = DERIVED_Q4_METHOD_YTD
        # CapEx (and similar cash outflows stored as positive magnitudes): negative
        # Q4d after YTD conversion implies Q3YTD > FY — inconsistent disclosures.
        # Refuse fabrication / REVIEW rather than emit negative CapEx Q4 (A2).
        _positive_outflow_fields = frozenset(
            {
                "capex",
                "dividends_paid",
                "share_repurchases",
                "business_acquisitions_cash",
                "purchases_of_investments",
            }
        )
        if field in _positive_outflow_fields and q4_v < 0 and fy_v >= 0:
            return {
                "ok": False,
                "value": None,
                "reason_code": _BLOCK_AMBIGUOUS,
                "detail": (
                    f"{field}: YTD-derived Q4={q4_v} is negative while FY≥0 "
                    f"(Q3YTD={q3_v} > FY={fy_v}) — inconsistent cumulative stack; "
                    "refuse negative CapEx/outflow Q4 (do not fabricate)"
                ),
                "flow_basis": basis,
                "formula": formula,
                "method": method,
                "discrete_parts": parts,
            }
        return {
            "ok": True,
            "value": q4_v,
            "reason_code": None,
            "detail": None,
            "unit": next(iter(unit_set), "USD"),
            "tag": next(iter(tag_set), None),
            "inputs": {"FY": fy_v, "Q1": q1_v, "Q2": q2_v, "Q3": q3_v},
            "flow_basis": basis,
            "formula": formula,
            "method": method,
            "discrete_parts": parts,
            "classification_reason": classification["reason"],
        }

    # DISCRETE
    q4_v = fy_v - q1_v - q2_v - q3_v
    return {
        "ok": True,
        "value": q4_v,
        "reason_code": None,
        "detail": None,
        "unit": next(iter(unit_set), "USD"),
        "tag": next(iter(tag_set), None),
        "inputs": {"FY": fy_v, "Q1": q1_v, "Q2": q2_v, "Q3": q3_v},
        "flow_basis": FLOW_BASIS_DISCRETE,
        "formula": "Q4 = FY - Q1 - Q2 - Q3",
        "method": DERIVED_Q4_METHOD,
        "classification_reason": classification["reason"],
    }


def _source_versions(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for d in docs:
        pk = d.get("period_key")
        out[str(pk)] = {
            "period_key": pk,
            "version_id": d.get("version_id"),
            "accession": d.get("accession"),
            "source_id": d.get("source_id"),
            "status": d.get("status"),
        }
    return out


def derive_q4_period_document(
    ticker: str,
    fiscal_year: int,
    fy_doc: dict[str, Any],
    q1_doc: dict[str, Any],
    q2_doc: dict[str, Any],
    q3_doc: dict[str, Any],
    *,
    version_id: str = "v001",
    fields: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Build a Normalized Q4 period document with derived flow fields + lineage."""
    pk = period_key_q(fiscal_year, 4)
    for lab, expected_key, doc in (
        ("FY", period_key_fy(fiscal_year), fy_doc),
        ("Q1", period_key_q(fiscal_year, 1), q1_doc),
        ("Q2", period_key_q(fiscal_year, 2), q2_doc),
        ("Q3", period_key_q(fiscal_year, 3), q3_doc),
    ):
        if doc is None:
            raise ValueError(f"missing {lab} document for {pk}")
        if doc.get("period_key") and doc.get("period_key") != expected_key:
            raise ValueError(
                f"period alignment: expected {expected_key}, got {doc.get('period_key')}"
            )

    q3_end = q3_doc.get("period_end") or q3_doc.get("period_end")
    fy_end = fy_doc.get("period_end") or fy_doc.get("period_end")
    period_end = fy_end
    period_start = None
    if q3_end:
        try:
            period_start = (
                date.fromisoformat(str(q3_end)[:10]) + timedelta(days=1)
            ).isoformat()
        except ValueError:
            period_start = None

    src_meta = _source_versions([fy_doc, q1_doc, q2_doc, q3_doc])
    # Default formula/method; per-field overrides applied from assess_field_derivation.
    formula = "Q4 = FY - Q1 - Q2 - Q3"
    primary_method = DERIVED_Q4_METHOD

    doc = blank_period_document(
        ticker,
        pk,
        version_id,
        period_type="Q",
        fiscal_year=fiscal_year,
        fiscal_period="Q4",
        period_start=period_start,
        period_end=period_end,
        filed_at=fy_doc.get("filed_at"),
        available_as_of=fy_doc.get("available_as_of") or fy_doc.get("filed_at"),
        accession=fy_doc.get("accession"),
        source_id=f"derived:{pk}:{DERIVED_Q4_METHOD}",
        cik=fy_doc.get("cik") or q3_doc.get("cik"),
        entity_name=fy_doc.get("entity_name") or q3_doc.get("entity_name"),
        gate0_class=fy_doc.get("gate0_class") or "operating",
        reporting_currency=fy_doc.get("reporting_currency") or "USD",
        statement_basis=fy_doc.get("statement_basis") or "us-gaap",
        change_reason="initial",
    )
    doc["derived"] = True
    doc["derivation_method"] = primary_method
    doc["derivation"] = {
        "method": primary_method,
        "formula": formula,
        "derived_period_key": pk,
        "inputs": src_meta,
        "evidence_kind": "MODEL_INFERENCE",  # derived — never reported FACT
        "field_flow_basis": {},
        "field_formulas": {},
    }
    doc.setdefault("field_units", {})
    doc.setdefault("null_reasons", {})
    doc["notes"] = list(doc.get("notes") or []) + [
        {
            "code": primary_method,
            "detail": (
                f"{pk} flow metrics reconstructed via duration/YTD-aware derivation "
                f"(default {formula}); derived, not reported FACT"
            ),
        }
    ]

    target_fields = fields or DERIVABLE_FLOW_FIELDS
    derived_count = 0
    blocked: dict[str, Any] = {}

    methods_used: set[str] = set()
    for field in target_fields:
        result = assess_field_derivation(field, fy_doc, q1_doc, q2_doc, q3_doc)
        if result["ok"]:
            unit = result.get("unit") or "USD"
            field_method = result.get("method") or DERIVED_Q4_METHOD
            field_formula = result.get("formula") or formula
            flow_basis = result.get("flow_basis") or FLOW_BASIS_DISCRETE
            methods_used.add(field_method)
            parts = result.get("discrete_parts") or {}
            parts_note = ""
            if parts:
                parts_note = (
                    f"; discrete_parts="
                    f"Q1d={parts.get('Q1')};Q2d={parts.get('Q2')};"
                    f"Q3d={parts.get('Q3')};Q4d={parts.get('Q4')}"
                )
            class_reason = result.get("classification_reason") or ""
            notes = (
                f"method={field_method}; formula={field_formula}; "
                f"flow_basis={flow_basis}; "
                f"derived_period_key={pk}; "
                f"inputs="
                f"FY:{src_meta.get(period_key_fy(fiscal_year), {})}; "
                f"Q1:{src_meta.get(period_key_q(fiscal_year, 1), {})}; "
                f"Q2:{src_meta.get(period_key_q(fiscal_year, 2), {})}; "
                f"Q3:{src_meta.get(period_key_q(fiscal_year, 3), {})}; "
                f"unit={unit}; evidence_kind=MODEL_INFERENCE "
                f"(derived, not reported FACT)"
                f"{parts_note}"
                + (f"; classification={class_reason}" if class_reason else "")
            )
            attach_field_with_lineage(
                doc,
                field,
                result["value"],
                source_kind="calculated",
                source_ref=f"derived:{field_method}",
                source_id=doc["source_id"],
                notes=notes,
                uncertain=False,
                review_status="pending",
                reviewed_by="machine_derived",
            )
            doc["field_units"][field] = unit
            doc["derivation"]["field_flow_basis"][field] = flow_basis
            doc["derivation"]["field_formulas"][field] = field_formula
            derived_count += 1
        else:
            code = result.get("reason_code") or _BLOCK_MISSING
            detail = result.get("detail") or "not derivable"
            blocked[field] = {
                "code": code,
                "detail": detail,
                "flow_basis": result.get("flow_basis"),
            }
            attach_field_with_lineage(
                doc,
                field,
                None,
                source_kind="calculated",
                source_ref=f"derived:{DERIVED_Q4_METHOD}:blocked",
                source_id=doc["source_id"],
                notes=f"method={DERIVED_Q4_METHOD}; blocked: {detail}",
                uncertain=True,
                review_status="pending",
                reviewed_by="machine_derived",
                null_reason={"code": code, "detail": detail},
            )

    if DERIVED_Q4_METHOD_YTD in methods_used:
        doc["derivation_method"] = DERIVED_Q4_METHOD_YTD
        doc["derivation"]["method"] = DERIVED_Q4_METHOD_YTD
        doc["derivation"]["formula"] = "Q4 = FY - Q3YTD (per YTD fields); discrete fields use FY-Q1-Q2-Q3"
        doc["source_id"] = f"derived:{pk}:{DERIVED_Q4_METHOD_YTD}"
    doc["derivation"]["methods_used"] = sorted(methods_used)

    # Explicitly do not derive BS / non-additive — leave null with NOT_APPLICABLE
    annotate_fields = sorted(
        set(NON_DERIVABLE_FIELDS)
        & set(
            list(BS_CORE_FIELDS)
            + [
                "diluted_eps",
                "shares_diluted_weighted",
                "shares_basic_weighted",
                "shares_outstanding",
            ]
        )
    )
    for field in annotate_fields:
        if doc.get("fields", {}).get(field) is not None:
            continue
        if field in (doc.get("null_reasons") or {}):
            continue
        attach_field_with_lineage(
            doc,
            field,
            None,
            source_kind="calculated",
            source_ref=f"derived:{DERIVED_Q4_METHOD}:not_applicable",
            source_id=doc["source_id"],
            notes=(
                f"method={DERIVED_Q4_METHOD}; NOT derived — "
                "balance-sheet / non-additive metric excluded from FY−Q1−Q2−Q3"
            ),
            uncertain=False,
            reviewed_by="machine_derived",
            null_reason={
                "code": "NOT_APPLICABLE",
                "detail": "Q4 snapshot/non-additive metric not derived via FY−Q1−Q2−Q3",
            },
        )

    doc["derivation"]["derived_field_count"] = derived_count
    doc["derivation"]["blocked_fields"] = blocked
    return doc


def q4_derivation_feasible(
    fy_doc: dict[str, Any] | None,
    q1_doc: dict[str, Any] | None,
    q2_doc: dict[str, Any] | None,
    q3_doc: dict[str, Any] | None,
    *,
    require_fields: tuple[str, ...] = ("revenue",),
) -> dict[str, Any]:
    """Gate whether a derived Q4 period should be created."""
    if any(d is None for d in (fy_doc, q1_doc, q2_doc, q3_doc)):
        missing = [
            lab
            for lab, d in (
                ("FY", fy_doc),
                ("Q1", q1_doc),
                ("Q2", q2_doc),
                ("Q3", q3_doc),
            )
            if d is None
        ]
        return {
            "ok": False,
            "reason_code": _BLOCK_MISSING,
            "detail": f"missing inputs: {', '.join(missing)}",
        }
    assert fy_doc and q1_doc and q2_doc and q3_doc
    ok_peri, peri_detail = _docs_perimeter_comparable(
        [fy_doc, q1_doc, q2_doc, q3_doc]
    )
    if not ok_peri:
        return {"ok": False, "reason_code": _BLOCK_AMBIGUOUS, "detail": peri_detail}
    conflict, conflict_detail = _version_conflict([fy_doc, q1_doc, q2_doc, q3_doc])
    if conflict:
        return {
            "ok": False,
            "reason_code": _BLOCK_CONFLICT,
            "detail": conflict_detail,
        }
    for field in require_fields:
        r = assess_field_derivation(field, fy_doc, q1_doc, q2_doc, q3_doc)
        if not r["ok"]:
            return {
                "ok": False,
                "reason_code": r.get("reason_code") or _BLOCK_MISSING,
                "detail": r.get("detail"),
            }
    return {"ok": True, "reason_code": None, "detail": None}


def select_contiguous_economic_quarters(
    reported: list[tuple[int, int]],
    *,
    derivable_q4_years: set[int] | frozenset[int] | None = None,
    prefer_q: int = 8,
) -> dict[str, Any]:
    """
    Prefer latest ~prefer_q *contiguous* economic quarters.

    If a full contiguous window of prefer_q is possible (using safe Q4 derivation),
    return that window. If continuity is impossible, return the longest contiguous
    suffix ending at the latest available quarter, list explicit gaps, and provide
    `fallback_reported_keys` = latest prefer_q reported-only keys.
    """
    derivable_q4_years = set(derivable_q4_years or set())
    reported_set = {(int(fy), int(q)) for fy, q in reported}
    available: set[tuple[int, int]] = set(reported_set)
    for y in derivable_q4_years:
        if (y, 4) not in available:
            available.add((y, 4))

    if not available:
        return {
            "selected": [],
            "selected_keys": [],
            "derived_q4_years_used": [],
            "contiguous": True,
            "gaps": [],
            "fallback_reported_keys": [],
            "policy": "empty",
        }

    latest = max(available, key=lambda t: economic_quarter_index(t[0], t[1]))
    window: list[tuple[int, int]] = []
    gaps: list[dict[str, Any]] = []
    fy, q = latest
    for _ in range(prefer_q):
        window.append((fy, q))
        if (fy, q) not in available:
            why = "not_reported"
            if q == 4 and fy not in derivable_q4_years:
                why = "q4_not_derivable"
            elif q == 4:
                why = "q4_marked_derivable_but_missing_from_available"
            gaps.append(
                {
                    "fiscal_year": fy,
                    "fiscal_period": f"Q{q}",
                    "period_key": period_key_q(fy, q),
                    "why": why,
                }
            )
        fy, q = step_quarter_back(fy, q)
    window.reverse()

    if not gaps:
        derived_used = [
            y for (y, qq) in window if qq == 4 and (y, 4) not in reported_set
        ]
        return {
            "selected": window,
            "selected_keys": [period_key_q(y, qq) for y, qq in window],
            "derived_q4_years_used": derived_used,
            "contiguous": True,
            "gaps": [],
            "fallback_reported_keys": [],
            "policy": (
                "contiguous_with_safe_derivation"
                if derived_used
                else "contiguous_reported"
            ),
            "latest": {"fiscal_year": latest[0], "fiscal_period": f"Q{latest[1]}"},
        }

    # Continuity broken — longest contiguous suffix ending at latest
    suffix: list[tuple[int, int]] = []
    fy, q = latest
    while (fy, q) in available:
        suffix.append((fy, q))
        if len(suffix) >= prefer_q:
            break
        fy, q = step_quarter_back(fy, q)
    suffix.reverse()

    reported_sorted = sorted(
        reported_set, key=lambda t: economic_quarter_index(t[0], t[1])
    )
    fallback = reported_sorted[-prefer_q:] if reported_sorted else []
    derived_used = [
        y for (y, qq) in suffix if qq == 4 and (y, 4) not in reported_set
    ]
    return {
        "selected": suffix,
        "selected_keys": [period_key_q(y, qq) for y, qq in suffix],
        "derived_q4_years_used": derived_used,
        "contiguous": False,
        "gaps": gaps,
        "fallback_reported_keys": [period_key_q(y, qq) for y, qq in fallback],
        "policy": "partial_contiguous_suffix_plus_gap_report",
        "latest": {"fiscal_year": latest[0], "fiscal_period": f"Q{latest[1]}"},
    }


def select_periods_prefer_contiguous(
    q_periods: list[dict[str, Any]],
    *,
    prefer_q: int = 8,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Among materialized Q period docs, prefer a contiguous window.

    If period_key values are not parseable as FY/Qn, fall back to the legacy
    latest-~prefer_q sort behavior (no invented continuity).
    """
    if not q_periods:
        return [], {"policy": "empty", "selected_keys": [], "gaps": []}

    by_key: dict[str, dict[str, Any]] = {}
    reported_pairs: list[tuple[int, int]] = []
    unparsed: list[dict[str, Any]] = []
    for p in q_periods:
        pk = p.get("period_key") or ""
        try:
            kind, fy, q = parse_period_key(pk)
        except ValueError:
            unparsed.append(p)
            continue
        if kind != "Q" or q is None:
            unparsed.append(p)
            continue
        by_key[pk] = p
        reported_pairs.append((fy, q))

    if not reported_pairs:
        # Legacy fallback for non-standard period_key shapes used in older tests
        ordered = sorted(q_periods, key=lambda d: d.get("period_key") or "")
        out = ordered[-prefer_q:] if ordered else []
        return out, {
            "policy": "fallback_unparsed_latest",
            "selected_keys": [p.get("period_key") for p in out],
            "contiguous": None,
            "gaps": [],
        }

    sel = select_contiguous_economic_quarters(
        reported_pairs,
        derivable_q4_years=set(),
        prefer_q=prefer_q,
    )
    keys = sel["selected_keys"]
    if not keys and sel.get("fallback_reported_keys"):
        keys = sel["fallback_reported_keys"]
        sel = {**sel, "policy": "fallback_latest_reported", "selected_keys": keys}
    out = [by_key[k] for k in keys if k in by_key]
    return out, sel


# Aliases for older call sites / tests
DERIVED_Q4_METHOD_ALIAS = DERIVED_Q4_METHOD
assess_field_derivation_alias = assess_field_derivation
