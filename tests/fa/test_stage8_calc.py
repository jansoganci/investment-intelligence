"""Stage 8 calc / bridge / DCF dual-terminal / reverse DCF unit tests."""
from __future__ import annotations

from fa.stage8.calc import (
    build_ev_equity_bridge,
    compute_stage8_bridge_metrics,
    equity_iv_from_enterprise,
    prefer_diluted_shares,
)
from fa.stage8.dcf import run_fcff_scenarios
from fa.stage8.market_data import (
    build_price_provenance,
    classify_staleness,
    price_sensitive_allowed,
    reconcile_currency,
)
from fa.stage8.reverse_dcf import solve_implied_fcff_growth


def test_ev_bridge_math():
    cs = {
        "shares_diluted_weighted": 100.0,
        "shares_outstanding": 90.0,
        "total_debt": 200.0,
        "cash_and_equivalents": 50.0,
        "period_key": "FY2024",
        "period_end": "2024-12-31",
    }
    b = build_ev_equity_bridge(share_price=10.0, cs=cs)
    assert b["equity_market_cap"] == 1000.0
    assert b["enterprise_value"] == 1150.0  # 1000+200-50
    assert b["share_basis"] == "shares_diluted_weighted"
    sh, basis = prefer_diluted_shares(cs)
    assert sh == 100.0 and basis == "shares_diluted_weighted"
    eq = equity_iv_from_enterprise(1150.0, gross_debt=200.0, cash=50.0)
    assert eq == 1000.0


def test_currency_and_freshness():
    ok = reconcile_currency("USD", "USD")
    assert ok["ok"] is True
    bad = reconcile_currency("USD", "EUR")
    assert bad["ok"] is False
    allowed, _ = price_sensitive_allowed("STALE", True)
    assert allowed is False
    allowed2, _ = price_sensitive_allowed("CURRENT", True)
    assert allowed2 is True
    prov = build_price_provenance(
        share_price=10.0,
        currency="USD",
        as_of="2026-09-29T12:00:00+00:00",
        source="test",
    )
    assert prov["provenance_complete"] is True
    assert "staleness_class" in prov
    st, _ = classify_staleness(as_of=None, source="x")
    assert st == "UNKNOWN"


def test_dual_terminal_cross_checks_not_averaged():
    out = run_fcff_scenarios(
        base_fcff=500.0,
        discount_class="standard_opco",
        primary_archetype="A7",
        bridge={
            "gross_debt": 1000.0,
            "cash_and_equivalents": 200.0,
            "shares_used": 100.0,
            "lease_add_to_debt": 0.0,
            "sti_subtracted": 0.0,
        },
    )
    assert out["applicable"] is True
    assert out["no_terminal_average"] is True
    assert out["no_method_average"] is True
    assert "perpetual_growth" in str(out["scenarios"]["central"]["terminal_perpetual_growth"])
    assert "exit_multiple" in str(out["scenarios"]["central"]["terminal_exit_multiple"])
    # Both methods present; averaged field is None
    assert out["scenarios"]["central"]["averaged_terminal_iv"] is None
    assert out["iv_range_perpetual_growth"]["low"] is not None
    assert out["iv_range_exit_multiple"]["low"] is not None
    # Envelope note must say NOT averaged
    assert "NOT" in out["iv_range_envelope_descriptive"]["note"] or "not" in out["iv_range_envelope_descriptive"]["note"]


def test_reverse_dcf_solve_bounds():
    sol = solve_implied_fcff_growth(
        target_enterprise_value=8000.0,
        base_fcff=400.0,
        discount_class="standard_opco",
    )
    assert sol["constructible"] is True
    assert sol["implied_fcff_growth"] is not None
    assert "RESEARCH_CANDIDATE" in sol.get("numerics_tag", "") or sol.get("solve")


def test_compute_stage8_metrics_flags():
    periods = [
        {
            "period_key": "FY2023",
            "period_type": "FY",
            "version_id": "v1",
            "period_end": "2023-12-31",
            "reporting_currency": "USD",
            "fields": {
                "operating_cash_flow": 100.0,
                "cash_and_equivalents": 20.0,
                "total_debt": 80.0,
                "shares_diluted_weighted": 10.0,
                "shares_outstanding": 10.0,
                "sbc_expense": 5.0,
            },
        },
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "version_id": "v1",
            "period_end": "2024-12-31",
            "reporting_currency": "USD",
            "fields": {
                "operating_cash_flow": 120.0,
                "cash_and_equivalents": 25.0,
                "total_debt": 70.0,
                "shares_diluted_weighted": 10.5,
                "shares_outstanding": 10.2,
                "sbc_expense": 6.0,
            },
        },
    ]
    calc = compute_stage8_bridge_metrics(periods, share_price=40.0)
    assert calc.metrics["no_terminal_average"] is True
    assert calc.metrics["no_buy_sell"] is True
    assert calc.metrics["no_capm_engine"] is True
    assert calc.metrics["ev_equity_bridge"]["enterprise_value"] is not None


