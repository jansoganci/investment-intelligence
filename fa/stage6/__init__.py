"""Stage 6 — ROIC / Reinvestment (Operating). No colors, no thresholds, no Stage 7.

Evidence/review stage: does not mechanically terminate later stages.
Benchmark ≠ hard gate. Numeric ROIC/ROIIC/WACC bands NOT LOCKED.
Incremental ROIC ≠ Stage 5 Incremental OM (IOM).
"""
from .evaluate import evaluate_stage6
from .pipeline import run_stage6
from .report import render_stage6_markdown

__all__ = ["evaluate_stage6", "render_stage6_markdown", "run_stage6"]
