"""Stage 4 Q4 derivation + contiguous economic-quarter coverage (generic)."""
from __future__ import annotations

import copy

import pytest

from fa.contract import blank_period_document
from fa.history_coverage import (
    _ensure_derived_q4,
    discover_periods_from_companyfacts,
    ensure_normalized_history,
)
from fa.quarter_derivation import (
    DERIVED_Q4_METHOD,
    DERIVABLE_FLOW_FIELDS,
    NON_DERIVABLE_FIELDS,
    assess_field_derivation,
    derive_q4_period_document,
    q4_derivation_feasible,
    select_contiguous_economic_quarters,
)
from fa.stage4.calc import _select_periods, compute_stage4_metrics
from fa import storage, versioning


def _flow_doc(
    ticker: str,
    period_key: str,
    *,
    period_type: str,
    fiscal_year: int,
    fiscal_period: str,
    revenue: float,
    operating_income: float,
    net_income: float,
    accession: str,
    period_end: str,
    period_start: str | None = None,
    cash: float | None = 100.0,
    tag: str = "Revenues",
    version_id: str = "v001",
    flow_basis: str | None = "DISCRETE",
    extra_fields: dict | None = None,
) -> dict:
    # Default discrete ~90d start when Q and start omitted (W1: label alone ≠ discrete).
    if period_start is None and period_type == "Q" and period_end:
        from datetime import date, timedelta
        try:
            period_start = (
                date.fromisoformat(period_end[:10]) - timedelta(days=90)
            ).isoformat()
        except ValueError:
            period_start = None
    doc = blank_period_document(
        ticker,
        period_key,
        version_id,
        period_type=period_type,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        period_start=period_start,
        period_end=period_end,
        accession=accession,
        source_id=accession,
        cik="0000999999",
        entity_name="Synth Co",
        reporting_currency="USD",
        statement_basis="us-gaap",
        gate0_class="operating",
        fields={
            "revenue": revenue,
            "operating_income": operating_income,
            "net_income": net_income,
            "cash_and_equivalents": cash,
            "shares_diluted_weighted": 50.0,
            "diluted_eps": 1.0,
            **(extra_fields or {}),
        },
    )
    if flow_basis:
        doc["field_flow_basis"] = {
            f: flow_basis
            for f in ("revenue", "operating_income", "net_income", *list((extra_fields or {}).keys()))
        }
    doc["field_units"] = {
        "shares_diluted_weighted": "shares",
        "revenue": "USD",
        "operating_income": "USD",
        "net_income": "USD",
        "cash_and_equivalents": "USD",
    }
    doc["lineage"] = [
        {
            "field": f,
            "value": v,
            "period_key": period_key,
            "version_id": version_id,
            "source_kind": "sec_companyfacts",
            "source_ref": ref,
            "source_id": accession,
            "notes": None,
            "uncertain": False,
        }
        for f, v, ref in (
            ("revenue", revenue, f"us-gaap:{tag}"),
            ("operating_income", operating_income, "us-gaap:OperatingIncomeLoss"),
            ("net_income", net_income, "us-gaap:NetIncomeLoss"),
        )
    ]
    doc["status"] = "accepted"
    return doc


def _year_pack(ticker: str, year: int, *, fy_rev: float = 1000.0) -> dict:
    q1, q2, q3 = 200.0, 250.0, 300.0
    return {
        "FY": _flow_doc(
            ticker,
            f"FY{year}",
            period_type="FY",
            fiscal_year=year,
            fiscal_period="FY",
            revenue=fy_rev,
            operating_income=400.0,
            net_income=200.0,
            accession=f"FY-{year}",
            period_end=f"{year}-12-31",
        ),
        "Q1": _flow_doc(
            ticker,
            f"{year}Q1",
            period_type="Q",
            fiscal_year=year,
            fiscal_period="Q1",
            revenue=q1,
            operating_income=80.0,
            net_income=40.0,
            accession=f"Q-{year}-Q1",
            period_end=f"{year}-03-31",
        ),
        "Q2": _flow_doc(
            ticker,
            f"{year}Q2",
            period_type="Q",
            fiscal_year=year,
            fiscal_period="Q2",
            revenue=q2,
            operating_income=100.0,
            net_income=50.0,
            accession=f"Q-{year}-Q2",
            period_end=f"{year}-06-30",
        ),
        "Q3": _flow_doc(
            ticker,
            f"{year}Q3",
            period_type="Q",
            fiscal_year=year,
            fiscal_period="Q3",
            revenue=q3,
            operating_income=120.0,
            net_income=60.0,
            accession=f"Q-{year}-Q3",
            period_end=f"{year}-09-30",
        ),
        "Q4_expected_rev": fy_rev - q1 - q2 - q3,
    }


