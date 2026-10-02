"""Boundaries: no BUY/SELL; no numeric risk gates; no Stage 1–8 redesign; no final FA."""
from __future__ import annotations

import ast
from pathlib import Path

STAGE9 = Path("/workspace/investment_intelligence/fa/stage9")
STAGE8 = Path("/workspace/investment_intelligence/fa/stage8")
FA_PIPE = Path("/workspace/investment_intelligence/fa/pipeline.py")


def _all_source(path: Path) -> str:
    return "\n".join(p.read_text() for p in path.glob("*.py"))


def test_no_final_fa_or_buy_sell_scores():
    src = _all_source(STAGE9).lower()
    assert "buy_signal" not in src
    assert "sell_signal" not in src
    assert "blended_score" not in src
    assert "averaged_external" in src or "no_averaged_external_risk_score" in src
    assert "auto_red" not in src
    assert "final_fa_color" not in src
    assert "no_final_fa_synthesis" in src


def test_outcomes_enum_locked():
    from fa.stage9.questions import (
        STAGE9_OUTCOMES,
        ER_LENSES,
        S9_HFA_CARRIES,
        S8_H9_FORWARDABLE,
        FALSE_POSITIVE_CATALOGUE,
        EVIDENCE_LABELS,
        CONCENTRATION_LABELS,
    )

    assert STAGE9_OUTCOMES == {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}
    assert [e[0] for e in ER_LENSES] == [f"ER{i}" for i in range(1, 9)]
    assert "S9_HFA_THESIS_BREAKER_ACTIVE" in S9_HFA_CARRIES
    assert "S8_H9_CYCLE_SENSITIVE_VALUATION" in S8_H9_FORWARDABLE
    assert len(FALSE_POSITIVE_CATALOGUE) == 12
    assert FALSE_POSITIVE_CATALOGUE[0][0] == "FP-E1"
    assert EVIDENCE_LABELS == {"FACT", "GUIDANCE", "CLAIM", "INFERENCE", "UNKNOWN"}
    assert "extreme" in CONCENTRATION_LABELS


def test_er2_er8_locked_constraints_in_source():
    src = _all_source(STAGE9)
    assert "no_stage5_pricing_power_redo" in src.lower() or "no S5 pricing-power redo" in src or "NO Stage 5 pricing-power redo" in src
    assert "no_stage1_thesis_restatement" in src.lower() or "NO Stage 1 thesis restatement" in src
    assert "NOT a giant risk register" in src or "not_giant_register" in src or "NOT giant risk register" in src


def test_no_numeric_gate_constants_in_ast():
    forbidden = {
        "CONCENTRATION_KILL_GATE",
        "REGULATORY_KILL_GATE",
        "EXTERNAL_RISK_SCORE",
        "PORTER_SCORE_GATE",
        "COUNTRY_RISK_SCORE",
        "AVERAGED_ER_SCORE",
    }
    for path in STAGE9.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                raise AssertionError(f"Forbidden gate name in {path}")


def test_stage8_unchanged_no_stage9_calls():
    src = _all_source(STAGE8)
    assert "run_stage9" not in src
    assert "evaluate_stage9" not in src


def test_analyze_company_not_wired_to_stage9():
    pipe = FA_PIPE.read_text()
    assert "run_stage9" not in pipe
    assert "evaluate_stage9" not in pipe


def test_no_ticker_hardcodes_in_production_stage9():
    src = _all_source(STAGE9)
    for t in ("ROP", "META", "VISA", "KO", "NVDA", "ADBE", "TSLA", "BRK", "RIO", "NCLH"):
        assert f'"{t}"' not in src
        assert f"'{t}'" not in src
    # Bare V as string literal ticker also forbidden in production modules
    assert '"V"' not in src
    assert "'V'" not in src


def test_calc_advertises_boundary_flags():
    from fa.stage9.calc import compute_stage9_metrics

    r = compute_stage9_metrics([])
    assert r.metrics["no_numeric_risk_gates"] is True
    assert r.metrics["no_averaged_external_risk_score"] is True
    assert r.metrics["no_industry_warehouse"] is True
    assert r.metrics["no_stage5_pricing_power_redo"] is True
    assert r.metrics["no_stage1_thesis_restatement"] is True
    assert r.metrics["no_final_fa_synthesis"] is True
    assert r.metrics["concentration_no_auto_fail"] is True
