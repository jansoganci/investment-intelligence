"""Wave 1 regression — F-S3-CUM-01 (FY-only cumulative) + A2/F-DERIVE-YTD-Q4-01 (YTD Q4)."""
from __future__ import annotations

from fa.contract import blank_period_document
from fa.quarter_derivation import (
    DERIVED_Q4_METHOD,
    DERIVED_Q4_METHOD_YTD,
    FLOW_BASIS_DISCRETE,
    FLOW_BASIS_YTD,
    FLOW_BASIS_UNKNOWN,
    assess_field_derivation,
    classify_quarterly_flow_basis,
    derive_q4_period_document,
    discrete_quarters_from_ytd,
)
from fa.stage3.calc import compute_stage3_metrics


def _fy(pk, ocf, ni, capex, **extra):
    doc = {
        "period_key": pk,
        "period_type": "FY",
        "version_id": "v001",
        "fields": {
            "operating_cash_flow": ocf,
            "net_income": ni,
            "capex": capex,
        },
        "field_uncertainty": {},
        "lineage": [],
    }
    doc.update(extra)
    return doc


def _q(pk, ocf, ni, capex, *, period_type="Q", **extra):
    doc = {
        "period_key": pk,
        "period_type": period_type,
        "version_id": "v001",
        "fields": {
            "operating_cash_flow": ocf,
            "net_income": ni,
            "capex": capex,
        },
        "field_uncertainty": {},
        "lineage": [],
    }
    doc.update(extra)
    return doc


# ---------------------------------------------------------------------------
# W1.1 F-S3-CUM-01 — cumulative FY-only non-overlapping
# ---------------------------------------------------------------------------


def test_w1_cumulative_excludes_ytd_interims():
    """Pre-fix failure shape: FY + nested YTD Q → cumulative must equal FY-only."""
    periods = [
        _fy("FY2023", 50, 40, 10),
        _fy("FY2024", 60, 55, 12),
        _q("2024Q3", 45, 30, 8),  # YTD-shaped interim overlapping FY2024
    ]
    r = compute_stage3_metrics(periods)
    # Series still includes interim
    assert "2024Q3" in r.metrics["period_keys"]
    assert len(r.metrics["ocf_vs_ni_series"]) == 3
    # Cumulative is FY-only
    assert r.metrics["cumulative_basis"] == "FY_only_non_overlapping"
    assert r.metrics["cumulative_period_keys"] == ["FY2023", "FY2024"]
    assert r.metrics["cumulative_ocf"] == 110  # 50+60, NOT 50+60+45
    assert r.metrics["cumulative_ni"] == 95
    assert r.metrics["cumulative_ocf_minus_ni"] == 15


def test_w1_cumulative_excludes_discrete_quarters_that_partition_fy():
    """DE-like: FY + Q1..Q4 that sum to FY must not double-count in cumulative."""
    periods = [
        _fy("FY2024", 9231, 5000, 1640),
        _q("2024Q1", -908, 1000, 362),
        _q("2024Q2", 944, 1200, 719),
        _q("2024Q3", 4139, 1400, 1043),
        _q("2024Q4", 5056, 1400, -484),  # pre-fix wrong Q4 present in series OK
    ]
    r = compute_stage3_metrics(periods)
    assert r.metrics["cumulative_ocf"] == 9231
    assert r.metrics["cumulative_ni"] == 5000
    assert set(r.metrics["cumulative_period_keys"]) == {"FY2024"}
    # Series still has quarters
    assert len(r.metrics["ocf_vs_ni_series"]) == 5


