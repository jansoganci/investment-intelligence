"""Session-aware market-data freshness + provenance (Plan §0.H).

Labels: CURRENT | RECENT | STALE | UNKNOWN.
Hour/day bands = RESEARCH_CANDIDATE / NOT_LOCKED — clearly labeled.
Never silent fresh-price / stale-CS mix. Currency reconcile required.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from zoneinfo import ZoneInfo

# RESEARCH_CANDIDATE / NOT_LOCKED — calibration defaults only; not production gates.
RESEARCH_CANDIDATE_OPEN_SESSION_CURRENT_HOURS = 6
RESEARCH_CANDIDATE_OPEN_SESSION_RECENT_HOURS = 24
RESEARCH_CANDIDATE_CLOSED_SESSION_RECENT_DAYS = 3

_IST = ZoneInfo("Europe/Istanbul")
_ET = ZoneInfo("America/New_York")


def _parse_as_of(as_of: str | datetime | None) -> datetime | None:
    if as_of is None:
        return None
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None:
            return as_of.replace(tzinfo=timezone.utc)
        return as_of.astimezone(timezone.utc)
    s = str(as_of).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _us_equity_session_open(now_utc: datetime) -> bool:
    """Rough US equity regular-session check (ET Mon–Fri 09:30–16:00). NOT_LOCKED."""
    et = now_utc.astimezone(_ET)
    if et.weekday() >= 5:
        return False
    minutes = et.hour * 60 + et.minute
    return (9 * 60 + 30) <= minutes < (16 * 60)


def classify_staleness(
    *,
    as_of: str | datetime | None,
    now: datetime | None = None,
    source: str | None = None,
    delay_note: str | None = None,
) -> tuple[str, str]:
    """Return (staleness_class, why). Session-aware — not naive clock hours."""
    now_utc = now or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    dt = _parse_as_of(as_of)
    if dt is None:
        return "UNKNOWN", "Missing or unparseable as_of — cannot classify freshness"
    if not source:
        return "UNKNOWN", "as_of present but source missing — provenance incomplete"

    age = now_utc - dt
    open_sess = _us_equity_session_open(now_utc)

    if open_sess:
        hours = age.total_seconds() / 3600.0
        if hours <= RESEARCH_CANDIDATE_OPEN_SESSION_CURRENT_HOURS:
            note = f"open session; age≈{hours:.1f}h"
            if delay_note:
                note += f"; delay_note={delay_note}"
            return "CURRENT", note
        if hours <= RESEARCH_CANDIDATE_OPEN_SESSION_RECENT_HOURS:
            return (
                "RECENT",
                f"open session; age≈{hours:.1f}h (RESEARCH_CANDIDATE band; delay ok if labeled)",
            )
        return (
            "STALE",
            f"open session with prior/aged quote age≈{hours:.1f}h — lean STALE for price-sensitive conclusions",
        )

    # Overnight / weekend / holiday: official close must NOT become STALE merely by clock hours
    days = age.total_seconds() / 86400.0
    if days <= RESEARCH_CANDIDATE_CLOSED_SESSION_RECENT_DAYS:
        return (
            "CURRENT",
            f"closed/overnight session; official close age≈{days:.2f}d remains CURRENT/RECENT for research "
            f"(RESEARCH_CANDIDATE closed band={RESEARCH_CANDIDATE_CLOSED_SESSION_RECENT_DAYS}d)",
        )
    if days <= 7:
        return "RECENT", f"closed session; age≈{days:.1f}d — RECENT for research"
    return "STALE", f"closed session; age≈{days:.1f}d — STALE for price-sensitive IV/MoS"


def build_price_provenance(
    *,
    share_price: float | None,
    currency: str | None,
    as_of: str | datetime | None,
    source: str | None,
    delay_note: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Required provenance fields for any price-using artifact."""
    now_utc = now or datetime.now(timezone.utc)
    dt = _parse_as_of(as_of)
    staleness, why = classify_staleness(
        as_of=as_of, now=now_utc, source=source, delay_note=delay_note
    )
    as_of_utc = dt.astimezone(timezone.utc).isoformat() if dt else None
    as_of_ist = dt.astimezone(_IST).isoformat() if dt else None
    return {
        "share_price": share_price,
        "currency": currency,
        "as_of_utc": as_of_utc,
        "as_of_europe_istanbul": as_of_ist,
        "source": source,
        "staleness_class": staleness,
        "staleness_why": why,
        "delay_note": delay_note,
        "provenance_complete": all(
            x is not None and x != ""
            for x in (share_price, currency, as_of_utc, source, staleness)
        ),
    }


