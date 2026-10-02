"""Stage 1 pipeline: FA list refuse + Stage 2 gate on PROCEED."""
from __future__ import annotations

from fa.pipeline import analyze_company
from fa.stage1.evaluate import evaluate_stage1
from fa.stage1.pipeline import happy_path_payload_synth_opco, run_stage1
from fa.stage1.report import render_stage1_markdown
from fa.stage1.storage import load_stage1_current, save_stage1_report


def test_unlisted_ticker_refused_stage1(fa_root, demo_list_path):
    result = run_stage1(
        "NOT_ON_LIST",
        happy_path_payload_synth_opco(),
        root=fa_root,
        fa_list_path=demo_list_path,
    )
    assert result.refused is True
    assert result.ok is False
    assert "not on the Fundamental Analysis List" in (result.refuse_reason or "")


def test_run_stage1_persists_current(fa_root, demo_list_path):
    result = run_stage1(
        "SYNTH_OPCO",
        happy_path_payload_synth_opco(),
        root=fa_root,
        fa_list_path=demo_list_path,
    )
    assert result.ok is True
    assert result.stage1 is not None
    assert result.stage1.process_outcome == "PROCEED"
    doc = load_stage1_current("SYNTH_OPCO", fa_root)
    assert doc is not None
    assert doc["process_outcome"] == "PROCEED"
    assert "Stage 1 — Gates 0–2 — SYNTH_OPCO" in (result.markdown or "")


def test_stage2_blocked_when_stage1_not_proceed(fa_root, demo_list_path):
    # Seed company layout + periods via fixtures, then overwrite Stage 1 as TOO_HARD
    analyze_company(
        "SYNTH_OPCO",
        root=fa_root,
        fa_list_path=demo_list_path,
        use_fixtures=True,
        seed=True,
    )
    bad = evaluate_stage1(
        "SYNTH_OPCO",
        {
            "gate0_class": "operating",
            "answers": {"G1-M1": "", "G1-M2": "", "G1-M3": "", "G1-M4": ""},
            "thesis": {"one_sentence": "placeholder that will not reach thesis checks"},
        },
    )
    assert bad.process_outcome == "TOO_HARD"
    save_stage1_report(
        "SYNTH_OPCO", bad, root=fa_root, markdown=render_stage1_markdown(bad)
    )

    result = analyze_company(
        "SYNTH_OPCO",
        root=fa_root,
        fa_list_path=demo_list_path,
        use_fixtures=True,
        seed=False,  # do not re-seed Stage 1 PROCEED
    )
    assert result.stage2_blocked is True
    assert result.stage2 is None
    assert "PROCEED" in (result.stage2_block_reason or "")
    assert "blocked" in (result.markdown or "").lower()


def test_stage2_allowed_when_stage1_proceed(fa_root, demo_list_path):
    result = analyze_company(
        "SYNTH_OPCO",
        root=fa_root,
        fa_list_path=demo_list_path,
        use_fixtures=True,
        seed=True,
    )
    assert result.stage2_blocked is False
    assert result.stage2 is not None
    assert result.ok is True
    assert "Stage 2 — Balance Sheet — SYNTH_OPCO" in (result.markdown or "")


def test_stage2_blocked_when_stage1_missing(fa_root, demo_list_path):
    # Ensure layout without Stage 1
    from fa import storage

    storage.ensure_company_layout("SYNTH_OPCO", fa_root, entity_name="Synthetic Operating Co")
    result = analyze_company(
        "SYNTH_OPCO",
        root=fa_root,
        fa_list_path=demo_list_path,
        use_fixtures=False,
        seed=False,
    )
    assert result.stage2_blocked is True
    assert result.stage2 is None
    assert "Stage 1 missing" in (result.stage2_block_reason or "")