def test_w1_cumulative_cost_like_inflation_removed():
    """COST-like: 5 FY + YTD Qs → cumulative == FY sum only."""
    fys = [
        _fy("FY2021", 100, 50, 20),
        _fy("FY2022", 110, 55, 22),
        _fy("FY2023", 120, 60, 24),
        _fy("FY2024", 130, 65, 26),
        _fy("FY2025", 140, 70, 28),
    ]
    interims = [
        _q("2024Q1", 30, 15, 6),
        _q("2024Q2", 60, 30, 12),
        _q("2024Q3", 90, 45, 18),
        _q("2025Q1", 35, 18, 7),
        _q("2025Q2", 70, 35, 14),
        _q("2025Q3", 105, 52, 21),
    ]
    r = compute_stage3_metrics(fys + interims)
    assert r.metrics["cumulative_ocf"] == 600  # 100+110+120+130+140
    assert r.metrics["cumulative_ni"] == 300
    assert r.metrics["n_fy_periods"] == 5
    assert all(k.startswith("FY") for k in r.metrics["cumulative_period_keys"])
    assert len(r.metrics["per_period"]) == 11  # series intact


def test_w1_fy_only_cumulative_unchanged_when_no_interims():
    periods = [
        _fy("FY2023", 50, 40, 10),
        _fy("FY2024", 60, 55, 12),
        _fy("FY2025", 70, 50, 15),
    ]
    r = compute_stage3_metrics(periods)
    assert r.metrics["cumulative_ocf"] == 180
    assert r.metrics["cumulative_ni"] == 145
    assert r.metrics["cumulative_ocf_minus_ni"] == 35


# ---------------------------------------------------------------------------
# W1.2 A2 — YTD vs discrete Q4 derivation
# ---------------------------------------------------------------------------


def _cf_doc(ticker, pk, *, fy, fp, ptype, end, start, fields, accession):
    doc = blank_period_document(
        ticker,
        pk,
        "v001",
        period_type=ptype,
        fiscal_year=fy,
        fiscal_period=fp,
        period_start=start,
        period_end=end,
        accession=accession,
        source_id=accession,
        cik="0000315189",
        entity_name="Deere",
        reporting_currency="USD",
        statement_basis="us-gaap",
        gate0_class="operating",
        fields=dict(fields),
    )
    doc["status"] = "accepted"
    doc["field_units"] = {k: "USD" for k in fields}
    doc["lineage"] = [
        {
            "field": f,
            "value": v,
            "period_key": pk,
            "version_id": "v001",
            "source_kind": "sec_companyfacts",
            "source_ref": f"us-gaap:{f}",
            "source_id": accession,
            "notes": None,
            "uncertain": False,
        }
        for f, v in fields.items()
    ]
    return doc


def test_w1_ytd_capex_q4_not_negative_de_shape():
    """Pre-fix: DE 2024 CapEx Q4 = FY-(Q1+Q2+Q3) = -484. Post: FY-Q3YTD = +597."""
    fy = _cf_doc(
        "DE", "FY2024", fy=2024, fp="FY", ptype="FY",
        start="2023-10-30", end="2024-10-27",
        fields={"capex": 1_640_000_000, "revenue": 50_000_000_000,
                "operating_income": 10_000_000_000, "net_income": 5_000_000_000},
        accession="FY-2024",
    )
    q1 = _cf_doc(
        "DE", "2024Q1", fy=2024, fp="Q1", ptype="Q",
        start="2023-10-30", end="2024-01-28",
        fields={"capex": 362_000_000, "revenue": 12_000_000_000,
                "operating_income": 2_000_000_000, "net_income": 1_000_000_000},
        accession="Q1-2024",
    )
    q2 = _cf_doc(
        "DE", "2024Q2", fy=2024, fp="Q2", ptype="Q",
        start="2023-10-30", end="2024-04-28",  # 181d YTD
        fields={"capex": 719_000_000, "revenue": 25_000_000_000,
                "operating_income": 4_000_000_000, "net_income": 2_000_000_000},
        accession="Q2-2024",
    )
    q3 = _cf_doc(
        "DE", "2024Q3", fy=2024, fp="Q3", ptype="Q",
        start="2023-10-30", end="2024-07-28",  # 272d YTD
        fields={"capex": 1_043_000_000, "revenue": 38_000_000_000,
                "operating_income": 6_000_000_000, "net_income": 3_000_000_000},
        accession="Q3-2024",
    )
    # Pre-fix identity (must NOT be used)
    naive = 1_640_000_000 - 362_000_000 - 719_000_000 - 1_043_000_000
    assert naive == -484_000_000

    a = assess_field_derivation("capex", fy, q1, q2, q3)
    assert a["ok"] is True
    assert a["flow_basis"] == FLOW_BASIS_YTD
    assert a["value"] == 597_000_000
    assert a["method"] == DERIVED_Q4_METHOD_YTD
    assert a["formula"] == "Q4 = FY - Q3YTD"
    assert a["discrete_parts"]["Q2"] == 719_000_000 - 362_000_000
    assert a["discrete_parts"]["Q3"] == 1_043_000_000 - 719_000_000
    assert a["discrete_parts"]["Q4"] == 597_000_000

    doc = derive_q4_period_document("DE", 2024, fy, q1, q2, q3)
    assert doc["fields"]["capex"] == 597_000_000
    assert doc["fields"]["capex"] > 0
    assert doc["derivation_method"] == DERIVED_Q4_METHOD_YTD


