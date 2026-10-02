"""Stage 8 — Valuation / Intrinsic Value / Margin of Safety (Operating).

No colors, no scores, no BUY/SELL, no universal valuation thresholds.
No CAPM engine, no method averaging, no Stage 9.
NON-TERMINATING by default (terminates_later_stages=False).
Independent of fa.pipeline.analyze_company.
"""
from .evaluate import evaluate_stage8
from .pipeline import run_stage8
from .report import render_stage8_markdown

__all__ = ["evaluate_stage8", "render_stage8_markdown", "run_stage8"]
