"""Thin post-artifact Registry write hooks (Plan §0.F).

Call AFTER stage / Final FA artifacts exist on disk. Artifacts remain SoR.
Registry failures never delete or roll back artifacts; registry transaction
rolls back only. Kill-switch: FA_REGISTRY_HOOKS=0|false|off.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from .db import RegistryError, registry_session
from .writers import record_final_fa_result, record_stage_after_artifact, start_run
from . import paths

logger = logging.getLogger(__name__)

_FALSEY = frozenset({"0", "false", "off", "no", "disabled"})


class RegistryHookError(Exception):
    """Raised when a registry hook fails and raise_on_error=True.

    Never indicates artifact rollback — artifact was already saved.
    """

    def __init__(self, message: str, *, cause: BaseException | None = None):
        super().__init__(message)
        self.cause = cause


def hooks_enabled() -> bool:
    raw = os.environ.get("FA_REGISTRY_HOOKS", "1")
    return str(raw).strip().lower() not in _FALSEY


def _is_uat_root(root: Path | None) -> bool:
    """True when FA root itself lives under a .../uat/... path segment."""
    if root is None:
        return False
    return "uat" in {p.lower() for p in Path(root).parts}


def resolve_uat_status(
    root: Path | None = None,
    *,
    uat_status: str | None = None,
) -> str:
    if uat_status is not None:
        return uat_status
    if _is_uat_root(root):
        return "pending"
    return "none"


def extract_terminates_later_stages(doc: dict[str, Any], stage: int) -> bool | None:
    """Pull terminates flag from saved doc without changing analytical content."""
    if "terminates_later_stages" in doc and doc["terminates_later_stages"] is not None:
        return bool(doc["terminates_later_stages"])
    if stage == 2 and "block_next" in doc:
        return bool(doc.get("block_next"))
    if stage == 1 and "block_stage2" in doc:
        return bool(doc.get("block_stage2"))
    return None


def hook_stage_after_save(
    *,
    ticker: str,
    stage: int,
    version_id: str,
    artifact_json_abs: Path | str,
    process_outcome: str | None = None,
    terminates_later_stages: bool | int | None = None,
    artifact_md_abs: Path | str | None = None,
    saved_at: str | None = None,
    root: Path | None = None,
    register: bool = True,
    skip_registry: bool = False,
    raise_on_error: bool = False,
    uat_status: str | None = None,
    run_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    actor: str = "script",
    trigger: str = "stage_run",
    intent: str | None = None,
    doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Post-artifact Stage hook. Safe for production save paths.

    Returns ``{ok, skipped, stage_result, error}``. Does not raise unless
    ``raise_on_error=True`` (after artifact already saved).
    """
    out: dict[str, Any] = {
        "ok": False,
        "skipped": False,
        "stage_result": None,
        "error": None,
    }
    if skip_registry or not register or not hooks_enabled():
        out["ok"] = True
        out["skipped"] = True
        return out

    json_abs = Path(artifact_json_abs)
    md_abs = Path(artifact_md_abs) if artifact_md_abs else None

    if doc is not None:
        if process_outcome is None:
            process_outcome = doc.get("process_outcome")
        if terminates_later_stages is None:
            terminates_later_stages = extract_terminates_later_stages(doc, stage)
        if saved_at is None:
            saved_at = doc.get("saved_at")

    uat = resolve_uat_status(root, uat_status=uat_status)

    try:
        if not json_abs.is_file():
            raise RegistryError(f"artifact missing for hook: {json_abs}")

        def _write(c: sqlite3.Connection) -> dict[str, Any]:
            row = record_stage_after_artifact(
                c,
                ticker=ticker,
                stage=stage,
                version_id=version_id,
                process_outcome=process_outcome,
                artifact_json_abs=json_abs,
                artifact_md_abs=md_abs,
                run_id=run_id,
                terminates_later_stages=terminates_later_stages,
                saved_at=saved_at,
                root=root,
                create_run_if_missing=True,
                actor=actor,
                trigger=trigger if uat == "none" else "uat",
                intent=intent or f"stage{stage}_only",
            )
            # Apply uat_status if not default (record_stage_after_artifact uses "none")
            if uat != "none" and not row.get("_idempotent"):
                c.execute(
                    "UPDATE stage_results SET uat_status = ? WHERE stage_result_id = ?",
                    (uat, row["stage_result_id"]),
                )
                row = dict(
                    c.execute(
                        "SELECT * FROM stage_results WHERE stage_result_id = ?",
                        (row["stage_result_id"],),
                    ).fetchone()
                )
                row["_idempotent"] = False
            return row

        if conn is not None:
            row = _write(conn)
        else:
            with registry_session(root) as c:
                row = _write(c)
        out["ok"] = True
        out["stage_result"] = row
        return out
    except Exception as exc:  # noqa: BLE001 — surface, never roll back artifact
        msg = f"registry stage hook failed (artifact intact): {exc}"
        logger.warning(msg)
        out["error"] = str(exc)
        out["ok"] = False
        if raise_on_error:
            raise RegistryHookError(msg, cause=exc) from exc
        return out


