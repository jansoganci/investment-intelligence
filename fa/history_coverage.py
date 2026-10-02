"""Generic Normalized history coverage from SEC companyfacts.

Target ~5 FY + ~8 contiguous economic quarters when official data exists.
No ticker hardcodes. Does not fabricate periods. Failed periods → UNKNOWN
with explicit reason. Missing fiscal Q4 flow metrics may be derived as
Q4 = FY − Q1 − Q2 − Q3 when safe (see quarter_derivation).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from . import config, storage, versioning
from .ids import normalize_ticker, period_key_fy, period_key_q
from .map_companyfacts import (
    TAG_MAP,
    _facts_for_mapping,
    map_companyfacts_to_period,
)
from .quarter_derivation import (
    DERIVED_Q4_METHOD,
    derive_q4_period_document,
    parse_period_key,
    q4_derivation_feasible,
    select_contiguous_economic_quarters,
)
from .sec_client import get_companyfacts, resolve_cik


SHARE_FIELDS = (
    "shares_diluted_weighted",
    "shares_basic_weighted",
    "shares_outstanding",
)

# Annual forms for FY discovery — 20-F for IFRS FPIs (e.g. RIO); no ticker hardcodes.
FY_ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A")


def _duration_days(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        return (date.fromisoformat(str(end)[:10]) - date.fromisoformat(str(start)[:10])).days
    except ValueError:
        return None


def _revenue_series(companyfacts: dict) -> list[dict]:
    """Return the best revenue USD series for period discovery.

    Prefer the TAG_MAP revenue tag whose FY annual-form rows (10-K/20-F family)
    have the *latest* period end. First-nonempty was wrong when an older ASC-606
    tag stops updating while a later tag (e.g. Revenues) continues — discovery
    would freeze on stale years. When latest FY ends tie, earlier TAG_MAP order
    wins (stable). IFRS FPI 20-F revenue tags participate via TAG_MAP aliases.
    """
    gaap = _facts_for_mapping(companyfacts)
    ranked: list[tuple[str, list[dict]]] = []
    fallback: list[dict] = []
    for tag in TAG_MAP.get("revenue", []):
        node = gaap.get(tag)
        if not node:
            continue
        units = node.get("units") or {}
        series = units.get("USD") or next(iter(units.values()), None)
        if not series:
            continue
        series_list = list(series)
        fy_ends = [
            (r.get("end") or "")
            for r in series_list
            if r.get("fp") == "FY" and r.get("form") in FY_ANNUAL_FORMS
        ]
        if fy_ends:
            ranked.append((max(fy_ends), series_list))
        elif not fallback:
            fallback = series_list
    if ranked:
        ranked.sort(key=lambda t: t[0], reverse=True)
        return ranked[0][1]
    return fallback


def _candidate_derivable_q4_years(
    fy_years: set[int],
    reported_q: set[tuple[int, int]],
) -> set[int]:
    """Years where FY + Q1 + Q2 + Q3 are present in discovery and Q4 is not reported."""
    out: set[int] = set()
    for y in fy_years:
        if (y, 4) in reported_q:
            continue  # prefer reported Q4
        if all((y, q) in reported_q for q in (1, 2, 3)):
            out.add(y)
    return out


def discover_periods_from_companyfacts(
    companyfacts: dict,
    *,
    prefer_fy: int = 6,
    prefer_q: int = 8,
) -> dict[str, Any]:
    """
    Discover available FY and quarterly period keys from companyfacts revenue tags.

    Quarterly selection prefers the latest ~prefer_q *contiguous economic quarters*,
    using safe Q4 derivation candidates (FY+Q1+Q2+Q3 present, no reported Q4) to
    bridge fiscal year-ends. Does not invent values here — derivation happens in
    ensure_normalized_history. If continuity is impossible, falls back to latest
    available reported quarters and records gap reasons.
    """
    series = _revenue_series(companyfacts)
    fy_best: dict[int, dict[str, Any]] = {}
    for row in series:
        if row.get("fp") != "FY":
            continue
        if row.get("form") not in FY_ANNUAL_FORMS:
            continue
        fy = row.get("fy")
        end = row.get("end") or ""
        if fy is None or not end:
            continue
        try:
            if int(str(end)[:4]) != int(fy):
                continue
        except ValueError:
            continue
        dur = _duration_days(row.get("start"), end)
        if dur is not None and not (300 <= dur <= 400):
            continue
        score = (
            2 if row.get("form") in ("10-K", "20-F") else 1,  # prefer non-A
            row.get("filed") or "",
            1 if dur is not None else 0,
        )
        prev = fy_best.get(int(fy))
        if prev is None or score > prev["score"]:
            fy_best[int(fy)] = {
                "score": score,
                "fiscal_year": int(fy),
                "fiscal_period": "FY",
                "period_type": "FY",
                "period_key": period_key_fy(int(fy)),
                "period_end": end,
                "accession": row.get("accn"),
                "filed_at": row.get("filed"),
                "revenue_probe": row.get("val"),
            }

    q_best: dict[tuple[int, str], dict[str, Any]] = {}
    for row in series:
        fp = row.get("fp")
        if fp not in ("Q1", "Q2", "Q3", "Q4"):
            continue
        if row.get("form") not in ("10-Q", "10-Q/A"):
            continue
        fy = row.get("fy")
        end = row.get("end") or ""
        if fy is None or not end:
            continue
        dur = _duration_days(row.get("start"), end)
        if dur is None or not (70 <= dur <= 110):
            continue
        try:
            end_year = int(str(end)[:4])
        except ValueError:
            continue
        # Calendar / Dec FYE: end_year == fy for Q1–Q4.
        # Non-Dec FYE: quarters may end in calendar fy-1 (Jan FYE: Q1–Q3 end
        # in prior calendar year; Sep FYE: often Q1). Reject fy-2+ comparatives.
        aligned = end_year == int(fy)
        prior_calendar = end_year == int(fy) - 1
        if not aligned and not prior_calendar:
            continue
        qnum = int(fp[1])
        score = (
            2 if aligned else (1 if prior_calendar else 0),
            1 if row.get("form") == "10-Q" else 0,
            row.get("filed") or "",
        )
        key = (int(fy), fp)
        prev = q_best.get(key)
        if prev is None or score > prev["score"]:
            q_best[key] = {
                "score": score,
                "fiscal_year": int(fy),
                "fiscal_period": fp,
                "period_type": "Q",
                "period_key": period_key_q(int(fy), qnum),
                "period_end": end,
                "accession": row.get("accn"),
                "filed_at": row.get("filed"),
                "revenue_probe": row.get("val"),
                "derived": False,
            }

    fy_list = [fy_best[y] for y in sorted(fy_best)]
    q_list = [q_best[k] for k in sorted(q_best)]
    fy_sel = fy_list[-prefer_fy:] if fy_list else []

    reported_pairs = [
        (int(m["fiscal_year"]), int(str(m["fiscal_period"])[1]))
        for m in q_list
    ]
    fy_years = {int(m["fiscal_year"]) for m in fy_list}
    reported_set = set(reported_pairs)
    derivable_years = _candidate_derivable_q4_years(fy_years, reported_set)

    contiguous = select_contiguous_economic_quarters(
        reported_pairs,
        derivable_q4_years=derivable_years,
        prefer_q=prefer_q,
    )

    # Build q_sel metas: reported from q_best; derived Q4 as placeholders
    q_by_pair = {
        (int(m["fiscal_year"]), int(str(m["fiscal_period"])[1])): m for m in q_list
    }
    q_sel: list[dict[str, Any]] = []
    selected_pairs = contiguous.get("selected") or []
    if not selected_pairs and contiguous.get("fallback_reported_keys"):
        # Continuity impossible — keep latest available reported (no invented continuity)
        for pk in contiguous["fallback_reported_keys"]:
            kind, fy, q = parse_period_key(pk)
            if kind == "Q" and q is not None and (fy, q) in q_by_pair:
                q_sel.append(dict(q_by_pair[(fy, q)]))
        policy = "fallback_latest_reported"
    else:
        for fy, q in selected_pairs:
            if (fy, q) in q_by_pair:
                q_sel.append(dict(q_by_pair[(fy, q)]))
            elif q == 4 and fy in derivable_years:
                fy_meta = fy_best.get(fy) or {}
                q_sel.append(
                    {
                        "score": (0, 0, ""),
                        "fiscal_year": fy,
                        "fiscal_period": "Q4",
                        "period_type": "Q",
                        "period_key": period_key_q(fy, 4),
                        "period_end": fy_meta.get("period_end"),
                        "accession": None,
                        "filed_at": fy_meta.get("filed_at"),
                        "revenue_probe": None,
                        "derived": True,
                        "derivation_method": DERIVED_Q4_METHOD,
                    }
                )
        policy = contiguous.get("policy") or "contiguous"

    # Ensure FY years needed for selected derived Q4s are in fy_sel
    needed_fy = {m["fiscal_year"] for m in q_sel if m.get("derived")}
    fy_sel_keys = {m["fiscal_year"] for m in fy_sel}
    for y in sorted(needed_fy):
        if y not in fy_sel_keys and y in fy_best:
            fy_sel.append(fy_best[y])
            fy_sel_keys.add(y)
    fy_sel = sorted(fy_sel, key=lambda m: m["fiscal_year"])
    # Keep prefer_fy window but never drop FYs required for selected derived Q4
    if len(fy_sel) > prefer_fy:
        required = {m["fiscal_year"] for m in q_sel if m.get("derived")}
        keep = [m for m in fy_sel if m["fiscal_year"] in required]
        rest = [m for m in fy_sel if m["fiscal_year"] not in required]
        fy_sel = (rest[-(prefer_fy - len(keep)) :] if prefer_fy > len(keep) else []) + keep
        fy_sel = sorted(fy_sel, key=lambda m: m["fiscal_year"])

    reasons = list(contiguous.get("gaps") or [])
    return {
        "fy_available": len(fy_list),
        "q_available": len(q_list),
        "fy_periods": fy_sel,
        "q_periods": q_sel,
        "fy_all_keys": [x["period_key"] for x in fy_list],
        "q_all_keys": [x["period_key"] for x in q_list],
        "reasons": reasons,
        "quarter_policy": policy,
        "derived_q4_years_planned": list(contiguous.get("derived_q4_years_used") or []),
        "contiguous": bool(contiguous.get("contiguous", False)),
    }


def _merge_share_fields(base: dict[str, Any], mapped: dict[str, Any]) -> dict[str, Any]:
    """Copy share fields + lineage from mapped into a deep-ish copy of base CURRENT."""
    import copy

    out = copy.deepcopy(base)
    out_fields = out.setdefault("fields", {})
    mapped_fields = mapped.get("fields") or {}
    mapped_lin = mapped.get("lineage") or []
    keep_lin = [
        L
        for L in (out.get("lineage") or [])
        if L.get("field") not in SHARE_FIELDS
    ]
    for field in SHARE_FIELDS:
        if field not in mapped_fields:
            continue
        val = mapped_fields.get(field)
        out_fields[field] = val
        for L in mapped_lin:
            if L.get("field") == field:
                keep_lin.append(dict(L))
                break
        if val is not None and isinstance(out.get("null_reasons"), dict):
            out["null_reasons"].pop(field, None)
    out["lineage"] = keep_lin
    units = out.setdefault("field_units", {})
    for field in SHARE_FIELDS:
        if out_fields.get(field) is not None:
            units[field] = "shares"
    return out


def _ensure_mapped_period(
    ticker: str,
    companyfacts: dict,
    meta: dict[str, Any],
    *,
    root: Path,
    accept: bool,
    report: dict[str, Any],
) -> dict[str, Any] | None:
    """Map+persist a reported period; return CURRENT doc or None on failure."""
    pk = meta["period_key"]
    try:
        mapped = map_companyfacts_to_period(
            companyfacts,
            ticker=ticker,
            period_key=pk,
            fiscal_year=meta["fiscal_year"],
            fiscal_period=meta["fiscal_period"],
            period_type=meta["period_type"],
            accession=meta.get("accession"),
            period_end=meta.get("period_end"),
            filed_at=meta.get("filed_at"),
        )
    except Exception as e:  # noqa: BLE001
        report["failed"].append(
            {
                "period_key": pk,
                "reason_code": "AUTOMATION_GAP",
                "detail": f"map_companyfacts_to_period failed: {e}",
            }
        )
        return None

    if mapped["fields"].get("revenue") is None:
        report["failed"].append(
            {
                "period_key": pk,
                "reason_code": "PERIOD_ALIGNMENT",
                "detail": "Mapped period has null revenue — not inventing; skipped",
            }
        )
        return None

    existing = storage.load_current_period(ticker, pk, root)
    if existing is None:
        mapped["change_reason"] = "initial"
        units = mapped.setdefault("field_units", {})
        for field in SHARE_FIELDS:
            if mapped["fields"].get(field) is not None:
                units[field] = "shares"
        versioning.create_initial_version(
            ticker, pk, mapped, accept=accept, root=root
        )
        report["created"].append(pk)
        return storage.load_current_period(ticker, pk, root)

    needs_shares = any(
        existing.get("fields", {}).get(f) is None
        and mapped.get("fields", {}).get(f) is not None
        for f in SHARE_FIELDS
    )
    if needs_shares and meta["period_type"] == "FY":
        merged = _merge_share_fields(existing, mapped)
        merged["accession"] = existing.get("accession") or mapped.get("accession")
        merged["source_id"] = existing.get("source_id") or mapped.get("source_id")
        versioning.create_superseding_version(
            ticker,
            pk,
            merged,
            change_reason="mapping_correction",
            accept=accept,
            root=root,
        )
        report["updated_shares"].append(pk)
        return storage.load_current_period(ticker, pk, root)

    report["skipped"].append(pk)
    return existing


def _ensure_derived_q4(
    ticker: str,
    fiscal_year: int,
    *,
    root: Path,
    accept: bool,
    report: dict[str, Any],
) -> dict[str, Any] | None:
    """Create derived Q4 when FY+Q1+Q2+Q3 exist and derivation is safe.

    Prefer reported Q4 if already present.
    """
    pk = period_key_q(fiscal_year, 4)
    existing = storage.load_current_period(ticker, pk, root)
    if existing is not None and not existing.get("derived"):
        # Prefer reported
        report.setdefault("q4_derivation", []).append(
            {
                "period_key": pk,
                "status": "skipped_reported_preferred",
                "detail": "Reported Q4 exists; derivation not applied",
            }
        )
        report["skipped"].append(pk)
        return existing
    if existing is not None and existing.get("derived"):
        report["skipped"].append(pk)
        return existing

    fy_doc = storage.load_current_period(ticker, period_key_fy(fiscal_year), root)
    q1_doc = storage.load_current_period(ticker, period_key_q(fiscal_year, 1), root)
    q2_doc = storage.load_current_period(ticker, period_key_q(fiscal_year, 2), root)
    q3_doc = storage.load_current_period(ticker, period_key_q(fiscal_year, 3), root)

    gate = q4_derivation_feasible(fy_doc, q1_doc, q2_doc, q3_doc)
    if not gate.get("ok"):
        report["failed"].append(
            {
                "period_key": pk,
                "reason_code": gate.get("reason_code") or "UNKNOWN",
                "detail": (
                    f"Q4 not derivable via {DERIVED_Q4_METHOD}: "
                    f"{gate.get('detail')}"
                ),
            }
        )
        report.setdefault("q4_derivation", []).append(
            {
                "period_key": pk,
                "status": "blocked",
                "reason_code": gate.get("reason_code"),
                "detail": gate.get("detail"),
            }
        )
        return None

    assert fy_doc and q1_doc and q2_doc and q3_doc
    derived = derive_q4_period_document(
        ticker, fiscal_year, fy_doc, q1_doc, q2_doc, q3_doc
    )
    if derived["fields"].get("revenue") is None:
        report["failed"].append(
            {
                "period_key": pk,
                "reason_code": "UNKNOWN",
                "detail": "Derived Q4 has null revenue — not persisting",
            }
        )
        return None

    derived["change_reason"] = "initial"
    versioning.create_initial_version(
        ticker, pk, derived, accept=accept, root=root
    )
    report["created"].append(pk)
    report.setdefault("derived_q4", []).append(pk)
    report.setdefault("q4_derivation", []).append(
        {
            "period_key": pk,
            "status": "derived",
            "method": DERIVED_Q4_METHOD,
        }
    )
    return storage.load_current_period(ticker, pk, root)


def ensure_normalized_history(
    ticker: str,
    *,
    root: Path | None = None,
    prefer_fy: int = 5,
    prefer_q: int = 8,
    companyfacts: dict | None = None,
    accept: bool = True,
    offline: bool | None = None,
) -> dict[str, Any]:
    """
    Ensure ~prefer_fy FY + ~prefer_q contiguous Q Normalized CURRENT periods exist
    when companyfacts contain official data. Derives missing fiscal Q4 flow metrics
    when FY+Q1+Q2+Q3 are comparable. Also fills share fields on existing FYs via
    mapping_correction when shares were previously unmapped.

    Generic — no production ticker branches.
    """
    ticker = normalize_ticker(ticker)
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)

    report: dict[str, Any] = {
        "ticker": ticker,
        "created": [],
        "updated_shares": [],
        "skipped": [],
        "failed": [],
        "derived_q4": [],
        "q4_derivation": [],
        "discovery": None,
        "share_concept_stage4_prefers": "shares_diluted_weighted",
    }

    if companyfacts is None:
        cik = resolve_cik(ticker, offline=offline)
        if not cik:
            report["failed"].append(
                {
                    "reason_code": "SOURCE_AVAILABILITY",
                    "detail": "Cannot resolve CIK for companyfacts history pull",
                }
            )
            return report
        # Persist CIK for filing/semantic paths
        meta = storage.load_meta(ticker, root)
        if meta.get("cik") != cik:
            meta["cik"] = cik
            storage.save_meta(ticker, meta, root)

        companyfacts = get_companyfacts(cik, offline=offline)
        if not companyfacts:
            report["failed"].append(
                {
                    "reason_code": "SOURCE_AVAILABILITY",
                    "detail": f"No companyfacts available for CIK {cik}",
                }
            )
            return report

    discovery = discover_periods_from_companyfacts(
        companyfacts, prefer_fy=prefer_fy, prefer_q=prefer_q
    )
    report["discovery"] = {
        "fy_available": discovery["fy_available"],
        "q_available": discovery["q_available"],
        "fy_selected": [p["period_key"] for p in discovery["fy_periods"]],
        "q_selected": [p["period_key"] for p in discovery["q_periods"]],
        "quarter_policy": discovery.get("quarter_policy"),
        "contiguous": discovery.get("contiguous"),
        "derived_q4_years_planned": discovery.get("derived_q4_years_planned"),
        "reasons": discovery.get("reasons"),
    }

    # Reported targets first (FY + non-derived Q), then derived Q4
    reported_targets = [
        m
        for m in list(discovery["fy_periods"]) + list(discovery["q_periods"])
        if not m.get("derived")
    ]
    derived_metas = [m for m in discovery["q_periods"] if m.get("derived")]

    if not reported_targets and not derived_metas:
        report["failed"].append(
            {
                "reason_code": "SOURCE_AVAILABILITY",
                "detail": "No FY/Q periods discoverable from companyfacts revenue tags",
            }
        )
        return report

    for meta in reported_targets:
        _ensure_mapped_period(
            ticker, companyfacts, meta, root=root, accept=accept, report=report
        )

    # Also ensure Q1–Q3 + FY for any planned derived year even if outside prefer window
    for meta in derived_metas:
        y = int(meta["fiscal_year"])
        for q in (1, 2, 3):
            qpk = period_key_q(y, q)
            if storage.load_current_period(ticker, qpk, root) is None:
                # Find meta from full discovery q_all if possible
                stub = {
                    "fiscal_year": y,
                    "fiscal_period": f"Q{q}",
                    "period_type": "Q",
                    "period_key": qpk,
                }
                # Re-discover single from companyfacts via map using stub ends
                _ensure_mapped_period(
                    ticker,
                    companyfacts,
                    stub,
                    root=root,
                    accept=accept,
                    report=report,
                )
        fypk = period_key_fy(y)
        if storage.load_current_period(ticker, fypk, root) is None:
            _ensure_mapped_period(
                ticker,
                companyfacts,
                {
                    "fiscal_year": y,
                    "fiscal_period": "FY",
                    "period_type": "FY",
                    "period_key": fypk,
                },
                root=root,
                accept=accept,
                report=report,
            )
        _ensure_derived_q4(
            ticker, y, root=root, accept=accept, report=report
        )

    return report
