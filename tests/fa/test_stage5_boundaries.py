"""Boundaries: no Stage 6, no valuation, no BUY/SELL, no R-O-G, no numeric bands, no BE9."""
from __future__ import annotations

import ast
from pathlib import Path

STAGE5 = Path("/workspace/investment_intelligence/fa/stage5")


def _all_source() -> str:
    return "\n".join(p.read_text() for p in STAGE5.glob("*.py"))


def test_no_stage6_module_or_calls():
    src = _all_source()
    assert "run_stage6" not in src
    assert "evaluate_stage6" not in src
    assert "compute_roic" not in src.lower()
    assert "incremental_roic" not in src.lower()


def test_no_be9():
    src = _all_source()
    assert "BE9" not in src or "no BE9" in src.lower() or "NO BE9" in src
    from fa.stage5.questions import BE_DIMENSIONS

    ids = [b[0] for b in BE_DIMENSIONS]
    assert ids == [f"BE{i}" for i in range(1, 9)]
    assert "BE9" not in ids


def test_no_buy_sell_rog_scores():
    src = _all_source().lower()
    assert "buy_signal" not in src
    assert "sell_signal" not in src
    assert "blended_score" not in src
    assert "peer_percentile" not in src or "never peer-percentile" in src


def test_outcomes_enum_locked():
    from fa.stage5.questions import STAGE5_OUTCOMES, CONTEXT_TAGS, PRICING_POWER_POSTURES

    assert STAGE5_OUTCOMES == {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}
    assert CONTEXT_TAGS == {
        "SCALE_ECONOMIES_SHARED_OK",
        "MATURE_FRANCHISE_ECONOMICS_OK",
        "CYCLE_PEAK_MARGIN_RISK",
        "CHALLENGE_ARCHETYPE",
        "ACCOUNTING_MARGIN_DISTORTION",
        "HIGH_MARGIN_QUALITY_RISK",
    }
    assert PRICING_POWER_POSTURES == {
        "STRONG", "MODERATE", "WEAK", "MIXED", "UNKNOWN", "NOT_APPLICABLE"
    }


def test_no_numeric_band_gates_in_ast():
    """Forbid production gate patterns like GM > X → PROCEED."""
    forbidden_assign_names = {"GM_BAND", "OP_BAND", "IM_BAND", "NUMERIC_BAND"}
    for path in STAGE5.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_assign_names:
                raise AssertionError(f"Forbidden band name in {path}")


def test_stage4_unchanged_no_stage5_calls():
    """Stage 4 must not call Stage 5 (no redesign)."""
    s4 = Path("/workspace/investment_intelligence/fa/stage4")
    src = "\n".join(p.read_text() for p in s4.glob("*.py"))
    assert "run_stage5" not in src
    assert "evaluate_stage5" not in src
