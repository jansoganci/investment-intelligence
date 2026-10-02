"""Stage 3 — Cash Generation (Operating). No colors, no thresholds, no Stage 4.

Evidence/review stage: does not mechanically terminate later stages.
"""
from .evaluate import evaluate_stage3
from .pipeline import run_stage3
from .report import render_stage3_markdown

__all__ = ["evaluate_stage3", "render_stage3_markdown", "run_stage3"]
