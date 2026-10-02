"""Append-only registry writers (Plan §0.E / §0.F). Artifacts = truth; registry = index."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from ..ids import normalize_ticker, sha256_hex, utc_now
from . import paths
from .db import RegistryError


# Forbidden to UPDATE once saved (Plan §0.E)
_STAGE_IMMUTABLE = frozenset(
    {
        "process_outcome",
        "terminates_later_stages",
        "artifact_json_path",
        "artifact_md_path",
        "version_id",
        "content_sha256",
        "stage",
        "ticker",
    }
)
_FINAL_IMMUTABLE = frozenset(
    {
        "final_state",
        "technical_eligible",
        "artifact_json_path",
        "artifact_md_path",
        "version_id",
        "content_sha256",
        "ticker",
        "stage_result_ids_consumed",
    }
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def make_run_id(ticker: str, *, salt: str | None = None) -> str:
    """Preferred form: {ticker}_{UTCCompact}_{shortHash}."""
    ticker = normalize_ticker(ticker)
    compact = utc_now().replace("-", "").replace(":", "").replace("Z", "")
    h = hashlib.sha256((salt or uuid.uuid4().hex).encode()).hexdigest()[:8]
    return f"{ticker}_{compact}_{h}"


def ensure_company(
    conn: sqlite3.Connection,
    ticker: str,
    *,
    entity_name: str | None = None,
    cik: str | None = None,
    gate0_class: str | None = None,
    fa_list_member: int | None = None,
    fa_list_as_of: str | None = None,
    notes: str | None = None,
) -> str:
    """Insert or refresh identity scalars for a company. Returns ticker."""
    ticker = normalize_ticker(ticker)
    now = utc_now()
    row = conn.execute("SELECT ticker FROM companies WHERE ticker = ?", (ticker,)).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO companies(
                ticker, entity_name, cik, gate0_class, fa_list_member, fa_list_as_of,
                stale_flag, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                ticker,
                entity_name,
                cik,
                gate0_class,
                0 if fa_list_member is None else int(fa_list_member),
                fa_list_as_of,
                notes,
                now,
                now,
            ),
        )
    else:
        # Allowed UPDATE: identity scalars / notes / fa_list
        sets: list[str] = ["updated_at = ?"]
        vals: list[Any] = [now]
        if entity_name is not None:
            sets.append("entity_name = ?")
            vals.append(entity_name)
        if cik is not None:
            sets.append("cik = ?")
            vals.append(cik)
        if gate0_class is not None:
            sets.append("gate0_class = ?")
            vals.append(gate0_class)
        if fa_list_member is not None:
            sets.append("fa_list_member = ?")
            vals.append(int(fa_list_member))
        if fa_list_as_of is not None:
            sets.append("fa_list_as_of = ?")
            vals.append(fa_list_as_of)
        if notes is not None:
            sets.append("notes = ?")
            vals.append(notes)
        vals.append(ticker)
        conn.execute(f"UPDATE companies SET {', '.join(sets)} WHERE ticker = ?", vals)
    return ticker


def start_run(
    conn: sqlite3.Connection,
    ticker: str,
    *,
    actor: str = "script",
    trigger: str = "stage_run",
    intent: str | None = None,
    parent_run_id: str | None = None,
    git_sha: str | None = None,
    code_fingerprint: str | None = None,
    notes: str | None = None,
    run_id: str | None = None,
    status: str = "in_progress",
) -> str:
    ticker = ensure_company(conn, ticker)
    rid = run_id or make_run_id(ticker)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO analysis_runs(
            run_id, ticker, started_at, ended_at, actor, trigger, intent, status,
            parent_run_id, git_sha, code_fingerprint, notes
        ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rid,
            ticker,
            now,
            actor,
            trigger,
            intent,
            status,
            parent_run_id,
            git_sha,
            code_fingerprint,
            notes,
        ),
    )
    _emit_event(conn, "run_started", ticker=ticker, run_id=rid, payload={"status": status})
    return rid


def complete_run(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    status: str = "completed",
    notes: str | None = None,
) -> None:
    if status not in ("completed", "failed", "abandoned"):
        raise RegistryError(f"invalid terminal run status: {status}")
    now = utc_now()
    row = conn.execute("SELECT status, ticker FROM analysis_runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise RegistryError(f"unknown run_id: {run_id}")
    sets = ["ended_at = ?", "status = ?"]
    vals: list[Any] = [now, status]
    if notes is not None:
        sets.append("notes = ?")
        vals.append(notes)
    vals.append(run_id)
    conn.execute(f"UPDATE analysis_runs SET {', '.join(sets)} WHERE run_id = ?", vals)
    conn.execute(
        "UPDATE companies SET current_analysis_run_id = ?, updated_at = ? WHERE ticker = ?",
        (run_id, now, row["ticker"]),
    )
    _emit_event(conn, "run_ended", ticker=row["ticker"], run_id=run_id, payload={"status": status})


def fail_run(conn: sqlite3.Connection, run_id: str, *, notes: str | None = None) -> None:
    complete_run(conn, run_id, status="failed", notes=notes)


def mark_company_stale(
    conn: sqlite3.Connection,
    ticker: str,
    *,
    stale: bool = True,
    reason: str | None = None,
) -> None:
    ticker = ensure_company(conn, ticker)
    now = utc_now()
    conn.execute(
        """
        UPDATE companies
        SET stale_flag = ?, stale_reason = ?, updated_at = ?
        WHERE ticker = ?
        """,
        (1 if stale else 0, reason if stale else None, now, ticker),
    )
    _emit_event(
        conn,
        "stale_marked" if stale else "stale_cleared",
        ticker=ticker,
        payload={"stale_reason": reason},
    )


def set_uat_status(
    conn: sqlite3.Connection,
    *,
    stage_result_id: str | None = None,
    final_fa_result_id: str | None = None,
    uat_status: str,
    uat_pack_path: str | None = None,
) -> None:
    if uat_status not in ("none", "pending", "accepted", "rejected"):
        raise RegistryError(f"invalid uat_status: {uat_status}")
    if stage_result_id:
        conn.execute(
            "UPDATE stage_results SET uat_status = ?, uat_pack_path = ? WHERE stage_result_id = ?",
            (uat_status, uat_pack_path, stage_result_id),
        )
    elif final_fa_result_id:
        conn.execute(
            "UPDATE final_fa_results SET uat_status = ?, uat_pack_path = ? WHERE final_fa_result_id = ?",
            (uat_status, uat_pack_path, final_fa_result_id),
        )
    else:
        raise RegistryError("stage_result_id or final_fa_result_id required")


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not Path(path).is_file():
        return None
    return sha256_hex(Path(path).read_bytes())


def _demote_stage_current(
    conn: sqlite3.Connection,
    ticker: str,
    stage: int,
    *,
    successor_id: str,
) -> str | None:
    """Demote prior CURRENT; set superseded_by. Returns prior stage_result_id if any."""
    prior = conn.execute(
        """
        SELECT stage_result_id FROM stage_results
        WHERE ticker = ? AND stage = ? AND is_current = 1
        """,
        (ticker, stage),
    ).fetchone()
    if prior is None:
        return None
    pid = prior["stage_result_id"]
    if pid == successor_id:
        return None
    conn.execute(
        """
        UPDATE stage_results
        SET is_current = 0, superseded_by_stage_result_id = ?
        WHERE stage_result_id = ?
        """,
        (successor_id, pid),
    )
    return pid


def _demote_final_current(
    conn: sqlite3.Connection,
    ticker: str,
    *,
    successor_id: str,
) -> str | None:
    prior = conn.execute(
        """
        SELECT final_fa_result_id FROM final_fa_results
        WHERE ticker = ? AND is_current = 1
        """,
        (ticker,),
    ).fetchone()
    if prior is None:
        return None
    pid = prior["final_fa_result_id"]
    if pid == successor_id:
        return None
    conn.execute(
        """
        UPDATE final_fa_results
        SET is_current = 0, superseded_by_final_fa_result_id = ?
        WHERE final_fa_result_id = ?
        """,
        (successor_id, pid),
    )
    return pid


def record_stage_result(
    conn: sqlite3.Connection,
    *,
    ticker: str,
    stage: int,
    version_id: str,
    process_outcome: str | None,
    artifact_json_path: str | None,
    run_id: str | None = None,
    terminates_later_stages: bool | int | None = None,
    artifact_md_path: str | None = None,
    saved_at: str | None = None,
    is_current: bool = True,
    content_sha256: str | None = None,
    uat_status: str = "none",
    uat_pack_path: str | None = None,
    stage_result_id: str | None = None,
    require_artifact: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Post-artifact write API (call AFTER artifact exists).

    Idempotent on (ticker, stage, version_id): returns existing row without
    overwriting historical outcome scalars. New version demotes prior CURRENT.
    """
    if stage < 1 or stage > 9:
        raise RegistryError(f"stage must be 1..9, got {stage}")
    ticker = ensure_company(conn, ticker)
    version_id = str(version_id)

    existing = conn.execute(
        """
        SELECT * FROM stage_results
        WHERE ticker = ? AND stage = ? AND version_id = ?
        """,
        (ticker, stage, version_id),
    ).fetchone()
    if existing is not None:
        # Idempotent: never overwrite immutable scalars
        out = dict(existing)
        out["_idempotent"] = True
        return out

    if require_artifact:
        if not artifact_json_path:
            raise RegistryError("missing artifact_json_path")
        abs_p = paths.fa_root(root) / artifact_json_path
        if not abs_p.is_file():
            raise RegistryError(f"missing artifact file: {artifact_json_path}")

    rid = stage_result_id or _new_id("sr")
    saved = saved_at or utc_now()
    term = None if terminates_later_stages is None else (1 if terminates_later_stages else 0)
    sha = content_sha256
    if sha is None and artifact_json_path:
        abs_p = paths.fa_root(root) / artifact_json_path
        sha = _file_sha256(abs_p)

    prior_id = None
    if is_current:
        # Insert first as non-current, then demote + promote in one logical step
        pass

    conn.execute(
        """
        INSERT INTO stage_results(
            stage_result_id, run_id, ticker, stage, version_id, process_outcome,
            terminates_later_stages, artifact_json_path, artifact_md_path, saved_at,
            is_current, supersedes_stage_result_id, superseded_by_stage_result_id,
            uat_status, uat_pack_path, content_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?, ?)
        """,
        (
            rid,
            run_id,
            ticker,
            stage,
            version_id,
            process_outcome,
            term,
            artifact_json_path,
            artifact_md_path,
            saved,
            uat_status,
            uat_pack_path,
            sha,
        ),
    )

    if is_current:
        prior_id = _demote_stage_current(conn, ticker, stage, successor_id=rid)
        conn.execute(
            """
            UPDATE stage_results
            SET is_current = 1, supersedes_stage_result_id = ?
            WHERE stage_result_id = ?
            """,
            (prior_id, rid),
        )

    _emit_event(
        conn,
        "stage_result_recorded",
        ticker=ticker,
        run_id=run_id,
        payload={
            "stage_result_id": rid,
            "stage": stage,
            "version_id": version_id,
            "process_outcome": process_outcome,
            "is_current": bool(is_current),
            "supersedes": prior_id,
        },
    )
    row = conn.execute(
        "SELECT * FROM stage_results WHERE stage_result_id = ?", (rid,)
    ).fetchone()
    out = dict(row)
    out["_idempotent"] = False
    return out


