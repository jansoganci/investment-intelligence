"""Boundaries: no BUY/SELL; no terminal averaging; no Stage 9; Stages 1–7 untouched calls."""
from __future__ import annotations

import ast
from pathlib import Path

STAGE8 = Path("/workspace/investment_intelligence/fa/stage8")
STAGE7 = Path("/workspace/investment_intelligence/fa/stage7")
FA_PIPE = Path("/workspace/investment_intelligence/fa/pipeline.py")


def _all_source(path: Path) -> str:
    return "\n".join(p.read_text() for p in path.glob("*.py"))


def test_no_stage9_impl():
    src = _all_source(STAGE8)
    assert "run_stage9" not in src
    assert "evaluate_stage9" not in src


def test_no_buy_sell_colors_cheap_expensive_language_as_verdict():
    src = _all_source(STAGE8).lower()
    # Allow mentions in forbidden/never comments; forbid verdict helpers
    assert "buy_signal" not in src
    assert "sell_signal" not in src
    assert "blended_score" not in src
    assert "averaged_fair_value" not in src
    assert "recommendation = \"buy\"" not in src
    assert "recommendation = \"sell\"" not in src
    assert "auto_red" not in src
    # Must explicitly forbid cheap/expensive as verdict
    assert "never_cheap_expensive" in src or "≠ cheap/expensive" in src or "!= cheap/expensive" in src or "≠cheap" in src.replace(" ", "")


def test_no_terminal_average_in_code():
    src = _all_source(STAGE8)
    assert "no_terminal_average" in src
    # Must not compute mean of dual terminals as truth
    assert "averaged_terminal" in src  # field set to None / forbidden
    from fa.stage8.dcf import run_fcff_scenarios

    out = run_fcff_scenarios(
        base_fcff=100.0,
        discount_class="standard_opco",
        bridge={
            "gross_debt": 50.0,
            "cash_and_equivalents": 10.0,
            "shares_used": 10.0,
            "lease_add_to_debt": 0.0,
            "sti_subtracted": 0.0,
        },
    )
    assert out["applicable"] is True
    assert out["no_terminal_average"] is True
    for sc in out["scenarios"].values():
        assert sc.get("averaged_terminal_iv") is None
        assert sc.get("no_terminal_average") is True
    # Ranges exist separately — not a single averaged fair value key as truth
    assert "iv_range_perpetual_growth" in out
    assert "iv_range_exit_multiple" in out


def test_freshness_failure_suppresses_mos_and_iv():
    from fa.stage8.evaluate import evaluate_stage8

    periods = [
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "version_id": "v1",
            "period_end": "2024-12-31",
            "reporting_currency": "USD",
            "fields": {
                "operating_cash_flow": 200.0,
                "cash_and_equivalents": 50.0,
                "total_debt": 100.0,
                "shares_diluted_weighted": 10.0,
                "shares_outstanding": 10.0,
                "revenue": 1000.0,
                "net_income": 100.0,
                "sbc_expense": 5.0,
            },
        }
    ]
    report = evaluate_stage8(
        "SYNTH_STALE",
        periods,
        market_price=25.0,
        price_currency="USD",
        price_as_of="2020-01-01T00:00:00+00:00",  # very old → STALE/UNKNOWN path
        price_source="unit_test_stale",
        force_primary="A1",
    )
    assert report.staleness_class in {"STALE", "UNKNOWN"}
    assert report.price_sensitive_suppressed is True
    assert report.calc.metrics["dcf"]["applicable"] is False
    assert report.expectations_label == "unknown"
    assert any("suppress" in b.lower() or "suppressed" in b.lower() for b in report.mos_uncertainty_bullets)
    assert report.terminates_later_stages is False
    assert report.process_outcome in {"REVIEW_REQUIRED", "TOO_HARD"}


