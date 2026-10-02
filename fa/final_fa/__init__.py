"""Final FA Synthesis — Plan §0 locked operating model.

Reconciliation of Stages 1–9 → eligibility + supports + challenges +
unresolved + human review. NOT averaging. GREEN ≠ BUY.
"""
from .evaluate import evaluate_final_fa, extract_carries
from .models import FinalFaSynthesis
from .pipeline import load_stage_currents, run_final_fa
from .report import render_final_fa_markdown
from .storage import (
    final_fa_current_path,
    load_final_fa_current,
    save_final_fa_report,
)

__all__ = [
    "FinalFaSynthesis",
    "evaluate_final_fa",
    "extract_carries",
    "final_fa_current_path",
    "load_final_fa_current",
    "load_stage_currents",
    "render_final_fa_markdown",
    "run_final_fa",
    "save_final_fa_report",
]
