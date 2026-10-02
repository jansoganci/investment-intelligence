"""Stage 9 — Industry / Competition / Macro / External Risk (Operating).

No colors, no scores, no BUY/SELL, no numeric risk gates, no averaged external-risk score.
No industry warehouse. No final FA synthesis.
ER2: Gate2/S1/S5 as hypotheses only — no S5 pricing-power redo / no S1 thesis restatement.
ER8: 3–7 observable falsifiers + monitoring — NOT a giant risk register.
NON-TERMINATING by default (terminates_later_stages=False).
Independent of fa.pipeline.analyze_company.
"""
from .evaluate import evaluate_stage9
from .pipeline import run_stage9
from .report import render_stage9_markdown

__all__ = ["evaluate_stage9", "render_stage9_markdown", "run_stage9"]