def test_capex_unknown_ocf_proxy_not_authoritative_fcff():
    """GENERIC defect guard: CapEx null → OCF must not silently become FCFF / VA3 PASS."""
    from fa.stage8.evaluate import evaluate_stage8
    from fa.stage8.normalization import build_normalized_base
    from fa.stage8.benchmark import label_benchmarks

    rows = [
        {
            "period_key": f"FY{2021+i}",
            "operating_cash_flow": 2000.0 + i * 50,
            "capex": None,  # CapEx undisclosed
            "business_acquisitions_cash": 3000.0,
            "net_income": 1500.0,
            "revenue": 6000.0,
            "sbc_expense": 40.0,
            "free_cash_flow": None,
        }
        for i in range(5)
    ]
    norm = build_normalized_base(rows, primary_archetype="A7", s6_flags=["S6_H7_ACQ_RETURN_OPACITY"])
    assert norm["fcf_method"] == "ocf_proxy_capex_unknown"
    assert norm["authoritative_fcff_eligible"] is False
    assert norm["base_incomplete"] is True

    periods = [
        {
            "period_key": f"FY{2021+i}",
            "period_type": "FY",
            "version_id": "v1",
            "period_end": f"{2021+i}-12-31",
            "reporting_currency": "USD",
            "fields": {
                "operating_cash_flow": 2000.0 + i * 50,
                # capex intentionally absent
                "business_acquisitions_cash": 3000.0,
                "cash_and_equivalents": 200.0,
                "total_debt": 5000.0,
                "shares_diluted_weighted": 100.0,
                "shares_outstanding": 100.0,
                "revenue": 6000.0,
                "net_income": 1500.0,
                "sbc_expense": 40.0,
            },
        }
        for i in range(5)
    ]
    report = evaluate_stage8(
        "synthetic_capex_null",
        periods,
        market_price=200.0,
        price_currency="USD",
        price_as_of="2026-09-29T14:00:00+00:00",
        price_source="unit_test",
        force_primary="A7",
        stage6_artifact={
            "process_outcome": "REVIEW_REQUIRED",
            "stage7_handoff_flags": ["S6_H7_ACQ_RETURN_OPACITY", "S6_H7_DUAL_VIEW_CONFLICT"],
            "archetype": {"primary_archetype": "A7"},
        },
    )
    dcf = report.calc.metrics.get("dcf") or {}
    assert dcf.get("base_incomplete") is True
    assert dcf.get("authoritative_fcff") is False
    assert dcf.get("defensible_iv") is False
    assert dcf.get("method") == "OCF_PROXY_INCOMPLETE_NOT_FCFF"
    # Must not silently claim base_fcff == OCF
    assert dcf.get("base_fcff") is None
    va3 = next(b for b in report.benchmark_results if b.dimension_id == "VA3")
    assert va3.label == "MIXED", va3.label
    assert "OCF proxy" in va3.why or "incomplete" in va3.why.lower()
    va7 = next(b for b in report.benchmark_results if b.dimension_id == "VA7")
    assert va7.label == "MIXED", va7.label
    assert report.process_outcome == "REVIEW_REQUIRED"


def test_classify_expectations_high_growth_alone_not_incoherent():
    """High implied growth alone must NOT yield incoherent_with_evidence."""
    from fa.stage8.reverse_dcf import classify_expectations

    lab, _ = classify_expectations(0.177)
    assert lab == "heroic"


def test_classify_expectations_a7_opacity_alone_not_incoherent():
    """A7 + S6_H7_ACQ_RETURN_OPACITY alone is uncertainty — not incoherent_with_evidence."""
    from fa.stage8.reverse_dcf import classify_expectations

    lab, why = classify_expectations(0.177, a7=True, s6_opacity=True)
    assert lab == "heroic", lab
    assert lab != "incoherent_with_evidence"
    assert "opacity" in why.lower() or "uncertainty" in why.lower()
    assert "not incoherent" in why.lower() or "≠ evidence contradiction" in why or "not evidence contradiction" in why.lower()


def test_classify_expectations_stage4_contradiction_still_incoherent():
    """Stage4 growth hint << implied heroic still yields incoherent_with_evidence."""
    from fa.stage8.reverse_dcf import classify_expectations

    lab, why = classify_expectations(0.177, stage4_growth_hint=0.02, a7=True, s6_opacity=True)
    assert lab == "incoherent_with_evidence", lab
    assert "Stage4" in why
    # Opacity note may still appear in why, but the trigger is Stage4 contradiction
    lab2, why2 = classify_expectations(0.20, stage4_growth_hint=0.01)
    assert lab2 == "incoherent_with_evidence"
    assert "Stage4" in why2