def test_w1_ytd_formulas_q2d_q3d_q4d():
    parts = discrete_quarters_from_ytd(100, 250, 400, 550)
    assert parts == {"Q1": 100, "Q2": 150, "Q3": 150, "Q4": 150}


def test_w1_never_fy_minus_sum_of_ytd_interims():
    """NEVER Q4=FY-(Q1+Q2YTD+Q3YTD) for YTD stacks (DHR/AZO CapEx shapes)."""
    for q1, q2, q3, fy, expect_q4 in [
        (291e6, 578e6, 876e6, 1392e6, 516e6),  # DHR 2024
        (245e6, 493e6, 785e6, 1156e6, 371e6),  # DHR 2025
        (114_397_000, 490_807_000, 725_910_000, 1_072_696_000, 346_786_000),  # AZO 2024
        (247_035_000, 539_737_000, 885_623_000, 1_327_257_000, 441_634_000),  # AZO 2025
    ]:
        c = classify_quarterly_flow_basis(q1, q2, q3, fy)
        assert c["basis"] == FLOW_BASIS_YTD
        naive = fy - q1 - q2 - q3
        assert naive < 0  # pre-fix failure
        got = discrete_quarters_from_ytd(q1, q2, q3, fy)["Q4"]
        assert got == expect_q4
        assert got > 0


def test_w1_discrete_quarters_still_use_fy_minus_q1q2q3():
    fy = _cf_doc(
        "SYN", "FY2024", fy=2024, fp="FY", ptype="FY",
        start="2024-01-01", end="2024-12-31",
        fields={"revenue": 1000, "operating_income": 400, "net_income": 200, "capex": 100},
        accession="FY",
    )
    q1 = _cf_doc(
        "SYN", "2024Q1", fy=2024, fp="Q1", ptype="Q",
        start="2024-01-01", end="2024-03-31",
        fields={"revenue": 200, "operating_income": 80, "net_income": 40, "capex": 20},
        accession="Q1",
    )
    q2 = _cf_doc(
        "SYN", "2024Q2", fy=2024, fp="Q2", ptype="Q",
        start="2024-04-01", end="2024-06-30",
        fields={"revenue": 250, "operating_income": 100, "net_income": 50, "capex": 25},
        accession="Q2",
    )
    q3 = _cf_doc(
        "SYN", "2024Q3", fy=2024, fp="Q3", ptype="Q",
        start="2024-07-01", end="2024-09-30",
        fields={"revenue": 300, "operating_income": 120, "net_income": 60, "capex": 30},
        accession="Q3",
    )
    a = assess_field_derivation("revenue", fy, q1, q2, q3)
    assert a["ok"] is True
    assert a["flow_basis"] == FLOW_BASIS_DISCRETE
    assert a["value"] == 250
    assert a["method"] == DERIVED_Q4_METHOD


