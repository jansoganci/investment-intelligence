"""Stage 7 — Management / Incentives / Capital Allocation (Operating).

No colors, no scores, no numeric gates, no BUY/SELL, no Stage 8.
Consumes S6_H7_* factually only — no ROIC recompute, no mechanical guilt.
NON-TERMINATING by default (terminates_later_stages=False).
"""
from .evaluate import evaluate_stage7
from .pipeline import run_stage7
from .report import render_stage7_markdown

__all__ = ["evaluate_stage7", "render_stage7_markdown", "run_stage7"]
