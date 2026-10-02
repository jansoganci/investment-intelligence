"""Stage 5 semantic heuristic extraction."""
from __future__ import annotations

from fa.stage5.semantic import heuristic_stage5_semantic, placeholder_stage5_semantic


def test_placeholder_not_filled():
    s = placeholder_stage5_semantic()
    assert s.filled is False


def test_heuristic_pricing_and_margin():
    text = (
        "Gross margin expanded due to price/mix benefits. "
        "The company demonstrated pricing power and pass-through of higher input costs. "
        "Operating leverage improved from scale economies. "
        "Share-based compensation and non-GAAP adjusted operating margin were discussed."
    )
    s = heuristic_stage5_semantic(text)
    assert s.filled
    topics = {f.topic for f in s.findings}
    assert "pricing_power" in topics or s.pricing_power_notes
    assert "margin_bridge" in topics or s.margin_bridge_notes
    assert all(f.evidence_kind in {"FACT", "COMPANY_EXPLANATION", "MODEL_INFERENCE"} for f in s.findings)
