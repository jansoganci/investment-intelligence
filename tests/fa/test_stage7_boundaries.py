"""Boundaries: no ROIC recompute; no Stage 8; no scores; Stages 1–6 untouched calls."""
from __future__ import annotations

import ast
from pathlib import Path

STAGE7 = Path("/workspace/investment_intelligence/fa/stage7")
STAGE6 = Path("/workspace/investment_intelligence/fa/stage6")


def _all_source(path: Path) -> str:
    return "\n".join(p.read_text() for p in path.glob("*.py"))


def test_no_stage8_impl_or_valuation():
    src = _all_source(STAGE7)
    assert "run_stage8" not in src
    assert "evaluate_stage8" not in src
    assert "intrinsic_value" not in src.lower() or "no stage 8" in src.lower()
    assert "buy_signal" not in src.lower()
    assert "sell_signal" not in src.lower()


def test_no_roic_recompute_in_stage7():
    src = _all_source(STAGE7).lower()
    # May mention ROIC in comments / consume notes, but must not call Stage 6 calc
    assert "compute_roic" not in src
    assert "compute_stage6_metrics" not in src
    assert "compute_nopat" not in src
    assert "wacc_hurdle" not in src
    from fa.stage7.calc import compute_stage7_metrics

    # Stage 7 calc must advertise no recompute
    r = compute_stage7_metrics([])
    assert r.metrics.get("no_roic_recompute") is True
    assert r.metrics.get("no_wacc_recompute") is True


def test_no_scores_colors_buy_sell_averaged_mg():
    src = _all_source(STAGE7).lower()
    assert "blended_score" not in src
    assert "averaged_mg" not in src
    assert "management_grade" not in src
    assert "peer_percentile" not in src or "no iss" in src or "out of v1" in src
    assert "auto_red" not in src


def test_outcomes_enum_locked():
    from fa.stage7.questions import (
        STAGE7_OUTCOMES,
        ALIGNMENT_LABELS,
        MG_LENSES,
        S6_H7_CONSUMABLE,
        FALSE_POSITIVE_CATALOGUE,
        COMM_EVIDENCE_KINDS,
        EXECUTION_DELIVERY_TAGS,
    )

    assert STAGE7_OUTCOMES == {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}
    assert ALIGNMENT_LABELS == {"aligned", "tension", "opaque", "unknown"}
    assert [m[0] for m in MG_LENSES] == [f"MG{i}" for i in range(1, 10)]
    assert MG_LENSES[0][1] == "Capital Allocation Coherence"
    assert "S6_H7_ACQ_RETURN_OPACITY" in S6_H7_CONSUMABLE
    assert len(FALSE_POSITIVE_CATALOGUE) == 15
    assert FALSE_POSITIVE_CATALOGUE[0][0] == "FP-M1"
    assert COMM_EVIDENCE_KINDS == {
        "FACT",
        "GUIDANCE",
        "MANAGEMENT_CLAIM",
        "SYSTEM_INFERENCE",
    }
    assert "delivered" in EXECUTION_DELIVERY_TAGS


def test_no_numeric_gate_constants_in_ast():
    forbidden = {
        "PAY_PERCENTILE_GATE",
        "BUYBACK_YIELD_GATE",
        "DIVIDEND_PAYOUT_GATE",
        "OWNERSHIP_PCT_GATE",
        "ROIC_BAND",
        "WACC_HURDLE",
        "MG_SCORE",
    }
    for path in STAGE7.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                raise AssertionError(f"Forbidden gate name in {path}")


def test_stage6_unchanged_no_stage7_calls():
    """Stage 6 must not call Stage 7 (no redesign)."""
    src = _all_source(STAGE6)
    assert "run_stage7" not in src
    assert "evaluate_stage7" not in src
    assert "compute_stage7" not in src


def test_no_ticker_hardcodes_in_production_stage7():
    src = _all_source(STAGE7)
    for t in ("ROP", "META", "VISA", "KO", "NVDA", "ADBE", "TSLA", "BRK"):
        assert f'"{t}"' not in src
        assert f"'{t}'" not in src


def test_analyze_company_not_wired_to_stage7():
    pipe = Path("/workspace/investment_intelligence/fa/pipeline.py").read_text()
    assert "run_stage7" not in pipe
    assert "evaluate_stage7" not in pipe