def reconcile_currency(
    price_currency: str | None,
    reporting_currency: str | None,
) -> dict[str, Any]:
    """Explicit currency reconcile — no silent mix."""
    pc = (price_currency or "").upper().strip() or None
    rc = (reporting_currency or "").upper().strip() or None
    if pc is None or rc is None:
        return {
            "ok": False,
            "price_currency": pc,
            "reporting_currency": rc,
            "status": "UNKNOWN",
            "why": "Missing price and/or reporting currency — unresolved",
        }
    if pc == rc:
        return {
            "ok": True,
            "price_currency": pc,
            "reporting_currency": rc,
            "status": "MATCHED",
            "why": f"Price currency {pc} matches reporting currency {rc}",
        }
    return {
        "ok": False,
        "price_currency": pc,
        "reporting_currency": rc,
        "status": "MISMATCH",
        "why": f"Currency mismatch price={pc} vs reporting={rc} — no silent FX; exception",
    }


def capital_structure_freshness_notes(
    *,
    filing_period_end: str | None,
    filing_as_of: str | None,
    price_staleness: str,
    post_period_events: list[str] | None = None,
    post_period_evidence_status: str | None = None,
    post_period_event_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Filing-period CS labeling + post-period flags. Never pretend real-time CS.

    Wave 3 / B3: empty `post_period_events` must NOT imply search established "none"
    when evidence is insufficient — see `post_period_evidence_status`.
    """
    events = list(post_period_events or [])
    records = list(post_period_event_records or [])
    evidence_status = post_period_evidence_status or (
        "events_found" if events else "unspecified_empty"
    )
    material_stale_cs = False
    why_parts = [
        f"CS from filing period_end={filing_period_end or 'UNKNOWN'}; "
        f"filing_as_of={filing_as_of or 'UNKNOWN'} — not same-day market data"
    ]
    if events:
        why_parts.append(f"post_period_material_events={events}")
        material_stale_cs = True
    else:
        # Honesty: empty list ≠ proven absence
        if evidence_status in {
            "insufficient_evidence",
            "no_post_cs_interim_available",
            "unspecified_empty",
            "caller_supplied_empty_unverified",
        }:
            why_parts.append(
                f"post_period_events empty with evidence_status={evidence_status} — "
                "does NOT establish that no material post-period events exist"
            )
        elif evidence_status == "searched_none_material":
            why_parts.append(
                "post_period search of later interim Normalized found no material "
                "debt/shares/acquisition deltas vs CS statement date"
            )
    # If price is CURRENT/RECENT but CS period_end is very old relative to price, flag mix risk
    silent_mix_risk = False
    if price_staleness in {"CURRENT", "RECENT"} and not filing_period_end:
        silent_mix_risk = True
        why_parts.append("fresh price with undated CS — silent-mix risk")
        material_stale_cs = True
    return {
        "filing_period_end": filing_period_end,
        "filing_as_of": filing_as_of,
        "post_period_events": events,
        "post_period_event_records": records,
        "post_period_evidence_status": evidence_status,
        "material_stale_cs_risk": material_stale_cs,
        "silent_mix_risk": silent_mix_risk,
        "why": "; ".join(why_parts),
        "never_silent_fresh_price_stale_cs": True,
        "empty_events_not_proof_of_none": evidence_status
        not in {"searched_none_material", "events_found"},
    }


def price_sensitive_allowed(staleness_class: str, currency_ok: bool) -> tuple[bool, str]:
    """Suppress price-sensitive IV/MoS when freshness/currency fails."""
    if not currency_ok:
        return False, "Currency unresolved — suppress price-sensitive IV/MoS"
    if staleness_class in {"STALE", "UNKNOWN"}:
        return (
            False,
            f"Price freshness={staleness_class} — no price-sensitive IV/MoS conclusion; exception queue",
        )
    if staleness_class in {"CURRENT", "RECENT"}:
        return True, f"Freshness={staleness_class} — price-sensitive exhibits allowed with provenance"
    return False, f"Unexpected staleness={staleness_class} — suppress"


def _period_sort_key(p: dict[str, Any]) -> str:
    return str(p.get("period_end") or p.get("period_key") or "")


def _gross_debt_from_fields(fields: dict[str, Any]) -> float | None:
    td = fields.get("total_debt")
    if td is not None:
        try:
            return float(td)
        except (TypeError, ValueError):
            pass
    parts = []
    for k in ("long_term_debt", "short_term_debt", "secured_debt"):
        v = fields.get(k)
        if v is not None:
            try:
                parts.append(float(v))
            except (TypeError, ValueError):
                pass
    return sum(parts) if parts else None


def detect_material_post_period_events(
    periods: list[dict[str, Any]],
    *,
    cs_period_key: str | None,
    cs_period_end: str | None = None,
    cs_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """General post-period material-event detector (Wave 3 / B3).

    Historical CS bases stay on the statement-date period. Material post-period
    events are *separate* evidence (not a silent CS advance).

    No ticker hardcodes. DHR/Masimo is a regression example only.
    """
    records: list[dict[str, Any]] = []
    events: list[str] = []

    if not periods:
        return {
            "events": [],
            "event_records": [],
            "evidence_status": "insufficient_evidence",
            "why": "No Normalized periods available to search for post-period events",
        }

    # Identify CS anchor period
    cs_period = None
    if cs_period_key:
        for p in periods:
            if p.get("period_key") == cs_period_key:
                cs_period = p
                break
    if cs_period is None:
        fy = sorted(
            [p for p in periods if p.get("period_type") == "FY"],
            key=_period_sort_key,
        )
        cs_period = fy[-1] if fy else None

    if cs_period is None:
        return {
            "events": [],
            "event_records": [],
            "evidence_status": "insufficient_evidence",
            "why": "CS anchor period unavailable — cannot judge post-period deltas",
        }

    cs_key = cs_period.get("period_key")
    cs_end = cs_period_end or cs_period.get("period_end")
    cs_f = dict(cs_fields or cs_period.get("fields") or {})
    cs_debt = _gross_debt_from_fields(cs_f)
    cs_shares = None
    for sk in ("shares_outstanding", "shares_diluted_weighted"):
        if cs_f.get(sk) is not None:
            try:
                cs_shares = float(cs_f[sk])
                break
            except (TypeError, ValueError):
                pass

    # Later periods: any period with period_end > cs_end, or interim after CS key
    later: list[dict[str, Any]] = []
    for p in periods:
        if p.get("period_key") == cs_key:
            continue
        pe = p.get("period_end")
        if cs_end and pe and str(pe) > str(cs_end):
            later.append(p)
        elif (not cs_end) and cs_key and str(p.get("period_key") or "") > str(cs_key):
            # Fallback lexicographic on period_key when ends missing
            later.append(p)

    if not later:
        return {
            "events": [],
            "event_records": [],
            "evidence_status": "no_post_cs_interim_available",
            "why": (
                f"No Normalized period after CS {cs_key}/{cs_end} — "
                "empty events does NOT prove absence of post-period corporate actions"
            ),
            "cs_period_key": cs_key,
            "cs_period_end": cs_end,
        }

    later = sorted(later, key=_period_sort_key)
    fields_incomplete = False

    for p in later:
        fields = p.get("fields") or {}
        pk = p.get("period_key")
        pe = p.get("period_end")
        filed = p.get("filed_at") or p.get("available_as_of")
        # Acquisition cash (interim / post-FY)
        acq = fields.get("business_acquisitions_cash")
        try:
            acq_f = float(acq) if acq is not None else None
        except (TypeError, ValueError):
            acq_f = None
        if acq_f is not None and acq_f > 0:
            # Material if absolute > $500M or >5% of CS debt (when known)
            material = acq_f >= 500_000_000
            if cs_debt and cs_debt > 0 and (acq_f / cs_debt) >= 0.05:
                material = True
            if material:
                rec = {
                    "type": "acquisition",
                    "relationship": "post_period_vs_cs_statement_date",
                    "event_date": pe,
                    "source": f"Normalized:{pk}",
                    "filed_at": filed,
                    "status": "disclosed_in_interim_normalized",
                    "metrics": {
                        "business_acquisitions_cash": acq_f,
                        "cs_period_key": cs_key,
                    },
                }
                records.append(rec)
                events.append(
                    f"acquisition_cash={acq_f:.0f} in {pk} (period_end={pe}) after CS {cs_key}"
                )

        # Debt step-up / paydown
        debt = _gross_debt_from_fields(fields)
        if debt is None and cs_debt is not None:
            # Interim present but debt fields missing → uncertainty, not "none"
            if p.get("period_type") != "FY":
                fields_incomplete = True
        if debt is not None and cs_debt is not None and cs_debt > 0:
            delta = debt - cs_debt
            abs_delta = abs(delta)
            pct = abs_delta / cs_debt
            if abs_delta >= 1_000_000_000 or pct >= 0.10:
                direction = "increase" if delta > 0 else "decrease"
                rec = {
                    "type": "financing_debt_change",
                    "relationship": "post_period_vs_cs_statement_date",
                    "event_date": pe,
                    "source": f"Normalized:{pk}",
                    "filed_at": filed,
                    "status": "disclosed_in_interim_normalized",
                    "metrics": {
                        "cs_gross_debt": cs_debt,
                        "interim_gross_debt": debt,
                        "delta": delta,
                        "direction": direction,
                        "cs_period_key": cs_key,
                    },
                }
                records.append(rec)
                events.append(
                    f"debt_{direction}={delta:.0f} ({pct:.1%}) in {pk} vs CS {cs_key}"
                )

        # Share count change
        sh = None
        for sk in ("shares_outstanding", "shares_diluted_weighted"):
            if fields.get(sk) is not None:
                try:
                    sh = float(fields[sk])
                    break
                except (TypeError, ValueError):
                    pass
        if sh is not None and cs_shares is not None and cs_shares > 0:
            sh_delta = sh - cs_shares
            sh_pct = abs(sh_delta) / cs_shares
            if sh_pct >= 0.01:  # ≥1% share change
                direction = "issuance_or_dilution" if sh_delta > 0 else "buyback_or_shrink"
                rec = {
                    "type": "share_count_change",
                    "relationship": "post_period_vs_cs_statement_date",
                    "event_date": pe,
                    "source": f"Normalized:{pk}",
                    "filed_at": filed,
                    "status": "disclosed_in_interim_normalized",
                    "metrics": {
                        "cs_shares": cs_shares,
                        "interim_shares": sh,
                        "delta": sh_delta,
                        "direction": direction,
                        "cs_period_key": cs_key,
                    },
                }
                records.append(rec)
                events.append(
                    f"shares_{direction}={sh_delta:.0f} ({sh_pct:.1%}) in {pk} vs CS {cs_key}"
                )

    if events:
        status = "events_found"
        why = f"Material post-period events vs CS {cs_key}/{cs_end}: {len(events)}"
    elif fields_incomplete:
        status = "insufficient_evidence"
        why = (
            f"Later periods after CS {cs_key} exist but key debt/CS fields incomplete — "
            "empty events does NOT establish none"
        )
    else:
        status = "searched_none_material"
        why = (
            f"Searched {len(later)} post-CS period(s); no material debt/shares/acquisition "
            "deltas vs CS statement date under v1 thresholds"
        )

    return {
        "events": events,
        "event_records": records,
        "evidence_status": status,
        "why": why,
        "cs_period_key": cs_key,
        "cs_period_end": cs_end,
        "later_period_keys": [p.get("period_key") for p in later],
    }
