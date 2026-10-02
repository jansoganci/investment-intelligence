"""Field lineage helpers."""
from __future__ import annotations

from typing import Any

from .ids import utc_now
from .models import FieldLineage


def make_lineage(
    field: str,
    value: Any,
    period_key: str,
    version_id: str,
    source_kind: str,
    source_ref: str | None = None,
    source_id: str | None = None,
    reviewed_by: str = "none",
    review_status: str = "pending",
    notes: str | None = None,
    uncertain: bool = False,
) -> FieldLineage:
    return FieldLineage(
        field=field,
        value=value,
        period_key=period_key,
        version_id=version_id,
        source_kind=source_kind,
        source_ref=source_ref,
        source_id=source_id,
        fetched_or_entered_at=utc_now(),
        reviewed_by=reviewed_by,
        review_status=review_status,  # type: ignore[arg-type]
        notes=notes,
        uncertain=uncertain,
    )


def lineage_to_dicts(items: list[FieldLineage] | list[dict]) -> list[dict]:
    out = []
    for x in items:
        if isinstance(x, FieldLineage):
            out.append(x.to_dict())
        else:
            out.append(dict(x))
    return out


def attach_field_with_lineage(
    doc: dict[str, Any],
    field: str,
    value: Any,
    *,
    source_kind: str,
    source_ref: str | None = None,
    source_id: str | None = None,
    notes: str | None = None,
    uncertain: bool = False,
    review_status: str = "pending",
    reviewed_by: str = "machine_extracted",
    null_reason: dict[str, str] | None = None,
) -> None:
    """Set field value and append lineage record on a period document."""
    doc.setdefault("fields", {})[field] = value
    lin = make_lineage(
        field=field,
        value=value,
        period_key=doc.get("period_key", ""),
        version_id=doc.get("version_id", ""),
        source_kind=source_kind,
        source_ref=source_ref,
        source_id=source_id,
        notes=notes,
        uncertain=uncertain,
        review_status=review_status,
        reviewed_by=reviewed_by,
    )
    d = lin.to_dict()
    # Architecture review_level alias (machine_extracted / agent_reviewed / user_verified)
    d["review_level"] = reviewed_by if reviewed_by != "none" else "machine_extracted"
    doc.setdefault("lineage", []).append(d)
    if uncertain:
        doc.setdefault("field_uncertainty", {})[field] = notes or "uncertain mapping"
    if value is None and (null_reason is not None or notes):
        # Prefer structured {code, detail}; fall back to detail string for older callers
        doc.setdefault("null_reasons", {})[field] = (
            null_reason if null_reason is not None else notes
        )
