"""Stage 4 — Growth Quality / Runway (Operating). No colors, no thresholds, no Stage 5.

Evidence/review stage: does not mechanically terminate later stages.
Benchmark ≠ hard gate. NC* NOT LOCKED.
"""
from .evaluate import evaluate_stage4
from .pipeline import run_stage4
from .report import render_stage4_markdown

__all__ = ["evaluate_stage4", "render_stage4_markdown", "run_stage4"]