def test_a7_not_free_organic_acq_growth():
    from fa.stage8.evaluate import evaluate_stage8
    from fa.stage8.normalization import build_normalized_base

    series = [
        {
            "period_key": f"FY{2020+i}",
            "operating_cash_flow": 100 + i * 10,
            "capex": None,
            "business_acquisitions_cash": 200 + i * 50,
            "net_income": 80,
            "revenue": 500 + i * 20,
            "sbc_expense": 10,
            "free_cash_flow": None,
        }
        for i in range(5)
    ]
    norm = build_normalized_base(
        series,
        primary_archetype="A7",
        secondary_traits=["acquisitive"],
        s6_flags=["S6_H7_ACQ_RETURN_OPACITY"],
    )
    assert norm["a7_dual"] is True
    assert norm["organic_exhibit"]["no_free_organic_acquired_growth"] is True
    assert norm["acq_exhibit"]["recurring_ma_as_reinvestment"] is True
    assert norm["acq_exhibit"]["no_deal_by_deal_dcf"] is True
    assert "s6_acq_return_opacity" in norm["uncertainty_drivers"]

    periods = [
        {
            "period_key": r["period_key"],
            "period_type": "FY",
            "version_id": "v1",
            "period_end": f"{r['period_key'][2:]}-12-31",
            "reporting_currency": "USD",
            "fields": {
                "operating_cash_flow": r["operating_cash_flow"],
                "business_acquisitions_cash": r["business_acquisitions_cash"],
                "cash_and_equivalents": 40.0,
                "total_debt": 300.0,
                "shares_diluted_weighted": 20.0,
                "shares_outstanding": 20.0,
                "revenue": r["revenue"],
                "net_income": r["net_income"],
                "sbc_expense": r["sbc_expense"],
            },
        }
        for r in series
    ]
    report = evaluate_stage8(
        "SYNTH_A7",
        periods,
        market_price=50.0,
        price_currency="USD",
        price_as_of="2026-09-29T12:00:00+00:00",
        price_source="unit_test",
        force_primary="A7",
        stage6_artifact={
            "process_outcome": "REVIEW_REQUIRED",
            "stage7_handoff_flags": [
                "S6_H7_DUAL_VIEW_CONFLICT",
                "S6_H7_ACQ_RETURN_OPACITY",
            ],
        },
    )
    assert report.a7_dual_exhibits is True
    assert report.archetype.primary_archetype == "A7"
    blob = " ".join(report.normalized_base_bullets + report.carry_forward_concerns).lower()
    assert "free-organic" in blob or "free organic" in blob or "no free-organic" in blob
    assert "S6_H7_ACQ_RETURN_OPACITY" in report.s6_handoff_flags_consumed
    assert report.terminates_later_stages is False
    # Must not emit BUY/SELL
    full = (report.to_dict() | {"md": ""}).__repr__().lower()
    assert "buy_signal" not in full


def test_outcomes_enum_locked_and_non_terminating():
    from fa.stage8.questions import (
        STAGE8_OUTCOMES,
        STALENESS_CLASSES,
        EXPECTATIONS_VOCAB,
        UNCERTAINTY_VOCAB,
        VA_LENSES,
        SCENARIO_NAMES,
    )

    assert STAGE8_OUTCOMES == {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}
    assert STALENESS_CLASSES == {"CURRENT", "RECENT", "STALE", "UNKNOWN"}
    assert EXPECTATIONS_VOCAB == {
        "conservative",
        "plausible",
        "demanding",
        "heroic",
        "incoherent_with_evidence",
        "unknown",
    }
    assert UNCERTAINTY_VOCAB == {"low", "moderate", "high", "extreme", "unanalyzable"}
    assert SCENARIO_NAMES == {"conservative", "central", "optimistic"}
    assert [v[0] for v in VA_LENSES] == [f"VA{i}" for i in range(1, 9)]


def test_reverse_dcf_vocab_exact():
    from fa.stage8.reverse_dcf import classify_expectations, EXPECTATIONS_VOCAB, run_reverse_dcf

    assert set(EXPECTATIONS_VOCAB) == {
        "conservative",
        "plausible",
        "demanding",
        "heroic",
        "incoherent_with_evidence",
        "unknown",
    }
    lab, why = classify_expectations(0.03)
    assert lab == "plausible"
    assert "cheap" not in why.lower() or "≠" in why or "not" in why.lower()
    # A7 + opacity alone → keep rate-band label (heroic); do NOT force incoherent
    lab2, why2 = classify_expectations(0.20, a7=True, s6_opacity=True)
    assert lab2 == "heroic"
    assert "opacity" in why2.lower() or "uncertainty" in why2.lower()
    # Real Stage4 contradiction still forces incoherent
    lab3, why3 = classify_expectations(0.20, stage4_growth_hint=0.02)
    assert lab3 == "incoherent_with_evidence"
    assert "Stage4" in why3
    out = run_reverse_dcf(
        market_bridge={"enterprise_value": 5000.0, "equity_market_cap": 4000.0, "shares_used": 100.0},
        base_fcff=200.0,
        discount_class="standard_opco",
    )
    assert out["never_cheap_expensive"] is True
    assert out["never_buy_sell"] is True
    assert out["expectations_label"] in EXPECTATIONS_VOCAB


def test_no_ticker_hardcodes_in_production_stage8():
    src = _all_source(STAGE8)
    for t in ("ROP", "META", "VISA", "KO", "NVDA", "ADBE", "TSLA", "BRK", "NCLH", "RIO"):
        assert f'"{t}"' not in src
        assert f"'{t}'" not in src


def test_analyze_company_not_wired_to_stage8():
    pipe = FA_PIPE.read_text()
    assert "run_stage8" not in pipe
    assert "evaluate_stage8" not in pipe


def test_stage7_unchanged_no_stage8_calls():
    src = _all_source(STAGE7)
    assert "run_stage8" not in src
    assert "evaluate_stage8" not in src
    assert "compute_stage8" not in src


def test_no_forbidden_gate_constants_in_ast():
    forbidden = {
        "MOS_PCT_GATE",
        "PE_CHEAP_GATE",
        "CAPM_BETA",
        "WACC_HURDLE",
        "FAIR_VALUE_SCORE",
        "BUY_THRESHOLD",
        "SELL_THRESHOLD",
    }
    for path in STAGE8.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                raise AssertionError(f"Forbidden gate name in {path}: {node.id}")