def hook_final_fa_after_artifact(
    *,
    ticker: str,
    version_id: str,
    artifact_json_abs: Path | str,
    final_state: str | None = None,
    technical_eligible: bool | int | None = None,
    artifact_md_abs: Path | str | None = None,
    saved_at: str | None = None,
    root: Path | None = None,
    register: bool = True,
    skip_registry: bool = False,
    raise_on_error: bool = False,
    uat_status: str | None = None,
    run_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    stage_result_ids_consumed: list[str] | None = None,
    actor: str = "script",
    trigger: str = "final_fa",
    intent: str | None = None,
    doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Post-artifact Final FA hook (synthesis itself NOT implemented).

    Returns ``{ok, skipped, final_fa_result, error}``.
    """
    out: dict[str, Any] = {
        "ok": False,
        "skipped": False,
        "final_fa_result": None,
        "error": None,
    }
    if skip_registry or not register or not hooks_enabled():
        out["ok"] = True
        out["skipped"] = True
        return out

    json_abs = Path(artifact_json_abs)
    md_abs = Path(artifact_md_abs) if artifact_md_abs else None

    if doc is not None:
        if final_state is None:
            final_state = doc.get("final_state")
        if technical_eligible is None and "technical_eligible" in doc:
            technical_eligible = doc.get("technical_eligible")
        if saved_at is None:
            saved_at = doc.get("saved_at")

    uat = resolve_uat_status(root, uat_status=uat_status)

    try:
        if not json_abs.is_file():
            raise RegistryError(f"artifact missing for hook: {json_abs}")

        json_rel = paths.rel_under_fa_data(json_abs, root)
        md_rel = paths.rel_under_fa_data(md_abs, root) if md_abs else None

        def _write(c: sqlite3.Connection) -> dict[str, Any]:
            rid = run_id
            if rid is None:
                rid = start_run(
                    c,
                    ticker,
                    actor=actor,
                    trigger=trigger if uat == "none" else "uat",
                    intent=intent or "final_fa_synth",
                )
            row = record_final_fa_result(
                c,
                ticker=ticker,
                version_id=version_id,
                final_state=final_state,
                artifact_json_path=json_rel,
                artifact_md_path=md_rel,
                run_id=rid,
                technical_eligible=technical_eligible,
                saved_at=saved_at,
                is_current=True,
                stage_result_ids_consumed=stage_result_ids_consumed,
                uat_status=uat,
                require_artifact=True,
                root=root,
            )
            return row

        if conn is not None:
            row = _write(conn)
        else:
            with registry_session(root) as c:
                row = _write(c)
        out["ok"] = True
        out["final_fa_result"] = row
        return out
    except Exception as exc:  # noqa: BLE001
        msg = f"registry final_fa hook failed (artifact intact): {exc}"
        logger.warning(msg)
        out["error"] = str(exc)
        out["ok"] = False
        if raise_on_error:
            raise RegistryHookError(msg, cause=exc) from exc
        return out


def register_final_fa_artifact(
    *,
    ticker: str,
    version_id: str,
    artifact_json_abs: Path | str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Public alias for future Final FA synthesis callers."""
    return hook_final_fa_after_artifact(
        ticker=ticker,
        version_id=version_id,
        artifact_json_abs=artifact_json_abs,
        **kwargs,
    )
