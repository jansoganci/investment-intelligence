"""E2E dry-run for SYNTH_OPCO — refuse if not listed; produce Stage 2 markdown."""
from __future__ import annotations

from pathlib import Path

from fa.lists import NotOnFAListError, require_on_fa_list
from fa.pipeline import analyze_company, dry_run_synth_opco
from fa.map_companyfacts import map_companyfacts_to_period
import json


def test_refuse_if_not_on_list(fa_root, demo_list_path):
    result = analyze_company(
        "NOT_ON_LIST",
        root=fa_root,
        fa_list_path=demo_list_path,
        seed=False,
        use_fixtures=False,
    )
    assert result.refused is True
    assert result.ok is False
    assert "not on the Fundamental Analysis List" in (result.refuse_reason or "")


def test_require_on_list_raises(demo_list_path):
    try:
        require_on_fa_list("MSFT", path=demo_list_path)
        assert False, "should have raised"
    except NotOnFAListError:
        pass


def test_dry_run_synth_opco_produces_report(fa_root, demo_list_path, capsys):
    result = analyze_company(
        "SYNTH_OPCO",
        root=fa_root,
        fa_list_path=demo_list_path,
        use_fixtures=True,
        seed=True,
    )
    assert result.ok is True
    assert result.refused is False
    assert result.stage2 is not None
    assert result.markdown is not None
    assert "Stage 2 — Balance Sheet — SYNTH_OPCO" in result.markdown
    assert result.stage2.process_outcome in {
        "PROCEED",
        "CONDITIONAL",
        "REVIEW_REQUIRED",
        "TOO_HARD",
        "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY",
    }
    # No color language
    md_lower = result.markdown.lower()
    assert "red/orange/green" not in md_lower or "no red/orange/green" in md_lower
    assert "RED" not in result.markdown.split("Process outcome")[0]  # soft check
    # No stage3
    assert "Stage 3" not in result.markdown or "No Stage 3" in result.markdown

    # Print for dry-run visibility
    print("\n===== DRY-RUN STAGE 2 REPORT (SYNTH_OPCO) =====\n")
    print(result.markdown)
    print(f"\n===== process_outcome={result.stage2.process_outcome} block_next={result.stage2.block_next} =====\n")


def test_map_companyfacts_marks_ambiguous_revenue():
    facts = json.loads(
        Path("/workspace/investment_intelligence/fa_fixtures/synthetic_operating_company/sec_companyfacts_stub.json").read_text()
    )
    doc = map_companyfacts_to_period(
        facts,
        ticker="SYNTH_OPCO",
        period_key="FY2025",
        fiscal_year=2025,
        accession="0009999991-26-000001",
    )
    # Both Revenues and SalesRevenueNet present → uncertain
    assert doc["fields"].get("revenue") is not None
    assert "revenue" in doc.get("field_uncertainty", {}) or any(
        (x.get("field") == "revenue" and x.get("uncertain")) for x in doc.get("lineage", [])
    )


def test_no_production_real_tickers_in_demo_list():
    demo = json.loads(
        Path("/workspace/investment_intelligence/fa_fixtures/demo_fa_list.json").read_text()
    )
    assert demo.get("synthetic_demo") is True
    for c in demo["companies"]:
        assert c.get("synthetic_demo") is True
        assert c["ticker"].startswith("SYNTH") or ".DEMO" in c["ticker"]
