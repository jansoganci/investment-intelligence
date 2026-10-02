"""Company FA History / Run Registry — unit + integration tests (Plan §0)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from fa.registry import (
    RegistryError,
    backup_registry,
    backfill_registry,
    complete_run,
    detect_drift,
    ensure_company,
    export_company_stage_matrix,
    fail_run,
    fetch_company_stage_matrix,
    mark_company_stale,
    open_registry,
    record_final_fa_result,
    record_stage_after_artifact,
    record_stage_result,
    repair_drift_from_disk,
    restore_registry_from_backup,
    start_run,
)
from fa.registry.db import init_schema
from fa.registry import paths as reg_paths


@pytest.fixture()
def reg_root(fa_root, monkeypatch):
    """Isolated FA_ROOT with registry paths bound."""
    monkeypatch.setattr(reg_paths.config, "FA_ROOT", fa_root)
    return fa_root


def _write_stage_artifact(
    root: Path,
    ticker: str,
    stage: int,
    version_id: str,
    *,
    process_outcome: str = "PROCEED",
    terminates: bool = False,
    as_current: bool = True,
) -> Path:
    thesis = root / "companies" / ticker / "Thesis"
    vdir = thesis / f"stage{stage}_versions"
    vdir.mkdir(parents=True, exist_ok=True)
    doc = {
        "ticker": ticker,
        "version_id": version_id,
        "process_outcome": process_outcome,
        "terminates_later_stages": terminates,
        "saved_at": "2026-09-29T12:00:00Z",
        "date": "2026-09-29T12:00:00Z",
    }
    jp = vdir / f"stage{stage}_{version_id}.json"
    jp.write_text(json.dumps(doc), encoding="utf-8")
    (vdir / f"stage{stage}_{version_id}.md").write_text(f"# stage {stage}\n", encoding="utf-8")
    if as_current:
        (thesis / f"stage{stage}_CURRENT.json").write_text(json.dumps(doc), encoding="utf-8")
        (thesis / f"stage{stage}_CURRENT.md").write_text(f"# stage {stage}\n", encoding="utf-8")
    meta = root / "companies" / ticker / "meta.json"
    if not meta.exists():
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(
            json.dumps(
                {
                    "ticker": ticker,
                    "entity_name": f"{ticker} Corp",
                    "cik": "0000123456",
                    "gate0_class": "operating",
                    "stale": False,
                }
            ),
            encoding="utf-8",
        )
    return jp


# --- DB creation ---


def test_db_creation_tables_and_views(reg_root):
    conn = open_registry(reg_root)
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        }
        assert "companies" in tables
        assert "analysis_runs" in tables
        assert "stage_results" in tables
        assert "final_fa_results" in tables
        assert "events" in tables
        views = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
            )
        }
        assert "v_company_stage_matrix" in views
        assert "v_company_current_fa" in views
        assert "v_company_history" in views
        assert "v_stale_analysis" in views
        assert reg_paths.registry_db_path(reg_root).is_file()
    finally:
        conn.close()


# --- inserts / runs ---


def test_inserts_company_run_stage(reg_root):
    jp = _write_stage_artifact(reg_root, "AAA", 8, "v001")
    conn = open_registry(reg_root)
    try:
        ensure_company(conn, "AAA", entity_name="AAA Corp", gate0_class="operating")
        rid = start_run(conn, "AAA", intent="stage8_only")
        row = record_stage_result(
            conn,
            ticker="AAA",
            stage=8,
            version_id="v001",
            process_outcome="REVIEW_REQUIRED",
            artifact_json_path=str(jp.relative_to(reg_root)),
            run_id=rid,
            terminates_later_stages=False,
            is_current=True,
            root=reg_root,
        )
        complete_run(conn, rid)
        conn.commit()
        assert row["process_outcome"] == "REVIEW_REQUIRED"
        assert row["is_current"] == 1
        n = conn.execute("SELECT COUNT(*) FROM stage_results").fetchone()[0]
        assert n == 1
        status = conn.execute(
            "SELECT status FROM analysis_runs WHERE run_id = ?", (rid,)
        ).fetchone()[0]
        assert status == "completed"
    finally:
        conn.close()


# --- append-only + CURRENT demotion ---


def test_append_only_and_current_demotion(reg_root):
    _write_stage_artifact(reg_root, "BBB", 4, "v001", process_outcome="CONDITIONAL")
    _write_stage_artifact(reg_root, "BBB", 4, "v002", process_outcome="PROCEED")
    conn = open_registry(reg_root)
    try:
        r1 = start_run(conn, "BBB", intent="stage4_only")
        a = record_stage_result(
            conn,
            ticker="BBB",
            stage=4,
            version_id="v001",
            process_outcome="CONDITIONAL",
            artifact_json_path="companies/BBB/Thesis/stage4_versions/stage4_v001.json",
            run_id=r1,
            is_current=True,
            root=reg_root,
        )
        r2 = start_run(conn, "BBB", trigger="rerun", intent="stage4_only", parent_run_id=r1)
        b = record_stage_result(
            conn,
            ticker="BBB",
            stage=4,
            version_id="v002",
            process_outcome="PROCEED",
            artifact_json_path="companies/BBB/Thesis/stage4_versions/stage4_v002.json",
            run_id=r2,
            is_current=True,
            root=reg_root,
        )
        conn.commit()
        rows = conn.execute(
            "SELECT version_id, is_current, process_outcome, superseded_by_stage_result_id "
            "FROM stage_results WHERE ticker='BBB' AND stage=4 ORDER BY version_id"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0]["version_id"] == "v001"
        assert rows[0]["is_current"] == 0
        assert rows[0]["process_outcome"] == "CONDITIONAL"
        assert rows[0]["superseded_by_stage_result_id"] == b["stage_result_id"]
        assert rows[1]["is_current"] == 1
        assert rows[1]["process_outcome"] == "PROCEED"
        assert a["stage_result_id"] != b["stage_result_id"]
        # only one current
        ncur = conn.execute(
            "SELECT COUNT(*) FROM stage_results WHERE ticker='BBB' AND stage=4 AND is_current=1"
        ).fetchone()[0]
        assert ncur == 1
    finally:
        conn.close()


# --- idempotency ---


def test_idempotent_insert_same_ticker_stage_version(reg_root):
    _write_stage_artifact(reg_root, "CCC", 6, "v001", process_outcome="PROCEED")
    conn = open_registry(reg_root)
    try:
        kwargs = dict(
            ticker="CCC",
            stage=6,
            version_id="v001",
            process_outcome="PROCEED",
            artifact_json_path="companies/CCC/Thesis/stage6_versions/stage6_v001.json",
            is_current=True,
            root=reg_root,
        )
        a = record_stage_result(conn, **kwargs)
        # Attempt with different outcome — must NOT overwrite
        b = record_stage_result(
            conn,
            ticker="CCC",
            stage=6,
            version_id="v001",
            process_outcome="STOP_NO_THESIS",  # would-be overwrite
            artifact_json_path="companies/CCC/Thesis/stage6_versions/stage6_v001.json",
            is_current=True,
            root=reg_root,
        )
        conn.commit()
        assert a["_idempotent"] is False
        assert b["_idempotent"] is True
        assert b["process_outcome"] == "PROCEED"
        n = conn.execute("SELECT COUNT(*) FROM stage_results WHERE ticker='CCC'").fetchone()[0]
        assert n == 1
    finally:
        conn.close()


# --- failed runs ---


def test_failed_run_status(reg_root):
    conn = open_registry(reg_root)
    try:
        rid = start_run(conn, "DDD", intent="stage9_only")
        fail_run(conn, rid, notes="boom")
        conn.commit()
        row = conn.execute(
            "SELECT status, notes, ended_at FROM analysis_runs WHERE run_id=?", (rid,)
        ).fetchone()
        assert row["status"] == "failed"
        assert row["ended_at"]
        assert row["notes"] == "boom"
    finally:
        conn.close()


# --- missing artifacts ---


def test_missing_artifact_require_raises(reg_root):
    conn = open_registry(reg_root)
    try:
        with pytest.raises(RegistryError, match="missing artifact"):
            record_stage_result(
                conn,
                ticker="EEE",
                stage=1,
                version_id="v001",
                process_outcome="PROCEED",
                artifact_json_path="companies/EEE/Thesis/stage1_versions/stage1_v001.json",
                require_artifact=True,
                root=reg_root,
            )
        with pytest.raises(RegistryError, match="artifact missing"):
            record_stage_after_artifact(
                conn,
                ticker="EEE",
                stage=1,
                version_id="v001",
                process_outcome="PROCEED",
                artifact_json_abs=reg_root / "companies/EEE/Thesis/nope.json",
                root=reg_root,
            )
    finally:
        conn.close()


# --- rollback ---


def test_transaction_rollback_and_backup_restore(reg_root):
    _write_stage_artifact(reg_root, "FFF", 2, "v001")
    conn = open_registry(reg_root)
    try:
        record_stage_result(
            conn,
            ticker="FFF",
            stage=2,
            version_id="v001",
            process_outcome="PROCEED",
            artifact_json_path="companies/FFF/Thesis/stage2_versions/stage2_v001.json",
            is_current=True,
            root=reg_root,
        )
        conn.commit()
    finally:
        conn.close()

    bak = backup_registry(reg_root)
    assert bak.is_file()

    conn = open_registry(reg_root)
    try:
        record_stage_result(
            conn,
            ticker="FFF",
            stage=2,
            version_id="v002",
            process_outcome="CONDITIONAL",
            artifact_json_path="companies/FFF/Thesis/stage2_versions/stage2_v001.json",
            is_current=True,
            root=reg_root,
        )
        # simulate failure → rollback
        conn.rollback()
        n = conn.execute("SELECT COUNT(*) FROM stage_results WHERE ticker='FFF'").fetchone()[0]
        assert n == 1
    finally:
        conn.close()

    # Add a committed row then restore backup (rollback aid)
    conn = open_registry(reg_root)
    try:
        record_stage_result(
            conn,
            ticker="FFF",
            stage=2,
            version_id="v099",
            process_outcome="REVIEW_REQUIRED",
            artifact_json_path="companies/FFF/Thesis/stage2_versions/stage2_v001.json",
            is_current=True,
            root=reg_root,
        )
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM stage_results WHERE ticker='FFF'").fetchone()[0] == 2
    finally:
        conn.close()

    restore_registry_from_backup(bak, reg_root)
    conn = open_registry(reg_root)
    try:
        n = conn.execute("SELECT COUNT(*) FROM stage_results WHERE ticker='FFF'").fetchone()[0]
        assert n == 1
        assert (
            conn.execute(
                "SELECT version_id FROM stage_results WHERE ticker='FFF'"
            ).fetchone()[0]
            == "v001"
        )
    finally:
        conn.close()


# --- stale ---


def test_stale_flag_and_view(reg_root):
    conn = open_registry(reg_root)
    try:
        ensure_company(conn, "GGG", gate0_class="operating")
        mark_company_stale(conn, "GGG", stale=True, reason="coverage_change")
        conn.commit()
        rows = conn.execute("SELECT * FROM v_stale_analysis").fetchall()
        assert any(r["ticker"] == "GGG" and r["stale_flag"] == 1 for r in rows)
        mark_company_stale(conn, "GGG", stale=False)
        conn.commit()
        rows2 = conn.execute(
            "SELECT * FROM v_stale_analysis WHERE ticker='GGG'"
        ).fetchall()
        assert rows2 == []
    finally:
        conn.close()


# --- views / export ---


def test_views_and_csv_export(reg_root):
    _write_stage_artifact(reg_root, "HHH", 8, "v001", process_outcome="REVIEW_REQUIRED")
    conn = open_registry(reg_root)
    try:
        record_stage_result(
            conn,
            ticker="HHH",
            stage=8,
            version_id="v001",
            process_outcome="REVIEW_REQUIRED",
            artifact_json_path="companies/HHH/Thesis/stage8_versions/stage8_v001.json",
            is_current=True,
            root=reg_root,
        )
        record_final_fa_result(
            conn,
            ticker="HHH",
            version_id="v001",
            final_state="ORANGE",
            technical_eligible=False,
            artifact_json_path=None,
            is_current=True,
            root=reg_root,
        )
        conn.commit()
        matrix = conn.execute(
            "SELECT ticker, s8_process_outcome, final_fa_final_state FROM v_company_stage_matrix WHERE ticker='HHH'"
        ).fetchone()
        assert matrix["s8_process_outcome"] == "REVIEW_REQUIRED"
        assert matrix["final_fa_final_state"] == "ORANGE"
        hist = conn.execute(
            "SELECT COUNT(*) FROM v_company_history WHERE ticker='HHH'"
        ).fetchone()[0]
        assert hist >= 2
    finally:
        conn.close()

    out = export_company_stage_matrix(reg_root, write_md=True)
    assert out["csv"].is_file()
    assert out["md"].is_file()
    text = out["csv"].read_text(encoding="utf-8")
    assert "HHH" in text
    assert "REVIEW_REQUIRED" in text
    rows = fetch_company_stage_matrix(reg_root)
    assert any(r["ticker"] == "HHH" for r in rows)


# --- backup ---


def test_backup_write_once(reg_root):
    open_registry(reg_root).close()
    p1 = backup_registry(reg_root)
    p2 = backup_registry(reg_root)
    assert p1.is_file() and p2.is_file()
    assert p1.name.startswith("fa_run_registry_")
    assert p1.suffix == ".sqlite"


# --- backfill ---


def test_backfill_idempotent(reg_root):
    _write_stage_artifact(reg_root, "III", 7, "v001", process_outcome="CONDITIONAL")
    _write_stage_artifact(reg_root, "III", 7, "v002", process_outcome="PROCEED", as_current=True)
    # v001 should not be current on disk after v002 write — rewrite CURRENT to v002 only
    # (_write_stage_artifact already set CURRENT to last call)
    stats1 = backfill_registry(reg_root)
    assert stats1["stage_rows_inserted"] >= 2
    assert "III" in stats1["tickers"]
    stats2 = backfill_registry(reg_root)
    assert stats2["stage_rows_inserted"] == 0
    assert stats2["stage_rows_idempotent"] >= 2

    conn = open_registry(reg_root)
    try:
        cur = conn.execute(
            """
            SELECT version_id, process_outcome, is_current FROM stage_results
            WHERE ticker='III' AND stage=7 ORDER BY version_id
            """
        ).fetchall()
        assert len(cur) == 2
        assert cur[1]["is_current"] == 1
        assert cur[1]["process_outcome"] == "PROCEED"
        assert cur[0]["is_current"] == 0
        co = conn.execute(
            "SELECT entity_name, gate0_class FROM companies WHERE ticker='III'"
        ).fetchone()
        assert co["entity_name"] == "III Corp"
        assert co["gate0_class"] == "operating"
    finally:
        conn.close()


# --- drift ---


def test_drift_detection_file_wins_report(reg_root):
    _write_stage_artifact(reg_root, "JJJ", 5, "v001", process_outcome="PROCEED")
    backfill_registry(reg_root)

    # Mutate registry CURRENT outcome? Forbidden — instead insert bogus registry-only row
    # Simulate mismatch: change disk CURRENT outcome without new version key change
    # (disk diverges from registered hash/outcome for same version — report hash/outcome mismatch)
    thesis = reg_root / "companies/JJJ/Thesis"
    cur = json.loads((thesis / "stage5_CURRENT.json").read_text())
    cur["process_outcome"] = "REVIEW_REQUIRED"
    (thesis / "stage5_CURRENT.json").write_text(json.dumps(cur), encoding="utf-8")
    (thesis / "stage5_versions/stage5_v001.json").write_text(json.dumps(cur), encoding="utf-8")

    report = detect_drift(reg_root)
    assert report["mismatches"] or report["hash_mismatches"]
    # outcome mismatch should appear (same version_id, different process_outcome)
    assert any(
        m.get("kind") == "stage" and m.get("ticker") == "JJJ" for m in report["mismatches"]
    ) or any(h.get("ticker") == "JJJ" for h in report["hash_mismatches"])

    # Missing in registry: add new disk version not backfilled
    _write_stage_artifact(reg_root, "JJJ", 5, "v002", process_outcome="CONDITIONAL")
    report2 = detect_drift(reg_root)
    assert any(
        m.get("version_id") == "v002" and m.get("ticker") == "JJJ"
        for m in report2["missing_in_registry"]
    )

    repaired = repair_drift_from_disk(reg_root)
    assert repaired["backfill"]["stage_rows_inserted"] >= 1
    report3 = detect_drift(reg_root)
    # After repair, v002 should be in registry; outcome mismatch for v001 remains
    # because we never silently overwrite historical outcome scalars
    assert not any(
        m.get("version_id") == "v002" for m in report3["missing_in_registry"]
    )


def test_final_fa_table_separate_and_no_stage_logic_import():
    """Final FA states live in final_fa_results; registry package does not import stage calc."""
    import fa.registry as reg

    src = Path(reg.__file__).read_text(encoding="utf-8")
    # Thin package — no stage1-9 analytical imports at package root
    assert "stage8.calc" not in src
    assert "final_fa_synth" not in src


def test_post_artifact_api(reg_root):
    jp = _write_stage_artifact(reg_root, "KKK", 9, "v001", process_outcome="CONDITIONAL")
    conn = open_registry(reg_root)
    try:
        row = record_stage_after_artifact(
            conn,
            ticker="KKK",
            stage=9,
            version_id="v001",
            process_outcome="CONDITIONAL",
            artifact_json_abs=jp,
            artifact_md_abs=jp.with_suffix(".md"),
            terminates_later_stages=False,
            root=reg_root,
        )
        conn.commit()
        assert row["is_current"] == 1
        assert row["artifact_json_path"].endswith("stage9_v001.json")
        assert row["process_outcome"] == "CONDITIONAL"
    finally:
        conn.close()
