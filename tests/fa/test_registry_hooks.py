"""Automatic Registry write hooks after Stage / Final FA artifact saves (Plan §0.F)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fa.final_fa.storage import save_final_fa_report
from fa.models import Stage2Report, Stage3Report
from fa.registry import (
    RegistryHookError,
    hook_final_fa_after_artifact,
    hook_stage_after_save,
    open_registry,
)
from fa.registry import paths as reg_paths
from fa.stage1.evaluate import evaluate_stage1
from fa.stage1.pipeline import happy_path_payload_synth_opco
from fa.stage1.report import render_stage1_markdown
from fa.stage1.storage import load_stage1_current, save_stage1_report, stage1_current_path
from fa.stage2.storage import load_stage2_current, save_stage2_report, stage2_current_path
from fa.stage3.storage import save_stage3_report, stage3_current_path


@pytest.fixture()
def reg_root(fa_root, monkeypatch):
    monkeypatch.setattr(reg_paths.config, "FA_ROOT", fa_root)
    return fa_root


def _minimal_stage2(ticker: str = "HOOK2", *, block_next: bool = False) -> Stage2Report:
    return Stage2Report(
        ticker=ticker,
        date="2026-10-01T00:00:00Z",
        periods_used=[],
        sources=["test"],
        process_outcome="PROCEED",
        narrative_verdict="ok",
        survival_thesis="survives",
        evidence_bullets={},
        falsifiers=[],
        monitors=[],
        gaps=[],
        enough_to_proceed="Yes",
        enough_why="test",
        block_next=block_next,
        block_reasons=[],
    )


def _minimal_stage3(ticker: str = "HOOK3") -> Stage3Report:
    return Stage3Report(
        ticker=ticker,
        date="2026-10-01T00:00:00Z",
        periods_used=[],
        sources=["test"],
        process_outcome="PROCEED",
        why_bullets=["why"],
        carry_forward_concerns=[],
        cash_conversion_bullets=[],
        working_capital_bullets=[],
        capex_bullets=[],
        cash_quality_warnings=[],
        what_is_strong=[],
        what_can_break=[],
        monitors=[],
        missing_ambiguous=[],
        terminates_later_stages=False,
    )


def test_automatic_stage1_write_registers_current(reg_root):
    report = evaluate_stage1("SYNTH_OPCO", happy_path_payload_synth_opco())
    assert report.process_outcome == "PROCEED"
    out = save_stage1_report(
        "SYNTH_OPCO",
        report,
        root=reg_root,
        markdown=render_stage1_markdown(report),
    )
    assert out["version_id"] == "v001"
    assert stage1_current_path("SYNTH_OPCO", reg_root).is_file()

    conn = open_registry(reg_root)
    try:
        row = conn.execute(
            """
            SELECT * FROM stage_results
            WHERE ticker = ? AND stage = 1 AND is_current = 1
            """,
            ("SYNTH_OPCO",),
        ).fetchone()
        assert row is not None
        assert row["version_id"] == "v001"
        assert row["process_outcome"] == "PROCEED"
        assert row["artifact_json_path"].endswith("stage1_v001.json")
    finally:
        conn.close()


def test_automatic_stage2_and_stage3_write(reg_root):
    r2 = _minimal_stage2("AAA")
    out2 = save_stage2_report("AAA", r2, root=reg_root, markdown="# s2\n")
    assert out2["version_id"] == "v001"
    assert stage2_current_path("AAA", reg_root).is_file()
    assert (reg_root / "companies" / "AAA" / "Generated" / "stage2_report.json").is_file()

    r3 = _minimal_stage3("AAA")
    out3 = save_stage3_report("AAA", r3, root=reg_root, markdown="# s3\n")
    assert out3 == {"version_id": "v001", "path": str(stage3_current_path("AAA", reg_root))}

    conn = open_registry(reg_root)
    try:
        s2 = conn.execute(
            "SELECT * FROM stage_results WHERE ticker=? AND stage=2 AND is_current=1",
            ("AAA",),
        ).fetchone()
        s3 = conn.execute(
            "SELECT * FROM stage_results WHERE ticker=? AND stage=3 AND is_current=1",
            ("AAA",),
        ).fetchone()
        assert s2["version_id"] == "v001"
        assert s2["terminates_later_stages"] == 0  # block_next False
        assert s3["process_outcome"] == "PROCEED"
    finally:
        conn.close()


def test_rerun_demotes_prior_current(reg_root):
    r = _minimal_stage2("BBB")
    save_stage2_report("BBB", r, root=reg_root, markdown="#1\n")
    r2 = _minimal_stage2("BBB", block_next=True)
    # Force different outcome for second version
    r2.process_outcome = "REVIEW_REQUIRED"
    save_stage2_report("BBB", r2, root=reg_root, markdown="#2\n")

    conn = open_registry(reg_root)
    try:
        rows = conn.execute(
            """
            SELECT version_id, is_current, process_outcome, terminates_later_stages
            FROM stage_results WHERE ticker=? AND stage=2 ORDER BY version_id
            """,
            ("BBB",),
        ).fetchall()
        assert len(rows) == 2
        assert rows[0]["version_id"] == "v001"
        assert rows[0]["is_current"] == 0
        assert rows[1]["version_id"] == "v002"
        assert rows[1]["is_current"] == 1
        assert rows[1]["terminates_later_stages"] == 1
        assert rows[1]["process_outcome"] == "REVIEW_REQUIRED"
        cur = conn.execute(
            "SELECT COUNT(*) AS n FROM stage_results WHERE ticker=? AND stage=2 AND is_current=1",
            ("BBB",),
        ).fetchone()["n"]
        assert cur == 1
    finally:
        conn.close()


def test_registry_failure_leaves_artifact_intact(reg_root, monkeypatch):
    from fa.registry import hooks as hooks_mod

    def boom(*_a, **_k):
        raise RuntimeError("simulated registry failure")

    monkeypatch.setattr(hooks_mod, "record_stage_after_artifact", boom)

    r = _minimal_stage2("FAIL")
    out = save_stage2_report("FAIL", r, root=reg_root, markdown="# fail\n")
    assert out["version_id"] == "v001"
    cur = stage2_current_path("FAIL", reg_root)
    assert cur.is_file()
    doc = json.loads(cur.read_text(encoding="utf-8"))
    assert doc["process_outcome"] == "PROCEED"
    assert doc["version_id"] == "v001"

    # Registry should have no CURRENT for this ticker/stage (transaction rolled back)
    conn = open_registry(reg_root)
    try:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM stage_results WHERE ticker=? AND stage=2",
            ("FAIL",),
        ).fetchone()["n"]
        assert n == 0
    finally:
        conn.close()


def test_registry_failure_raise_on_error(reg_root, monkeypatch):
    from fa.registry import hooks as hooks_mod

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(hooks_mod, "record_stage_after_artifact", boom)
    r = _minimal_stage2("RAISE")
    with pytest.raises(RegistryHookError):
        save_stage2_report(
            "RAISE",
            r,
            root=reg_root,
            markdown="#x\n",
            raise_on_registry_error=True,
        )
    assert stage2_current_path("RAISE", reg_root).is_file()


def test_duplicate_hook_idempotent(reg_root):
    r = _minimal_stage3("IDEM")
    out = save_stage3_report("IDEM", r, root=reg_root, markdown="#i\n")
    version_json = (
        reg_root / "companies" / "IDEM" / "Thesis" / "stage3_versions" / "stage3_v001.json"
    )
    h1 = hook_stage_after_save(
        ticker="IDEM",
        stage=3,
        version_id=out["version_id"],
        artifact_json_abs=version_json,
        root=reg_root,
        doc=json.loads(version_json.read_text(encoding="utf-8")),
        raise_on_error=True,
    )
    assert h1["ok"] is True
    assert h1["stage_result"]["_idempotent"] is True

    conn = open_registry(reg_root)
    try:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM stage_results WHERE ticker=? AND stage=3",
            ("IDEM",),
        ).fetchone()["n"]
        assert n == 1
        cur = conn.execute(
            "SELECT COUNT(*) AS n FROM stage_results WHERE ticker=? AND stage=3 AND is_current=1",
            ("IDEM",),
        ).fetchone()["n"]
        assert cur == 1
    finally:
        conn.close()


def test_kill_switch_and_skip_registry(reg_root, monkeypatch):
    monkeypatch.setenv("FA_REGISTRY_HOOKS", "0")
    r = _minimal_stage2("OFF")
    save_stage2_report("OFF", r, root=reg_root, markdown="#off\n")
    assert stage2_current_path("OFF", reg_root).is_file()
    conn = open_registry(reg_root)
    try:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM stage_results WHERE ticker=?",
            ("OFF",),
        ).fetchone()["n"]
        assert n == 0
    finally:
        conn.close()

    monkeypatch.setenv("FA_REGISTRY_HOOKS", "1")
    save_stage2_report("SKIP", r, root=reg_root, markdown="#skip\n", skip_registry=True)
    conn = open_registry(reg_root)
    try:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM stage_results WHERE ticker=?",
            ("SKIP",),
        ).fetchone()["n"]
        assert n == 0
    finally:
        conn.close()


def test_uat_root_sets_pending_status(tmp_path, monkeypatch):
    """When FA root path contains a 'uat' segment, uat_status defaults to pending."""
    uat_root = tmp_path / "uat" / "fa_data"
    uat_root.mkdir(parents=True)
    (uat_root / "companies").mkdir()
    monkeypatch.setattr(reg_paths.config, "FA_ROOT", uat_root)
    import fa.config as cfg

    monkeypatch.setattr(cfg, "FA_ROOT", uat_root)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", uat_root / "companies")

    r = _minimal_stage2("UAT1")
    save_stage2_report("UAT1", r, root=uat_root, markdown="#uat\n")
    conn = open_registry(uat_root)
    try:
        row = conn.execute(
            "SELECT uat_status FROM stage_results WHERE ticker=? AND stage=2",
            ("UAT1",),
        ).fetchone()
        assert row["uat_status"] == "pending"
    finally:
        conn.close()

    # Explicit override
    save_stage2_report(
        "UAT1",
        r,
        root=uat_root,
        markdown="#uat2\n",
        uat_status="accepted",
    )
    conn = open_registry(uat_root)
    try:
        row = conn.execute(
            """
            SELECT uat_status FROM stage_results
            WHERE ticker=? AND stage=2 AND is_current=1
            """,
            ("UAT1",),
        ).fetchone()
        assert row["uat_status"] == "accepted"
    finally:
        conn.close()


def test_analytical_fields_unchanged_by_hook(reg_root):
    r = _minimal_stage2("PURE")
    before = r.to_dict()
    save_stage2_report("PURE", r, root=reg_root, markdown="#p\n")
    after = load_stage2_current("PURE", reg_root)
    assert after is not None
    # Storage adds version_id / saved_at only; analytical fields match
    for k, v in before.items():
        assert after[k] == v
    assert "version_id" in after
    assert "saved_at" in after
    # Return shape stable
    out = save_stage2_report("PURE", r, root=reg_root, markdown="#p2\n")
    assert set(out.keys()) == {"version_id", "path"}


def test_final_fa_hook_with_handwritten_artifact(reg_root):
    thesis = reg_root / "companies" / "FFF" / "Thesis"
    vdir = thesis / "final_fa_versions"
    vdir.mkdir(parents=True, exist_ok=True)
    doc = {
        "ticker": "FFF",
        "version_id": "v001",
        "final_state": "ORANGE",
        "technical_eligible": False,
        "saved_at": "2026-10-01T12:00:00Z",
    }
    jp = vdir / "final_fa_v001.json"
    jp.write_text(json.dumps(doc), encoding="utf-8")
    (thesis / "final_fa_CURRENT.json").write_text(json.dumps(doc), encoding="utf-8")
    md = thesis / "final_fa_CURRENT.md"
    md.write_text("# final\n", encoding="utf-8")

    res = hook_final_fa_after_artifact(
        ticker="FFF",
        version_id="v001",
        artifact_json_abs=jp,
        artifact_md_abs=md,
        root=reg_root,
        doc=doc,
        raise_on_error=True,
    )
    assert res["ok"] is True
    assert res["final_fa_result"]["final_state"] == "ORANGE"
    assert res["final_fa_result"]["is_current"] == 1

    # Stub storage path also works
    out = save_final_fa_report(
        "FFF",
        {"final_state": "GREEN", "technical_eligible": True},
        root=reg_root,
        markdown="# v2\n",
    )
    assert out["version_id"] == "v002"
    conn = open_registry(reg_root)
    try:
        row = conn.execute(
            "SELECT * FROM final_fa_results WHERE ticker=? AND is_current=1",
            ("FFF",),
        ).fetchone()
        assert row["version_id"] == "v002"
        assert row["final_state"] == "GREEN"
        assert row["technical_eligible"] == 1
        prior = conn.execute(
            "SELECT is_current FROM final_fa_results WHERE ticker=? AND version_id='v001'",
            ("FFF",),
        ).fetchone()
        assert prior["is_current"] == 0
    finally:
        conn.close()


def test_hook_result_structured_on_success_and_skip(reg_root, monkeypatch):
    r = _minimal_stage2("STR")
    save_stage2_report("STR", r, root=reg_root, markdown="#s\n")
    jp = reg_root / "companies" / "STR" / "Thesis" / "stage2_versions" / "stage2_v001.json"
    ok = hook_stage_after_save(
        ticker="STR",
        stage=2,
        version_id="v001",
        artifact_json_abs=jp,
        root=reg_root,
        doc=json.loads(jp.read_text(encoding="utf-8")),
    )
    assert ok["ok"] and ok["stage_result"] is not None and ok["error"] is None

    monkeypatch.setenv("FA_REGISTRY_HOOKS", "0")
    skipped = hook_stage_after_save(
        ticker="STR",
        stage=2,
        version_id="v001",
        artifact_json_abs=jp,
        root=reg_root,
    )
    assert skipped["skipped"] is True and skipped["ok"] is True