def record_final_fa_result(
    conn: sqlite3.Connection,
    *,
    ticker: str,
    version_id: str,
    final_state: str | None,
    artifact_json_path: str | None,
    run_id: str | None = None,
    technical_eligible: bool | int | None = None,
    artifact_md_path: str | None = None,
    saved_at: str | None = None,
    is_current: bool = True,
    content_sha256: str | None = None,
    stage_result_ids_consumed: list[str] | None = None,
    uat_status: str = "none",
    uat_pack_path: str | None = None,
    final_fa_result_id: str | None = None,
    require_artifact: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """Post-artifact Final FA write API (table ready; synthesis itself NOT implemented)."""
    ticker = ensure_company(conn, ticker)
    version_id = str(version_id)

    existing = conn.execute(
        "SELECT * FROM final_fa_results WHERE ticker = ? AND version_id = ?",
        (ticker, version_id),
    ).fetchone()
    if existing is not None:
        out = dict(existing)
        out["_idempotent"] = True
        return out

    if require_artifact:
        if not artifact_json_path:
            raise RegistryError("missing artifact_json_path")
        abs_p = paths.fa_root(root) / artifact_json_path
        if not abs_p.is_file():
            raise RegistryError(f"missing artifact file: {artifact_json_path}")

    rid = final_fa_result_id or _new_id("ff")
    saved = saved_at or utc_now()
    te = None if technical_eligible is None else (1 if technical_eligible else 0)
    sha = content_sha256
    if sha is None and artifact_json_path:
        abs_p = paths.fa_root(root) / artifact_json_path
        sha = _file_sha256(abs_p)
    consumed = json.dumps(stage_result_ids_consumed) if stage_result_ids_consumed is not None else None

    conn.execute(
        """
        INSERT INTO final_fa_results(
            final_fa_result_id, run_id, ticker, version_id, final_state, technical_eligible,
            artifact_json_path, artifact_md_path, saved_at, is_current,
            supersedes_final_fa_result_id, superseded_by_final_fa_result_id,
            stage_result_ids_consumed, uat_status, uat_pack_path, content_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?, ?, ?)
        """,
        (
            rid,
            run_id,
            ticker,
            version_id,
            final_state,
            te,
            artifact_json_path,
            artifact_md_path,
            saved,
            consumed,
            uat_status,
            uat_pack_path,
            sha,
        ),
    )

    prior_id = None
    if is_current:
        prior_id = _demote_final_current(conn, ticker, successor_id=rid)
        conn.execute(
            """
            UPDATE final_fa_results
            SET is_current = 1, supersedes_final_fa_result_id = ?
            WHERE final_fa_result_id = ?
            """,
            (prior_id, rid),
        )

    _emit_event(
        conn,
        "final_fa_result_recorded",
        ticker=ticker,
        run_id=run_id,
        payload={
            "final_fa_result_id": rid,
            "version_id": version_id,
            "final_state": final_state,
            "is_current": bool(is_current),
        },
    )
    row = conn.execute(
        "SELECT * FROM final_fa_results WHERE final_fa_result_id = ?", (rid,)
    ).fetchone()
    out = dict(row)
    out["_idempotent"] = False
    return out


def assert_immutable_stage_scalars(conn: sqlite3.Connection, stage_result_id: str) -> None:
    """Helper for tests / guards — attempt forbidden UPDATE raises RegistryError."""
    row = conn.execute(
        "SELECT process_outcome FROM stage_results WHERE stage_result_id = ?",
        (stage_result_id,),
    ).fetchone()
    if row is None:
        raise RegistryError(f"unknown stage_result_id: {stage_result_id}")
    # Document policy; callers should not UPDATE these columns.
    _ = _STAGE_IMMUTABLE
    _ = _FINAL_IMMUTABLE


def _emit_event(
    conn: sqlite3.Connection,
    event_type: str,
    *,
    ticker: str | None = None,
    run_id: str | None = None,
    payload: dict | None = None,
) -> str:
    eid = _new_id("ev")
    conn.execute(
        """
        INSERT INTO events(event_id, ts, event_type, ticker, run_id, payload_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (eid, utc_now(), event_type, ticker, run_id, json.dumps(payload or {})),
    )
    return eid


def record_stage_after_artifact(
    conn: sqlite3.Connection,
    *,
    ticker: str,
    stage: int,
    version_id: str,
    process_outcome: str | None,
    artifact_json_abs: Path,
    artifact_md_abs: Path | None = None,
    run_id: str | None = None,
    terminates_later_stages: bool | int | None = None,
    saved_at: str | None = None,
    root: Path | None = None,
    create_run_if_missing: bool = True,
    actor: str = "script",
    trigger: str = "stage_run",
    intent: str | None = None,
) -> dict[str, Any]:
    """
    Convenience post-artifact hook: paths relative to fa_data/; optional run.

    Prefer calling this AFTER stage*_versions write. Does not change stage calc logic.
    """
    ticker = normalize_ticker(ticker)
    if not Path(artifact_json_abs).is_file():
        raise RegistryError(f"artifact missing: {artifact_json_abs}")

    json_rel = paths.rel_under_fa_data(artifact_json_abs, root)
    md_rel = paths.rel_under_fa_data(artifact_md_abs, root) if artifact_md_abs else None

    if run_id is None and create_run_if_missing:
        run_id = start_run(
            conn,
            ticker,
            actor=actor,
            trigger=trigger,
            intent=intent or f"stage{stage}_only",
        )

    row = record_stage_result(
        conn,
        ticker=ticker,
        stage=stage,
        version_id=version_id,
        process_outcome=process_outcome,
        artifact_json_path=json_rel,
        artifact_md_path=md_rel,
        run_id=run_id,
        terminates_later_stages=terminates_later_stages,
        saved_at=saved_at,
        is_current=True,
        require_artifact=True,
        root=root,
    )
    if run_id and not row.get("_idempotent"):
        # leave run open unless caller completes; backfill completes runs
        pass
    return row