def test_w1_ambiguous_refuses_fabrication():
    c = classify_quarterly_flow_basis(100, 50, 30, 500)
    assert c["basis"] == FLOW_BASIS_UNKNOWN
    fy = _cf_doc(
        "SYN", "FY2024", fy=2024, fp="FY", ptype="FY",
        start=None, end="2024-12-31",
        fields={"capex": 500, "revenue": 1000, "operating_income": 1, "net_income": 1},
        accession="FY",
    )
    q1 = _cf_doc(
        "SYN", "2024Q1", fy=2024, fp="Q1", ptype="Q",
        start=None, end=None,
        fields={"capex": 100, "revenue": 100, "operating_income": 1, "net_income": 1},
        accession="Q1",
    )
    q2 = _cf_doc(
        "SYN", "2024Q2", fy=2024, fp="Q2", ptype="Q",
        start=None, end=None,
        fields={"capex": 50, "revenue": 50, "operating_income": 1, "net_income": 1},
        accession="Q2",
    )
    q3 = _cf_doc(
        "SYN", "2024Q3", fy=2024, fp="Q3", ptype="Q",
        start=None, end=None,
        fields={"capex": 30, "revenue": 30, "operating_income": 1, "net_income": 1},
        accession="Q3",
    )
    a = assess_field_derivation("capex", fy, q1, q2, q3)
    assert a["ok"] is False
    assert a["reason_code"] == "MAPPING_AMBIGUOUS"
    assert a.get("flow_basis") == FLOW_BASIS_UNKNOWN


def test_w1_no_ticker_hardcodes_in_quarter_derivation():
    from pathlib import Path
    src = Path("/workspace/investment_intelligence/fa/quarter_derivation.py").read_text()
    for tok in ('"DE"', "'DE'", '"DHR"', "'DHR'", '"AZO"', "'AZO'"):
        assert tok not in src
    map_src = Path("/workspace/investment_intelligence/fa/map_companyfacts.py").read_text()
    # duration helpers must also be ticker-agnostic
    assert "ticker ==" not in map_src or "DE" not in map_src.split("ticker ==")[1][:50]


def test_w1_fiscal_label_alone_not_discrete():
    """Without duration and without additive/nested evidence → UNKNOWN, not DISCRETE."""
    c = classify_quarterly_flow_basis(10, -5, 8, 100)
    assert c["basis"] == FLOW_BASIS_UNKNOWN


def test_w1_ytd_negative_capex_q4_blocked_not_fabricated():
    """INTU-like: Q3YTD CapEx > FY → block rather than emit negative Q4 CapEx."""
    fy = _cf_doc(
        "SYN", "FY2025", fy=2025, fp="FY", ptype="FY",
        start="2024-08-01", end="2025-07-31",
        fields={"capex": 84_000_000, "revenue": 1000, "operating_income": 1, "net_income": 1},
        accession="FY",
    )
    q1 = _cf_doc(
        "SYN", "2025Q1", fy=2025, fp="Q1", ptype="Q",
        start="2024-08-01", end="2024-10-31",
        fields={"capex": 33_000_000, "revenue": 200, "operating_income": 1, "net_income": 1},
        accession="Q1",
    )
    q2 = _cf_doc(
        "SYN", "2025Q2", fy=2025, fp="Q2", ptype="Q",
        start="2024-08-01", end="2025-01-31",
        fields={"capex": 64_000_000, "revenue": 400, "operating_income": 1, "net_income": 1},
        accession="Q2",
    )
    q3 = _cf_doc(
        "SYN", "2025Q3", fy=2025, fp="Q3", ptype="Q",
        start="2024-08-01", end="2025-04-30",
        fields={"capex": 99_000_000, "revenue": 600, "operating_income": 1, "net_income": 1},
        accession="Q3",
    )
    a = assess_field_derivation("capex", fy, q1, q2, q3)
    assert a["ok"] is False
    assert a["reason_code"] == "MAPPING_AMBIGUOUS"
    assert a.get("flow_basis") == FLOW_BASIS_YTD
    assert a.get("value") is None