def test_reverse_dcf_ceiling_not_point_estimate():
    """Search-ceiling hit must be lower_bound_only — NOT a solved 30% point estimate."""
    from fa.stage8.reverse_dcf import solve_implied_fcff_growth, classify_expectations, run_reverse_dcf

    # Huge target EV vs small base → above search high
    sol = solve_implied_fcff_growth(
        target_enterprise_value=5_000_000.0,
        base_fcff=100.0,
        discount_class="standard_opco",
        growth_high=0.30,
    )
    assert sol["constructible"] is True
    assert sol["bound"] == "above_search_high"
    assert sol["solve_status"] == "unresolved_above_search_range"
    assert sol["lower_bound_only"] is True
    assert sol["root_found"] is False
    assert sol["implied_fcff_growth"] is None  # NOT the ceiling as point estimate
    assert sol["implied_fcff_growth_lower_bound"] == 0.30
    assert sol["search_range"]["growth_high"] == 0.30
    assert sol["price_value_residual_ev"] is not None
    assert sol["matched_ev"] < sol["target_ev"]

    lab, why = classify_expectations(
        None,
        constructible=True,
        solve_status="unresolved_above_search_range",
        lower_bound_only=True,
        bound_growth=0.30,
    )
    assert lab == "heroic"
    assert ">" in why and "30" in why
    assert "NOT a solved point estimate" in why
    assert "≈30" not in why and "≈30.0%" not in why

    out = run_reverse_dcf(
        market_bridge={"enterprise_value": 5_000_000.0, "equity_market_cap": 5_000_000.0, "shares_used": 100.0},
        base_fcff=100.0,
        discount_class="standard_opco",
    )
    assert out["expectations_label"] == "heroic"
    assert out["solve"]["lower_bound_only"] is True
    assert out["solve"]["implied_fcff_growth"] is None
    assert ">" in out["expectations_why"]


def test_exit_multiple_is_fcff_not_ebitda():
    """EXIT_FCFF_MULTIPLE must apply to FCFF; must not silently claim EBITDA basis."""
    from fa.stage8.dcf import (
        run_fcff_scenarios,
        RESEARCH_CANDIDATE_EXIT_FCFF_MULTIPLE,
        _terminal_exit_multiple,
    )

    term = _terminal_exit_multiple(100.0, multiple=12.0, discount=0.10, years=5)
    assert term["terminal_basis"] == "FCFF"
    assert term["terminal_basis_vocabulary"] == "EXIT_FCFF_MULTIPLE"
    assert term["not_ebitda"] is True
    assert term["exit_fcff_multiple"] == 12.0
    assert abs(term["terminal_value"] - 1200.0) < 1e-9

    out = run_fcff_scenarios(
        base_fcff=500.0,
        discount_class="standard_opco",
        bridge={"gross_debt": 0.0, "cash_and_equivalents": 0.0, "shares_used": 100.0},
    )
    assert out["exit_multiple_basis"]["metric"] == "FCFF"
    assert out["exit_multiple_basis"]["not_ebitda"] is True
    tex = out["scenarios"]["central"]["terminal_exit_multiple"]
    assert tex["terminal_basis"] == "FCFF"
    assert "EBITDA" not in (tex.get("terminal_basis_vocabulary") or "")
    assert RESEARCH_CANDIDATE_EXIT_FCFF_MULTIPLE["central"] == 12.0


def test_growth_regime_mismatch_downgrades_va3_va7():
    """High Stage4 CAGR vs generic low RESEARCH growth paths → VA3/VA7 MIXED, not PASS."""
    from fa.stage8.evaluate import evaluate_stage8

    periods = [
        {
            "period_key": f"FY{2021+i}",
            "period_type": "FY",
            "version_id": "v1",
            "period_end": f"{2021+i}-12-31",
            "reporting_currency": "USD",
            "fields": {
                "operating_cash_flow": 5000.0 + i * 2000,
                "capex": 400.0 + i * 50,
                "cash_and_equivalents": 1000.0,
                "total_debt": 500.0,
                "shares_diluted_weighted": 100.0,
                "shares_outstanding": 100.0,
                "revenue": 10000.0 * ((1.5) ** i),
                "net_income": 3000.0,
                "sbc_expense": 50.0,
            },
        }
        for i in range(5)
    ]
    stage4 = {
        "calc": {"metrics": {"revenue_cagr_5y": {"cagr": 0.67}}},
        "process_outcome": "CONDITIONAL",
        "archetype": {"primary_archetype": "A4"},
    }
    report = evaluate_stage8(
        "synthetic_high_growth",
        periods,
        market_price=200.0,
        price_currency="USD",
        price_as_of="2026-09-29T14:00:00+00:00",
        price_source="unit_test",
        force_primary="A4",
        stage4_artifact=stage4,
    )
    dcf = report.calc.metrics.get("dcf") or {}
    assert dcf.get("growth_path_regime_mismatch"), dcf.get("assumption_coherence")
    assert dcf.get("defensible_iv") is False
    va3 = next(b for b in report.benchmark_results if b.dimension_id == "VA3")
    assert va3.label == "MIXED", va3.why
    va7 = next(b for b in report.benchmark_results if b.dimension_id == "VA7")
    assert va7.label == "MIXED", va7.why
    assert "growth_path_regime_mismatch_vs_s4" in (report.uncertainty_drivers or [])
