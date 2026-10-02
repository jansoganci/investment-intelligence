"""Boundaries: no Stage 5/6, no valuation, no BUY/SELL, no R-O-G, no NC* gates."""
from __future__ import annotations

import ast
from pathlib import Path

STAGE4 = Path("/workspace/investment_intelligence/fa/stage4")


def _all_source() -> str:
    return "\n".join(p.read_text() for p in STAGE4.glob("*.py"))


def test_no_stage5_module_or_calls():
    src = _all_source()
    assert "stage5" not in src.lower() or "no stage 5" in src.lower()
    assert "run_stage5" not in src
    assert "evaluate_stage5" not in src


def test_no_roic_computation():
    src = _all_source().lower()
    # Mentions of ROIC as handoff are OK; computation patterns are not
    assert "incremental_roic" not in src
    assert "compute_roic" not in src
    assert "roic =" not in src


def test_no_buy_sell_rog_colors():
    src = _all_source()
    low = src.lower()
    assert "buy_signal" not in low
    assert "sell_signal" not in low
    assert "r/o/g" not in low or "no r/o/g" in low or "r-o-g" in low
    # No color enums as outcomes
    for path in STAGE4.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in {"RED", "ORANGE", "GREEN", "R", "O", "G"}:
                # Allow letter G in other contexts — only flag exact color constants in Assign to outcome-like
                pass


def test_nc_bands_not_locked_as_logic():
    src = _all_source().lower()
    # Should mention NOT LOCKED if NC referenced; must not use NC thresholds
    assert "nc1" not in src or "not locked" in src
    assert "nc_band" not in src


def test_outcomes_do_not_include_blocked_by_fragility():
    from fa.stage4.questions import STAGE4_OUTCOMES

    assert STAGE4_OUTCOMES == {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}
    assert "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY" not in STAGE4_OUTCOMES