def test_derive_q4_flow_metrics_math_and_method():
    pack = _year_pack("SYN_Q4", 2024)
    assert q4_derivation_feasible(pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"])["ok"]
    r = assess_field_derivation("revenue", pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"])
    assert r["ok"] is True
    assert r["value"] == 250.0
    doc = derive_q4_period_document(
        "SYN_Q4", 2024, pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"]
    )
    assert doc["period_key"] == "2024Q4"
    assert doc["derived"] is True
    assert doc["derivation_method"] == DERIVED_Q4_METHOD
    assert DERIVED_Q4_METHOD == "DERIVED_Q4_FROM_FY_MINUS_Q1_Q2_Q3"
    assert doc["fields"]["revenue"] == 250.0
    assert doc["fields"]["operating_income"] == 100.0
    assert doc["fields"]["net_income"] == 50.0
    lin = next(L for L in doc["lineage"] if L["field"] == "revenue")
    assert lin["source_kind"] == "calculated"
    assert DERIVED_Q4_METHOD in (lin.get("notes") or "")


def test_balance_sheet_not_derived():
    pack = _year_pack("SYN_Q4", 2024)
    assert "cash_and_equivalents" in NON_DERIVABLE_FIELDS
    assert "cash_and_equivalents" not in DERIVABLE_FLOW_FIELDS
    a = assess_field_derivation(
        "cash_and_equivalents", pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"]
    )
    assert a["ok"] is False
    assert a["reason_code"] == "NOT_APPLICABLE"
    doc = derive_q4_period_document(
        "SYN_Q4", 2024, pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"]
    )
    assert doc["fields"].get("cash_and_equivalents") is None
    assert (doc.get("null_reasons") or {}).get("cash_and_equivalents", {}).get(
        "code"
    ) == "NOT_APPLICABLE"


def test_block_when_any_input_missing():
    pack = _year_pack("SYN_Q4", 2024)
    gate = q4_derivation_feasible(pack["FY"], pack["Q1"], None, pack["Q3"])
    assert gate["ok"] is False
    assert gate["reason_code"] == "UNKNOWN"


def test_block_unit_mismatch():
    pack = _year_pack("SYN_Q4", 2024)
    pack["Q2"]["field_units"]["revenue"] = "USD_millions"
    a = assess_field_derivation("revenue", pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"])
    assert a["ok"] is False
    assert a["reason_code"] == "MAPPING_AMBIGUOUS"
    assert "unit" in (a["detail"] or "").lower()


def test_block_annual_vs_q_definition_inconsistent():
    pack = _year_pack("SYN_Q4", 2024)
    for L in pack["FY"]["lineage"]:
        if L["field"] == "revenue":
            L["source_ref"] = "us-gaap:SalesRevenueNet"
    a = assess_field_derivation("revenue", pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"])
    assert a["ok"] is False
    assert a["reason_code"] == "MAPPING_AMBIGUOUS"


def test_block_perimeter_change():
    pack = _year_pack("SYN_Q4", 2024)
    pack["Q3"]["entity_name"] = "Other Co Divested"
    a = assess_field_derivation("revenue", pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"])
    assert a["ok"] is False
    assert a["reason_code"] == "MAPPING_AMBIGUOUS"


def test_block_restatement_version_conflict():
    pack = _year_pack("SYN_Q4", 2024)
    pack["FY"]["status"] = "conflict"
    a = assess_field_derivation("revenue", pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"])
    assert a["ok"] is False
    assert a["reason_code"] == "SOURCE_CONFLICT"


def test_block_ytd_arithmetic_ambiguous():
    """Q3≈FY is YTD shape — derive via FY−Q3YTD (Q4d≈0), never FY−(Q1+Q2+Q3)."""
    pack = _year_pack("SYN_Q4", 2024)
    # Strip discrete duration so Q3≈FY arithmetic drives YTD classification
    for key in ("Q1", "Q2", "Q3", "FY"):
        pack[key]["period_start"] = None
        pack[key].pop("field_flow_basis", None)
    pack["Q3"]["fields"]["revenue"] = pack["FY"]["fields"]["revenue"]
    for L in pack["Q3"]["lineage"]:
        if L["field"] == "revenue":
            L["value"] = pack["Q3"]["fields"]["revenue"]
    a = assess_field_derivation("revenue", pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"])
    assert a["ok"] is True
    assert a["flow_basis"] == "YTD"
    assert a["value"] == 0.0  # FY - Q3YTD when Q3YTD == FY
    assert a["method"] == "DERIVED_Q4_FROM_FY_MINUS_Q3YTD"
    # Pre-fix wrong identity would be FY - Q1 - Q2 - Q3 = -Q1-Q2 ≠ 0
    fy = pack["FY"]["fields"]["revenue"]
    q1 = pack["Q1"]["fields"]["revenue"]
    q2 = pack["Q2"]["fields"]["revenue"]
    q3 = pack["Q3"]["fields"]["revenue"]
    assert fy - q1 - q2 - q3 != 0.0


def test_eps_and_shares_not_derived():
    pack = _year_pack("SYN_Q4", 2024)
    for field in ("diluted_eps", "shares_diluted_weighted"):
        a = assess_field_derivation(field, pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"])
        assert a["ok"] is False
        assert a["reason_code"] == "NOT_APPLICABLE"


def test_provenance_never_presents_derived_as_reported_fact():
    pack = _year_pack("SYN_Q4", 2024)
    doc = derive_q4_period_document(
        "SYN_Q4", 2024, pack["FY"], pack["Q1"], pack["Q2"], pack["Q3"]
    )
    assert doc.get("derived") is True
    assert doc.get("derivation_method") == DERIVED_Q4_METHOD
    assert doc["derivation"]["evidence_kind"] in {"MODEL_INFERENCE", "MODEL_INFERENCE"}
    for L in doc["lineage"]:
        if L.get("value") is not None and L["field"] in DERIVABLE_FLOW_FIELDS:
            assert L["source_kind"] == "calculated"
            assert DERIVED_Q4_METHOD in (L.get("notes") or "")


def test_contiguous_policy_prefers_derived_q4_bridge():
    reported = [
        (2023, 1),
        (2023, 2),
        (2023, 3),
        (2024, 1),
        (2024, 2),
        (2024, 3),
        (2025, 1),
        (2025, 2),
        (2025, 3),
        (2026, 1),
    ]
    sel = select_contiguous_economic_quarters(
        reported, derivable_q4_years={2023, 2024, 2025}, prefer_q=8
    )
    assert sel["contiguous"] is True
    assert sel["selected_keys"] == [
        "2024Q2",
        "2024Q3",
        "2024Q4",
        "2025Q1",
        "2025Q2",
        "2025Q3",
        "2025Q4",
        "2026Q1",
    ]
    assert sel["derived_q4_years_used"] == [2024, 2025]


def test_contiguous_impossible_keeps_available_and_reports_gap():
    reported = [
        (2024, 1),
        (2024, 2),
        (2024, 3),
        (2025, 1),
        (2025, 3),
        (2026, 1),
    ]
    sel = select_contiguous_economic_quarters(
        reported, derivable_q4_years={2024}, prefer_q=8
    )
    assert sel["contiguous"] is False
    assert sel["gaps"]
    assert sel["fallback_reported_keys"]
    assert "2025Q2" not in sel["selected_keys"]


def test_discover_and_ensure_contiguous_with_derivation(fa_root):
    rev_rows = []
    for y in range(2021, 2026):
        rev_rows.append(
            {
                "fy": y,
                "fp": "FY",
                "form": "10-K",
                "end": f"{y}-12-31",
                "start": f"{y}-01-01",
                "val": 1000.0 + (y - 2021) * 10,
                "accn": f"000-{y}",
                "filed": f"{y + 1}-02-15",
            }
        )
    q_specs = [
        (2023, "Q1", "2023-01-01", "2023-03-31"),
        (2023, "Q2", "2023-04-01", "2023-06-30"),
        (2023, "Q3", "2023-07-01", "2023-09-30"),
        (2024, "Q1", "2024-01-01", "2024-03-31"),
        (2024, "Q2", "2024-04-01", "2024-06-30"),
        (2024, "Q3", "2024-07-01", "2024-09-30"),
        (2025, "Q1", "2025-01-01", "2025-03-31"),
        (2025, "Q2", "2025-04-01", "2025-06-30"),
        (2025, "Q3", "2025-07-01", "2025-09-30"),
        (2026, "Q1", "2026-01-01", "2026-03-31"),
    ]
    for i, (fy, fp, start, end) in enumerate(q_specs):
        portion = {"Q1": 0.2, "Q2": 0.25, "Q3": 0.3}[fp]
        fy_val = 1000.0 + (fy - 2021) * 10 if fy <= 2025 else 250.0
        rev_rows.append(
            {
                "fy": fy,
                "fp": fp,
                "form": "10-Q",
                "end": end,
                "start": start,
                "val": fy_val * portion if fy <= 2025 else 250.0 + i,
                "accn": f"Q-{fy}-{fp}",
                "filed": f"{end[:7]}-28",
            }
        )
    facts = {
        "cik": 9999992,
        "entityName": "Synth Contiguous",
        "facts": {"us-gaap": {"Revenues": {"units": {"USD": rev_rows}}}},
    }
    d = discover_periods_from_companyfacts(facts, prefer_fy=5, prefer_q=8)
    q_keys = [p["period_key"] for p in d["q_periods"]]
    assert d["contiguous"] is True
    assert "2024Q4" in q_keys and "2025Q4" in q_keys
    derived_flags = {p["period_key"]: p.get("derived") for p in d["q_periods"]}
    assert derived_flags.get("2024Q4") is True
    assert derived_flags.get("2025Q4") is True

    storage.ensure_company_layout("SYN_CONT", fa_root, entity_name="Synth Contiguous")
    rep = ensure_normalized_history(
        "SYN_CONT",
        root=fa_root,
        prefer_fy=5,
        prefer_q=8,
        companyfacts=facts,
        accept=True,
    )
    assert "2024Q4" in (rep.get("derived_q4") or []) or "2024Q4" in (
        rep.get("created") or []
    )
    cur = storage.load_current_period("SYN_CONT", "2024Q4", fa_root)
    assert cur is not None
    assert cur.get("derived") is True
    assert cur.get("derivation_method") == DERIVED_Q4_METHOD
    assert cur["fields"]["revenue"] is not None
    lin = next(L for L in cur["lineage"] if L["field"] == "revenue")
    assert lin["source_kind"] == "calculated"


def test_prefer_reported_q4_over_derived(fa_root):
    pack = _year_pack("SYN_REP", 2024)
    storage.ensure_company_layout("SYN_REP", fa_root)
    for key in ("FY", "Q1", "Q2", "Q3"):
        doc = pack[key]
        versioning.create_initial_version(
            "SYN_REP", doc["period_key"], doc, accept=True, root=fa_root
        )
    reported_q4 = _flow_doc(
        "SYN_REP",
        "2024Q4",
        period_type="Q",
        fiscal_year=2024,
        fiscal_period="Q4",
        revenue=999.0,
        operating_income=1.0,
        net_income=1.0,
        accession="Q-2024-Q4-REPORTED",
        period_end="2024-12-31",
    )
    reported_q4["derived"] = False
    versioning.create_initial_version(
        "SYN_REP", "2024Q4", reported_q4, accept=True, root=fa_root
    )
    report = {
        "skipped": [],
        "q4_derivation": [],
        "failed": [],
        "created": [],
        "derived_q4": [],
    }
    out = _ensure_derived_q4(
        "SYN_REP", 2024, root=fa_root, accept=True, report=report
    )
    cur = storage.load_current_period("SYN_REP", "2024Q4", fa_root)
    assert cur["fields"]["revenue"] == 999.0
    assert not cur.get("derived")
    assert out["fields"]["revenue"] == 999.0


def test_stage4_calc_uses_contiguous_quarters():
    periods = []
    for y in range(2021, 2026):
        periods.append(
            {
                "period_key": f"FY{y}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {"revenue": 1000 + y},
            }
        )
    for pk, rev in [
        ("2023Q3", 1),
        ("2024Q1", 2),
        ("2024Q2", 3),
        ("2024Q3", 4),
        ("2024Q4", 5),
        ("2025Q1", 6),
        ("2025Q2", 7),
        ("2025Q3", 8),
        ("2025Q4", 9),
        ("2026Q1", 10),
    ]:
        periods.append(
            {
                "period_key": pk,
                "period_type": "Q",
                "version_id": "v1",
                "fields": {"revenue": rev},
                "derived": pk.endswith("Q4"),
                "derivation_method": DERIVED_Q4_METHOD if pk.endswith("Q4") else None,
            }
        )
    fy, q, flags = _select_periods(periods, prefer_fy=5, prefer_q=8)
    assert [p["period_key"] for p in q] == [
        "2024Q2",
        "2024Q3",
        "2024Q4",
        "2025Q1",
        "2025Q2",
        "2025Q3",
        "2025Q4",
        "2026Q1",
    ]
    assert flags.get("quarters_contiguous") is True
    r = compute_stage4_metrics(periods)
    assert [x["period_key"] for x in r.metrics["revenue_q_series"]] == [
        "2024Q2",
        "2024Q3",
        "2024Q4",
        "2025Q1",
        "2025Q2",
        "2025Q3",
        "2025Q4",
        "2026Q1",
    ]
