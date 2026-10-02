"""Stage 1 deterministic evaluation — Gates 0–2 process outcomes."""
from __future__ import annotations

from fa.stage1.evaluate import evaluate_stage1
from fa.stage1.pipeline import happy_path_payload_synth_opco


def test_happy_path_proceed():
    report = evaluate_stage1("SYNTH_OPCO", happy_path_payload_synth_opco())
    assert report.process_outcome == "PROCEED"
    assert report.block_stage2 is False
    assert report.enough_to_proceed == "Yes"
    assert report.gate0_class == "operating"


def test_missing_g1_m1_m4_too_hard():
    payload = happy_path_payload_synth_opco()
    for qid in ("G1-M1", "G1-M2", "G1-M3", "G1-M4"):
        payload["answers"][qid] = ""
    report = evaluate_stage1("SYNTH_OPCO", payload)
    assert report.process_outcome == "TOO_HARD"
    assert report.block_stage2 is True
    assert "G1-M1" in report.enough_why or "hand-wav" in report.enough_why.lower()


def test_no_falsifiers_g1_m7_too_hard():
    payload = happy_path_payload_synth_opco()
    payload["answers"]["G1-M7"] = ""
    report = evaluate_stage1("SYNTH_OPCO", payload)
    assert report.process_outcome == "TOO_HARD"
    assert "G1-M7" in report.enough_why or "falsifier" in report.enough_why.lower()


def test_ban_list_one_liner_review_required():
    payload = happy_path_payload_synth_opco()
    payload["thesis"]["one_sentence"] = "I want to own this because good margins and high ROIC."
    report = evaluate_stage1("SYNTH_OPCO", payload)
    assert report.process_outcome == "REVIEW_REQUIRED"
    assert report.ban_list_hits
    assert "good margins" in report.ban_list_hits or "high roic" in report.ban_list_hits


def test_fi_gate0_too_hard_oos():
    payload = happy_path_payload_synth_opco()
    payload["gate0_class"] = "financial_institution"
    report = evaluate_stage1("SYNTH_BANK", payload)
    assert report.process_outcome == "TOO_HARD"
    assert report.gate0_class == "financial_institution"
    assert "OOS" in report.enough_why or "out of scope" in report.enough_why.lower()


def test_missing_g2_m2_stop_no_thesis():
    payload = happy_path_payload_synth_opco()
    payload["answers"]["G2-M2"] = ""
    payload["thesis"]["advantage_type"] = ""
    report = evaluate_stage1("SYNTH_OPCO", payload)
    assert report.process_outcome == "STOP_NO_THESIS"
