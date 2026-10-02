"""Fundamental Analysis v1 — financial backend + Stage 1–2 (Operating only)."""
__version__ = "0.1.0"

from .pipeline import analyze_company

__all__ = ["analyze_company", "__version__"]
