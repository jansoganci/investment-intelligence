"""Multi-year history coverage + diluted share mapping (generic; KO fixtures OK in tests)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fa.history_coverage import (
    SHARE_FIELDS,
    discover_periods_from_companyfacts,
    ensure_normalized_history,
)
from fa.map_companyfacts import TAG_MAP, map_companyfacts_to_period
from fa.stage4.benchmark import assess_runway, label_benchmarks, _tag_false_positives
from fa.stage4.calc import compute_stage4_metrics
from fa.stage4.archetype import propose_archetype
from fa import storage, versioning
from fa.contract import blank_period_document


def _minimal_facts_multi_year() -> dict:
    """Synthetic companyfacts: 5 FY + 8Q revenue + diluted/basic/outstanding shares."""
    rev_rows = []
    dil_rows = []
    basic_rows = []
    out_rows = []
    # FY 2021-2025
    for y in range(2021, 2026):
        rev_rows.append(
            {
                "fy": y,
                "fp": "FY",
                "form": "10-K",
                "end": f"{y}-12-31",
                "start": f"{y}-01-01",
                "val": 1000.0 + (y - 2021) * 100,
                "accn": f"000-{y}",
                "filed": f"{y+1}-02-15",
            }
        )
        dil_rows.append(
            {
                "fy": y,
                "fp": "FY",
                "form": "10-K",
                "end": f"{y}-12-31",
                "start": f"{y}-01-01",
                "val": 100.0 - (y - 2021),  # shrinking (buybacks)
                "accn": f"000-{y}",
                "filed": f"{y+1}-02-15",
            }
        )
        basic_rows.append(
            {
                "fy": y,
                "fp": "FY",
                "form": "10-K",
                "end": f"{y}-12-31",
                "start": f"{y}-01-01",
                "val": 99.0 - (y - 2021),
                "accn": f"000-{y}",
                "filed": f"{y+1}-02-15",
            }
        )
        out_rows.append(
            {
                "fy": y,
                "fp": "FY",
                "form": "10-K",
                "end": f"{y}-12-31",
                "val": 98.0 - (y - 2021),
                "accn": f"000-{y}",
                "filed": f"{y+1}-02-15",
            }
        )
    # 8 quarters: 2024Q1..2025Q4 (use Q1-Q3 of 24/25 + invent Q4 as 10-K-like — use 10-Q Q1-Q3 only)
    # Build 2023Q4..2025Q3 = 8 quarters with ~90d
    q_specs = [
        (2023, "Q4", "2023-10-01", "2023-12-31"),
        (2024, "Q1", "2024-01-01", "2024-03-31"),
        (2024, "Q2", "2024-04-01", "2024-06-30"),
        (2024, "Q3", "2024-07-01", "2024-09-30"),
        (2024, "Q4", "2024-10-01", "2024-12-31"),
        (2025, "Q1", "2025-01-01", "2025-03-31"),
        (2025, "Q2", "2025-04-01", "2025-06-30"),
        (2025, "Q3", "2025-07-01", "2025-09-30"),
    ]
    for i, (fy, fp, start, end) in enumerate(q_specs):
        # current quarter
        rev_rows.append(
            {
                "fy": fy,
                "fp": fp,
                "form": "10-Q",
                "end": end,
                "start": start,
                "val": 250.0 + i,
                "accn": f"Q-{fy}-{fp}",
                "filed": f"{end[:7]}-28",
                "frame": f"CY{fy}{fp}",
            }
        )
        # YTD trap (should be ignored by duration filter)
        if fp == "Q3":
            rev_rows.append(
                {
                    "fy": fy,
                    "fp": fp,
                    "form": "10-Q",
                    "end": end,
                    "start": f"{fy}-01-01",
                    "val": 9999.0,  # YTD — must NOT win
                    "accn": f"Q-{fy}-{fp}",
                    "filed": f"{end[:7]}-28",
                }
            )
        dil_rows.append(
            {
                "fy": fy,
                "fp": fp,
                "form": "10-Q",
                "end": end,
                "start": start,
                "val": 95.0,
                "accn": f"Q-{fy}-{fp}",
                "filed": f"{end[:7]}-28",
            }
        )

    return {
        "cik": 9999991,
        "entityName": "Synth Multi",
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": rev_rows}},
                "WeightedAverageNumberOfDilutedSharesOutstanding": {
                    "units": {"shares": dil_rows}
                },
                "WeightedAverageNumberOfSharesOutstandingBasic": {
                    "units": {"shares": basic_rows}
                },
                "CommonStockSharesOutstanding": {"units": {"shares": out_rows}},
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "fy": y,
                                "fp": "FY",
                                "form": "10-K",
                                "end": f"{y}-12-31",
                                "start": f"{y}-01-01",
                                "val": 100.0 + (y - 2021) * 10,
                                "accn": f"000-{y}",
                                "filed": f"{y+1}-02-15",
                            }
                            for y in range(2021, 2026)
                        ]
                    }
                },
            }
        },
    }


def test_tag_map_has_separated_share_concepts():
    assert "shares_diluted_weighted" in TAG_MAP
    assert "shares_basic_weighted" in TAG_MAP
    assert "shares_outstanding" in TAG_MAP
    assert TAG_MAP["shares_diluted_weighted"] != TAG_MAP["shares_basic_weighted"]
    assert "WeightedAverageNumberOfDilutedSharesOutstanding" in TAG_MAP["shares_diluted_weighted"]
    assert "WeightedAverageNumberOfSharesOutstandingBasic" in TAG_MAP["shares_basic_weighted"]


def test_mapping_separates_basic_diluted_outstanding():
    facts = _minimal_facts_multi_year()
    doc = map_companyfacts_to_period(
        facts,
        ticker="SYNTH_H",
        period_key="FY2025",
        fiscal_year=2025,
        period_end="2025-12-31",
        accession="000-2025",
    )
    assert doc["fields"]["shares_diluted_weighted"] == 96.0  # 100-(2025-2021)=96
    assert doc["fields"]["shares_basic_weighted"] == 95.0
    assert doc["fields"]["shares_outstanding"] == 94.0
    # lineage notes must not imply mixing
    notes = " ".join(
        str(L.get("notes") or "") for L in doc.get("lineage") or [] if L.get("field") in SHARE_FIELDS
    )
    assert "diluted_weighted_average" in notes
    assert "basic_weighted_average" in notes
    assert "period_end_shares_outstanding" in notes


def test_quarterly_prefers_90day_not_ytd():
    facts = _minimal_facts_multi_year()
    doc = map_companyfacts_to_period(
        facts,
        ticker="SYNTH_H",
        period_key="2025Q3",
        fiscal_year=2025,
        fiscal_period="Q3",
        period_type="Q",
        period_end="2025-09-30",
    )
    assert doc["fields"]["revenue"] != 9999.0
    assert doc["fields"]["revenue"] == 250.0 + 7  # 8th quarter index




def test_discover_jan_fye_quarters_prior_calendar_year():
    """Jan FYE: Q1–Q3 end in calendar fy-1; must not be dropped as unaligned."""
    from fa.history_coverage import discover_periods_from_companyfacts

    rev = []
    # FY2024-2026 end late January (calendar year == fy)
    for y in range(2024, 2027):
        rev.append({
            "fy": y, "fp": "FY", "form": "10-K",
            "end": f"{y}-01-25", "start": f"{y-1}-01-26",
            "val": 1000.0 * y, "accn": f"000-fy-{y}", "filed": f"{y}-02-25",
        })
    # For FY2026: Q1 ends 2025-04-27, Q2 2025-07-27, Q3 2025-10-26 (all calendar 2025 = fy-1)
    # For FY2027: Q1 ends 2026-04-26, Q2 2026-07-26
    q_specs = [
        (2026, "Q1", "2025-01-26", "2025-04-27"),
        (2026, "Q2", "2025-04-28", "2025-07-27"),
        (2026, "Q3", "2025-07-28", "2025-10-26"),
        (2027, "Q1", "2026-01-26", "2026-04-26"),
        (2027, "Q2", "2026-04-27", "2026-07-26"),
        # Comparative trap: same end as FY2026 Q2 but labeled fy=2027 (fy-2 end) — reject
        (2027, "Q2", "2025-04-28", "2025-07-27"),
    ]
    for fy, fp, start, end in q_specs:
        rev.append({
            "fy": fy, "fp": fp, "form": "10-Q",
            "end": end, "start": start,
            "val": 100.0, "accn": f"000-{fy}-{fp}-{end}", "filed": end[:7] + "-28",
        })
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": rev}}}}}
    d = discover_periods_from_companyfacts(facts, prefer_fy=3, prefer_q=8)
    q_keys = [p["period_key"] for p in d["q_periods"]]
    assert "2026Q1" in q_keys
    assert "2026Q2" in q_keys
    assert "2026Q3" in q_keys
    assert "2027Q1" in q_keys
    assert "2027Q2" in q_keys
    # Selected Q2 for 2027 must be the 2026-07-26 end, not the fy-2 comparative
    q2 = next(p for p in d["q_periods"] if p["period_key"] == "2027Q2")
    assert q2["period_end"] == "2026-07-26"


def test_revenue_series_prefers_freshest_fy_tag_not_first_nonempty():
    """Stale first revenue tag must not freeze discovery when a later tag is fresher."""
    from fa.history_coverage import _revenue_series, discover_periods_from_companyfacts

    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {
                                "fy": 2022,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2022-01-30",
                                "start": "2021-02-01",
                                "val": 100.0,
                                "accn": "000-old",
                                "filed": "2022-03-01",
                            }
                        ]
                    }
                },
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "fy": y,
                                "fp": "FY",
                                "form": "10-K",
                                "end": f"{y}-01-25",
                                "start": f"{y-1}-01-26",
                                "val": 1000.0 * y,
                                "accn": f"000-{y}",
                                "filed": f"{y}-02-25",
                            }
                            for y in range(2022, 2027)
                        ]
                        + [
                            {
                                "fy": 2026,
                                "fp": q,
                                "form": "10-Q",
                                "end": end,
                                "start": start,
                                "val": 500.0,
                                "accn": f"000-q-{q}",
                                "filed": "2026-08-01",
                            }
                            for q, start, end in [
                                ("Q1", "2026-01-26", "2026-04-26"),
                                ("Q2", "2026-04-27", "2026-07-26"),
                            ]
                        ]
                    }
                },
            }
        }
    }
    series = _revenue_series(facts)
    fy_ends = sorted(
        {
            r.get("end")
            for r in series
            if r.get("fp") == "FY" and r.get("form") in ("10-K", "10-K/A")
        },
        reverse=True,
    )
    assert fy_ends[0] == "2026-01-25"
    d = discover_periods_from_companyfacts(facts, prefer_fy=5, prefer_q=8)
    fy_keys = [p["period_key"] for p in d["fy_periods"]]
    assert fy_keys[-1] == "FY2026"
    assert "FY2026" in fy_keys
    assert d["fy_available"] >= 5



def test_ifrs_20f_revenue_discovery_without_us_gaap_tags():
    """IFRS FPI (20-F) revenue tags must discover FY periods — no ticker hardcode.

    US-GAAP TAG_MAP names alone miss ifrs-full:RevenueFromContractsWithCustomers /
    Revenue; annual form filter must accept 20-F/20-F/A alongside 10-K family.
    """
    from fa.history_coverage import _revenue_series, discover_periods_from_companyfacts, FY_ANNUAL_FORMS

    facts = {
        "facts": {
            "ifrs-full": {
                "RevenueFromContractsWithCustomers": {
                    "units": {
                        "USD": [
                            {
                                "fy": y,
                                "fp": "FY",
                                "form": "20-F",
                                "end": f"{y}-12-31",
                                "start": f"{y}-01-01",
                                "val": 50_000_000_000 + y,
                                "accn": f"000-ifrs-{y}",
                                "filed": f"{y+1}-02-20",
                            }
                            for y in range(2021, 2026)
                        ]
                        + [
                            # comparative prior column in later filing — must not displace
                            {
                                "fy": 2025,
                                "fp": "FY",
                                "form": "20-F",
                                "end": "2023-12-31",
                                "start": "2023-01-01",
                                "val": 1.0,
                                "accn": "000-comp",
                                "filed": "2026-02-20",
                            }
                        ]
                    }
                }
            }
        }
    }
    assert "20-F" in FY_ANNUAL_FORMS
    series = _revenue_series(facts)
    assert series, "IFRS revenue series must be discovered"
    d = discover_periods_from_companyfacts(facts, prefer_fy=5, prefer_q=8)
    fy_keys = [p["period_key"] for p in d["fy_periods"]]
    assert fy_keys == ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
    assert d["q_available"] == 0  # no 10-Q for FPI stub — honest empty quarters
    # comparative end-year != fy rejected
    assert all(p["period_end"] == f"{int(p['period_key'][2:])}-12-31" for p in d["fy_periods"])


def test_discover_periods_ordering_and_limits():
    facts = _minimal_facts_multi_year()
    d = discover_periods_from_companyfacts(facts, prefer_fy=5, prefer_q=8)
    assert d["fy_available"] >= 5
    assert d["q_available"] >= 8
    fy_keys = [p["period_key"] for p in d["fy_periods"]]
    assert fy_keys == sorted(fy_keys)
    assert fy_keys[-1] == "FY2025"
    assert len(fy_keys) == 5
    q_keys = [p["period_key"] for p in d["q_periods"]]
    assert q_keys == sorted(q_keys)
    assert len(q_keys) == 8


def test_ensure_history_creates_periods_no_invention(fa_root):
    facts = _minimal_facts_multi_year()
    storage.ensure_company_layout("SYNTH_H", fa_root, entity_name="Synth")
    rep = ensure_normalized_history(
        "SYNTH_H",
        root=fa_root,
        prefer_fy=5,
        prefer_q=8,
        companyfacts=facts,
        accept=True,
    )
    assert len(rep["created"]) >= 5
    periods = storage.load_all_current_periods("SYNTH_H", fa_root)
    fy = sorted(
        [p for p in periods if p.get("period_type") == "FY"],
        key=lambda d: d["period_key"],
    )
    q = [p for p in periods if p.get("period_type") == "Q"]
    assert len(fy) == 5
    assert len(q) == 8
    # no invented: every FY has lineage from companyfacts
    for p in fy:
        assert p["fields"]["revenue"] is not None
        assert p["fields"]["shares_diluted_weighted"] is not None
        assert any(
            L.get("field") == "shares_diluted_weighted" and L.get("source_kind") == "sec_companyfacts"
            for L in p.get("lineage") or []
        )


def test_ensure_history_fills_shares_on_existing(fa_root):
    facts = _minimal_facts_multi_year()
    storage.ensure_company_layout("SYNTH_H", fa_root)
    # Seed thin FY without shares
    for y, rev in ((2024, 1300.0), (2025, 1400.0)):
        doc = blank_period_document(
            "SYNTH_H",
            f"FY{y}",
            "v001",
            period_type="FY",
            fiscal_year=y,
            fiscal_period="FY",
            period_end=f"{y}-12-31",
            fields={"revenue": rev, "net_income": 50},
        )
        versioning.create_initial_version("SYNTH_H", f"FY{y}", doc, accept=True, root=fa_root)
    rep = ensure_normalized_history(
        "SYNTH_H", root=fa_root, prefer_fy=5, prefer_q=0, companyfacts=facts, accept=True
    )
    assert "FY2024" in rep["updated_shares"] or "FY2025" in rep["updated_shares"]
    cur = storage.load_current_period("SYNTH_H", "FY2025", fa_root)
    assert cur["fields"]["shares_diluted_weighted"] is not None
    assert cur["fields"]["revenue"] == 1400.0  # preserved existing revenue


def test_missing_period_failure_recorded(fa_root):
    """Empty facts → SOURCE_AVAILABILITY, no fabricated periods."""
    storage.ensure_company_layout("SYNTH_H", fa_root)
    rep = ensure_normalized_history(
        "SYNTH_H",
        root=fa_root,
        companyfacts={"cik": 1, "facts": {"us-gaap": {}}},
        accept=True,
    )
    assert rep["created"] == []
    assert any(f.get("reason_code") == "SOURCE_AVAILABILITY" for f in rep["failed"])
    assert storage.load_all_current_periods("SYNTH_H", fa_root) == []


def test_calc_cagr_and_quarterly_with_history():
    periods = []
    for y in range(2020, 2026):
        periods.append(
            {
                "period_key": f"FY{y}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "revenue": 100 * (1.05 ** (y - 2020)),
                    "net_income": 10 * (1.05 ** (y - 2020)),
                    "shares_diluted_weighted": 100 - (y - 2020),
                    "shares_basic_weighted": 99 - (y - 2020),
                    "shares_outstanding": 98 - (y - 2020),
                    "operating_cash_flow": 20,
                    "capex": 5,
                },
            }
        )
    for i, (y, q) in enumerate(
        [(2024, 1), (2024, 2), (2024, 3), (2024, 4), (2025, 1), (2025, 2), (2025, 3), (2025, 4)]
    ):
        periods.append(
            {
                "period_key": f"{y}Q{q}",
                "period_type": "Q",
                "version_id": "v1",
                "fields": {"revenue": 25 + i},
            }
        )
    r = compute_stage4_metrics(periods)
    assert r.metrics["history_flags"]["fy_used"] == 5
    assert r.metrics["history_flags"]["q_used"] == 8
    assert r.metrics["history_flags"]["history_thin"] is False
    assert r.metrics["revenue_cagr_3y"]["cagr"] is not None
    assert r.metrics["revenue_cagr_5y"]["cagr"] is not None
    assert r.metrics["share_concept_used_for_bd4"] == "shares_diluted_weighted"
    assert r.metrics["share_count_direction"] == "down"
    assert r.metrics["absolute_vs_per_share_growth"]
    # prefers diluted, not outstanding
    for row in r.metrics["share_count_trend"]:
        assert row["shares_field"] == "shares_diluted_weighted"


def test_calc_missing_shares_reason_and_no_mix_with_outstanding_only():
    periods = [
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "version_id": "v1",
            "fields": {"revenue": 100, "shares_outstanding": 50},
        },
        {
            "period_key": "FY2025",
            "period_type": "FY",
            "version_id": "v1",
            "fields": {"revenue": 110, "shares_outstanding": 48},
        },
    ]
    r = compute_stage4_metrics(periods)
    # period-end outstanding alone must NOT drive BD4 share trend
    assert r.metrics["share_count_direction"] == "UNKNOWN"
    assert "shares:FY2025" in r.null_reasons


def test_bd4_with_buybacks_and_dilution_not_mechanical():
    def _run(shares_seq, ni_seq):
        periods = []
        for i, y in enumerate(range(2023, 2026)):
            periods.append(
                {
                    "period_key": f"FY{y}",
                    "period_type": "FY",
                    "version_id": "v1",
                    "fields": {
                        "revenue": 100 + i * 10,
                        "net_income": ni_seq[i],
                        "shares_diluted_weighted": shares_seq[i],
                        "capex": 5,
                    },
                }
            )
        calc = compute_stage4_metrics(periods)
        arch = propose_archetype(thesis_summary="trademark beverage concentrate brand")
        runway = assess_runway(
            archetype=arch, semantic=None, thesis_runway="x", calc_metrics=calc.metrics
        )
        fps = _tag_false_positives(calc_metrics=calc.metrics, semantic=None, archetype=arch)
        results, _ = label_benchmarks(
            calc_metrics=calc.metrics,
            archetype=arch,
            semantic=None,
            runway=runway,
            fp_tags=fps,
            thesis_coherence="supports",
        )
        return next(b for b in results if b.dimension_id == "BD4"), calc

    bd4_buyback, calc_b = _run([100, 95, 90], [10, 11, 12])
    assert calc_b.metrics["share_count_direction"] == "down"
    assert bd4_buyback.label in {"PASS", "MIXED"}
    assert "not mechanical" in bd4_buyback.why.lower() or "NOT mechanical" in bd4_buyback.why

    bd4_dilution, calc_d = _run([90, 95, 100], [10, 11, 12])
    assert calc_d.metrics["share_count_direction"] == "up"
    assert bd4_dilution.label in {"PASS", "MIXED"}  # not auto BELOW for dilution
    why_l = bd4_dilution.why.lower()
    assert "not mechanical buyback=good" in why_l or "not mechanical" in why_l
    # Dilution must not force BELOW_REFERENCE
    assert bd4_dilution.label != "BELOW_REFERENCE"


def test_ko_companyfacts_fixture_maps_diluted_when_cached():
    """Live KO cache may be present; if so, assert diluted WAD maps (no fabrication)."""
    cache = Path("/workspace/investment_intelligence/fa_data/cache/sec/companyfacts/CIK0000021344.json")
    if not cache.exists():
        pytest.skip("KO companyfacts cache not present")
    cf = json.loads(cache.read_text(encoding="utf-8"))
    doc = map_companyfacts_to_period(
        cf,
        ticker="KO",
        period_key="FY2025",
        fiscal_year=2025,
        period_end="2025-12-31",
        accession="0001628280-26-010047",
    )
    assert doc["fields"]["shares_diluted_weighted"] is not None
    assert doc["fields"]["shares_basic_weighted"] is not None
    assert doc["fields"]["shares_diluted_weighted"] != doc["fields"]["shares_basic_weighted"]
    d = discover_periods_from_companyfacts(cf, prefer_fy=5, prefer_q=8)
    assert d["fy_available"] >= 3
    assert len(d["fy_periods"]) >= 3


def test_discover_sept_fye_q1_prior_calendar():
    """Non-Dec FYE: Q1 ending in prior calendar year must be discovered (generic)."""
    rev_rows = []
    # FY ends Sep 30
    for y in range(2023, 2026):
        rev_rows.append(
            {
                "fy": y,
                "fp": "FY",
                "form": "10-K",
                "end": f"{y}-09-30",
                "start": f"{y-1}-10-01",
                "val": 1000.0 + y,
                "accn": f"FY-{y}",
                "filed": f"{y}-11-15",
            }
        )
        # Q1: Oct–Dec of prior calendar year (fy-1)
        rev_rows.append(
            {
                "fy": y,
                "fp": "Q1",
                "form": "10-Q",
                "end": f"{y-1}-12-31",
                "start": f"{y-1}-10-01",
                "val": 240.0 + y,
                "accn": f"Q1-{y}",
                "filed": f"{y}-01-28",
            }
        )
        rev_rows.append(
            {
                "fy": y,
                "fp": "Q2",
                "form": "10-Q",
                "end": f"{y}-03-31",
                "start": f"{y}-01-01",
                "val": 250.0 + y,
                "accn": f"Q2-{y}",
                "filed": f"{y}-04-28",
            }
        )
        rev_rows.append(
            {
                "fy": y,
                "fp": "Q3",
                "form": "10-Q",
                "end": f"{y}-06-30",
                "start": f"{y}-04-01",
                "val": 260.0 + y,
                "accn": f"Q3-{y}",
                "filed": f"{y}-07-28",
            }
        )
        # Stale comparative Q1 (end_year << fy-1) must be rejected
        rev_rows.append(
            {
                "fy": y,
                "fp": "Q1",
                "form": "10-Q",
                "end": f"{y-3}-12-31",
                "start": f"{y-3}-10-01",
                "val": 1.0,
                "accn": f"Q1-stale-{y}",
                "filed": f"{y}-01-28",
            }
        )
    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": rev_rows}
                }
            }
        }
    }
    disc = discover_periods_from_companyfacts(facts, prefer_fy=3, prefer_q=8)
    q_keys = set(disc["q_all_keys"])
    assert "2025Q1" in q_keys
    assert "2024Q1" in q_keys
    assert "2025Q2" in q_keys
    # derivable Q4 when FY+Q1+Q2+Q3 present
    assert 2025 in set(disc.get("derived_q4_years_planned") or []) or any(
        m.get("derived") for m in disc["q_periods"]
    ) or disc["contiguous"] or "2025Q4" in [m["period_key"] for m in disc["q_periods"]]
