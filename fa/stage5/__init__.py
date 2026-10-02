"""Stage 5 — Margins / Business Economics (Operating). No colors, no bands, no Stage 6.

Evidence/review stage: does not mechanically terminate later stages.
Benchmark ≠ hard gate. Numeric GM/OP/IM bands NOT LOCKED. No BE9 ROIC.
Incremental OM ≠ ROIIC.
"""
from .evaluate import evaluate_stage5
from .pipeline import run_stage5
from .report import render_stage5_markdown

__all__ = ["evaluate_stage5", "render_stage5_markdown", "run_stage5"]
