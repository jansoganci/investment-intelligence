"""Structured placeholder fields for LLM/human semantic review (no silent GAAP rewrite)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import StructuredSemanticReview


def load_semantic_from_fixture_notes(
    notes_path: Path | None = None,
    notes_payload: dict | None = None,
) -> StructuredSemanticReview:
    """Fill StructuredSemanticReview from fixture notes JSON for dry-run (no LLM)."""
    data: dict[str, Any] = {}
    if notes_payload:
        data = notes_payload
    elif notes_path and notes_path.exists():
        text = notes_path.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # markdown/text notes — leave mostly empty with excerpt
            return StructuredSemanticReview(
                covenants_notes=text[:2000] if text else None,
                review_source="fixture",
                filled=bool(text),
            )

    return StructuredSemanticReview(
        covenants_notes=data.get("covenants_notes"),
        going_concern_language=bool(data.get("going_concern_language", False)),
        going_concern_excerpt=data.get("going_concern_excerpt"),
        severe_solvency_language=bool(data.get("severe_solvency_language", False)),
        liquidity_mdna_flags=list(data.get("liquidity_mdna_flags") or []),
        leverage_optional_vs_required=data.get("leverage_optional_vs_required") or "not_assessed",
        near_term_liquidity_failure_credible=bool(
            data.get("near_term_liquidity_failure_credible", False)
        ),
        near_term_liquidity_notes=data.get("near_term_liquidity_notes"),
        off_balance_commitments_notes=data.get("off_balance_commitments_notes"),
        restricted_cash_notes=data.get("restricted_cash_notes"),
        undrawn_facilities_notes=data.get("undrawn_facilities_notes"),
        maturity_notes=data.get("maturity_notes"),
        other_flags=list(data.get("other_flags") or []),
        review_source=data.get("review_source") or "fixture",
        filled=True,
    )


def placeholder_semantic_review() -> StructuredSemanticReview:
    """Empty placeholder — LLM call not required in dry-run."""
    return StructuredSemanticReview(review_source="placeholder", filled=False)
