"""Boundaries: IOM ≠ ROIIC; no Stage 7; no thresholds; Stages 1–5 untouched calls."""
from __future__ import annotations

import ast
from pathlib import Path

STAGE6 = Path("/workspace/investment_intelligence/fa/stage6")
STAGE5 = Path("/workspace/investment_intelligence/fa/stage5")


def _all_source(path: Path) -> str:
    return "\n".join(p.read_text() for p in path.glob("*.py"))


def test_no_stage7_impl_or_grades():
    src = _all_source(STAGE6)
    assert "run_stage7" not in src
    assert "evaluate_stage7" not in src
    assert "management_grade" not in src.lower()
    assert "DEF 14A" not in src or "no Stage 7" in src or "Stage 7" in src


def test_no_buy_sell_rog_scores_thresholds():
    src = _all_source(STAGE6).lower()
    assert "buy_signal" not in src
    assert "sell_signal" not in src
    assert "blended_score" not in src
    assert "peer_percentile" not in src or "never peer-percentile" in src
    # No WACC hurdle constants as gates
    assert "wacc_hurdle" not in src or "no_wacc_hurdle" in src


def test_outcomes_enum_locked():
    from fa.stage6.questions import (
        STAGE6_OUTCOMES,
        RUNWAY_LABELS,
        INCREMENTAL_MEANING_CLASSES,
        STAGE7_HANDOFF_FLAGS,
        RC_DIMENSIONS,
    )

    assert STAGE6_OUTCOMES == {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}
    assert RUNWAY_LABELS == {"ample", "limited", "unclear", "not_applicable"}
    assert "structurally_informative" in INCREMENTAL_MEANING_CLASSES
    assert "not_meaningful" in INCREMENTAL_MEANING_CLASSES
    assert "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST" in STAGE7_HANDOFF_FLAGS
    assert [r[0] for r in RC_DIMENSIONS] == [f"RC{i}" for i in range(1, 9)]


def test_no_numeric_roic_band_gates_in_ast():
    forbidden = {"ROIC_BAND", "ROIIC_BAND", "WACC_HURDLE", "NUMERIC_ROIC_GATE"}
    for path in STAGE6.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                raise AssertionError(f"Forbidden band name in {path}")


def test_stage5_iom_not_reimplemented_as_roiic():
    """Stage 6 must not reuse Stage 5 IOM namespace as ROIIC."""
    src = _all_source(STAGE6)
    # May mention IOM for boundary honesty, but must not compute ΔOP/ΔRev as ROIIC
    assert "incremental_om(" not in src
    assert "ΔOP/ΔRev" not in src or "≠" in src or "ne_iom" in src.lower() or "ne iom" in src.lower()
    from fa.stage5.calc import incremental_om
    from fa.stage6.calc import _classify_incremental

    # Stage 5 IOM on ΔOP/ΔRev
    iom = incremental_om(10.0, 50.0, window_id="yoy")
    assert iom.incremental_om == 0.2
    # Stage 6 ROIIC on ΔNOPAT/ΔIC — different construct
    roiic = _classify_incremental(10.0, 50.0, window_id="yoy")
    assert roiic.incremental_roic == 0.2
    assert "Stage 5" in roiic.stage5_boundary or "IOM" in roiic.stage5_boundary
    # Different field names
    assert not hasattr(roiic, "incremental_om")
    assert not hasattr(iom, "incremental_roic")


def test_stage5_unchanged_no_stage6_calls():
    """Stage 5 must not call Stage 6 (no redesign)."""
    src = _all_source(STAGE5)
    assert "run_stage6" not in src
    assert "evaluate_stage6" not in src
    assert "compute_roic" not in src.lower() or "no_roic" in src.lower()


def test_no_ticker_hardcodes_in_production_stage6():
    src = _all_source(STAGE6)
    for t in ("ROP", "VISA", "KO", "NVDA", "ADBE", "TSLA", "NCLH", "RIO"):
        # Allow mentions only inside comments about UAT roles? Hard ban in production code strings
        # Simple: no quoted ticker literals
        assert f'"{t}"' not in src
        assert f"'{t}'" not in src
