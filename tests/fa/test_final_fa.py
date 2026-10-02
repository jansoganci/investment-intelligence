"""Final FA Synthesis tests — Plan §0 locked rules (no UAT)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fa.final_fa import (
    evaluate_final_fa,
    load_final_fa_current,
    run_final_fa,
    save_final_fa_report,
)
from fa.final_fa.evaluate import extract_carries
from fa.registry import open_registry
from fa.registry import paths as reg_paths
from fa import storage as fa_storage


# ---------------------------------------------------------------------------
# Fixtures helpers — synthetic stage CURRENT docs (do not invent outcomes
# beyond what evaluate consumes)
# ---------------------------------------------------------------------------

def _base_stage(ticker: str, n: int, outcome: str = "PROCEED", **extra) -> dict:
    doc = {
        "ticker": ticker,
        "date": "2026-10-01T00:00:00Z",
        "process_outcome": outcome,
        "version_id": "v001",
        "why_bullets": [f"S{n} why"],
        "what_is_strong": [f"S{n} strong"],
        "what_can_break": [],
        "monitors": [f"S{n} monitor"],
        "carry_forward_concerns": [],
    }
    doc.update(extra)
    return doc


def _full_stages(
    ticker: str = "SYN",
    *,
    skip: set[int] | None = None,
    outcomes: dict[int, str] | None = None,
    extras: dict[int, dict] | None = None,
) -> dict[int, dict | None]:
    skip = skip or set()
    outcomes = outcomes or {}
    extras = extras or {}
    stages: dict[int, dict | None] = {}
    for n in range(1, 10):
        if n in skip:
            stages[n] = None
            continue
        extra = dict(extras.get(n) or {})
        if n == 1:
            extra.setdefault(
                "thesis",
                {
                    "one_sentence": "Quality OpCo with durable advantage",
                    "economic_engine": "recurring revenue",
                    "advantage_type": "network",
                    "capital_destination": "reinvest + distribute",
                    "kill_shot_primary": "moat collapse",
                },
            )
        if n == 6:
            extra.setdefault("stage7_handoff_flags", [])
        if n == 8:
            extra.setdefault("s7_h8_carries", [])
            extra.setdefault("s8_h9_carries", [])
        if n == 9:
            extra.setdefault("s9_hfa_carries", [])
            extra.setdefault("thesis_breakers", [])
            extra.setdefault("s1_8_conflicts", [])
        stages[n] = _base_stage(ticker, n, outcomes.get(n, "PROCEED"), **extra)
    return stages


def _write_stages(root: Path, ticker: str, stages: dict[int, dict | None]) -> None:
    fa_storage.ensure_company_layout(ticker, root)
    thesis = root / "companies" / ticker / "Thesis"
    thesis.mkdir(parents=True, exist_ok=True)
    for n, doc in stages.items():
        if doc is None:
            continue
        path = thesis / f"stage{n}_CURRENT.json"
        path.write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture()
def reg_root(fa_root, monkeypatch):
    monkeypatch.setattr(reg_paths.config, "FA_ROOT", fa_root)
    return fa_root


# ---------------------------------------------------------------------------
# Completeness / outside-color
# ---------------------------------------------------------------------------

def test_incomplete_when_required_stage_missing():
    stages = _full_stages(skip={9})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "INCOMPLETE"
    assert syn.technical_eligible is False
    assert syn.stage_outcomes["s9"] == "missing"
    assert any("S9" in u for u in syn.unresolved)


def test_incomplete_when_s2_missing():
    stages = _full_stages(skip={2})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "INCOMPLETE"
    assert syn.technical_eligible is False


def test_incomplete_when_s1_missing():
    stages = _full_stages(skip={1})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "INCOMPLETE"


def test_too_hard_propagation_from_required_stage():
    stages = _full_stages(outcomes={6: "TOO_HARD"})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "TOO_HARD"
    assert syn.technical_eligible is False
    # TOO_HARD ≠ RED
    assert syn.final_state != "RED"


def test_stage1_stop_no_thesis_maps_outside():
    stages = _full_stages(outcomes={1: "STOP_NO_THESIS"})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "STOP_NO_THESIS"
    assert syn.technical_eligible is False


def test_stage1_too_hard_maps_outside():
    stages = _full_stages(outcomes={1: "TOO_HARD"})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "TOO_HARD"


# ---------------------------------------------------------------------------
# Soft-missing S4/S5/S7 → ORANGE max / no GREEN
# ---------------------------------------------------------------------------

def test_soft_missing_s4_s5_s7_orange_max_no_green():
    stages = _full_stages(skip={4, 5, 7})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "ORANGE"
    assert syn.technical_eligible is False
    assert set(syn.soft_missing_chips) == {"S4_MISSING", "S5_MISSING", "S7_MISSING"}
    assert syn.orange_ceiling is True
    assert syn.final_state != "GREEN"
    # soft-missing alone ≠ RED / REVIEW / INCOMPLETE
    assert syn.final_state not in {"RED", "REVIEW_REQUIRED", "INCOMPLETE"}


def test_soft_missing_s4_only_caps_orange():
    stages = _full_stages(skip={4})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "ORANGE"
    assert syn.technical_eligible is False
    assert "S4_MISSING" in syn.soft_missing_chips


# ---------------------------------------------------------------------------
# GREEN path
# ---------------------------------------------------------------------------

def test_green_path_all_required_present_no_hard_blockers():
    stages = _full_stages()  # all PROCEED, no soft carries, no breaker
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "GREEN"
    assert syn.technical_eligible is True
    assert syn.acknowledgements["green_ne_buy"] is True
    assert syn.acknowledgements["no_buy_sell"] is True
    assert syn.acknowledgements["no_weights"] is True
    assert not syn.soft_missing_chips


def test_green_allows_s1_soft_carries_without_orange_cap():
    """S8_H9 alone is soft S1 — may remain documented without forcing ORANGE."""
    stages = _full_stages(
        extras={8: {"s8_h9_carries": ["S8_H9_EXPECTATIONS_DEMANDING"]}}
    )
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "GREEN"
    assert syn.technical_eligible is True
    assert "S8_H9_EXPECTATIONS_DEMANDING" in syn.carries_consumed["s8_h9"]
    assert any("S8_H9_EXPECTATIONS_DEMANDING" in c.text for c in syn.challenges)


def test_material_soft_s6_dual_view_forces_orange():
    stages = _full_stages(
        extras={6: {"stage7_handoff_flags": ["S6_H7_DUAL_VIEW_CONFLICT"]}}
    )
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "ORANGE"
    assert syn.technical_eligible is False


# ---------------------------------------------------------------------------
# FACT breaker → REVIEW_REQUIRED
# ---------------------------------------------------------------------------

def test_fact_breaker_active_review_required():
    stages = _full_stages(
        extras={
            9: {
                "s9_hfa_carries": ["S9_HFA_THESIS_BREAKER_ACTIVE", "S9_HFA_REGULATORY_MATERIAL"],
                "thesis_breakers": [
                    {
                        "breaker_id": "TB_REG",
                        "mechanism": "Adverse regulatory action",
                        "active_fact": True,
                        "evidence_label": "FACT",
                    }
                ],
                "carry_forward_concerns": [
                    "Final-FA carry: S9_HFA_THESIS_BREAKER_ACTIVE",
                    "Active FACT breaker TB_REG: Adverse regulatory action",
                ],
            }
        }
    )
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "REVIEW_REQUIRED"
    assert syn.technical_eligible is False
    assert syn.final_state != "RED"  # not auto-RED
    assert any(h.id == "HR_FACT_BREAKER" and h.blocks_color for h in syn.human_review_queue)
    assert "S9_HFA_THESIS_BREAKER_ACTIVE" in syn.carries_consumed["s9_hfa"]


def test_fact_fact_conflict_review():
    stages = _full_stages(
        extras={
            9: {
                "s1_8_conflicts": [
                    "FACT vs FACT on thesis-critical moat claim between S5 and S9"
                ],
            }
        }
    )
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "REVIEW_REQUIRED"
    assert any(c.human_required for c in syn.conflicts)


# ---------------------------------------------------------------------------
# Artifact + registry hook
# ---------------------------------------------------------------------------

def test_artifact_and_registry_hook_write(reg_root):
    stages = _full_stages("ART")
    _write_stages(reg_root, "ART", stages)
    out = run_final_fa("ART", root=reg_root, persist=True)
    assert out["ok"] is True
    assert out["final_state"] == "GREEN"
    cur = load_final_fa_current("ART", reg_root)
    assert cur is not None
    assert cur["final_state"] == "GREEN"
    assert cur["technical_eligible"] is True
    md = reg_root / "companies" / "ART" / "Thesis" / "final_fa_CURRENT.md"
    assert md.is_file()
    assert "Final FA Synthesis" in md.read_text(encoding="utf-8")
    vdir = reg_root / "companies" / "ART" / "Thesis" / "final_fa_versions"
    assert list(vdir.glob("final_fa_v*.json"))

    conn = open_registry(reg_root)
    try:
        row = conn.execute(
            "SELECT * FROM final_fa_results WHERE ticker=? AND is_current=1",
            ("ART",),
        ).fetchone()
        assert row is not None
        assert row["final_state"] == "GREEN"
        assert row["technical_eligible"] == 1
    finally:
        conn.close()


def test_run_final_fa_incomplete_persists(reg_root):
    stages = _full_stages("INC", skip={8})
    _write_stages(reg_root, "INC", stages)
    out = run_final_fa("INC", root=reg_root)
    assert out["final_state"] == "INCOMPLETE"
    cur = load_final_fa_current("INC", reg_root)
    assert cur["final_state"] == "INCOMPLETE"
    assert cur["technical_eligible"] is False


# ---------------------------------------------------------------------------
# No Stage 1–9 module mutation
# ---------------------------------------------------------------------------

def test_no_stage_module_mutation_on_disk(reg_root):
    stages = _full_stages("PURE")
    _write_stages(reg_root, "PURE", stages)
    before = {}
    for n in range(1, 10):
        p = reg_root / "companies" / "PURE" / "Thesis" / f"stage{n}_CURRENT.json"
        before[n] = p.read_text(encoding="utf-8")
    run_final_fa("PURE", root=reg_root)
    for n in range(1, 10):
        p = reg_root / "companies" / "PURE" / "Thesis" / f"stage{n}_CURRENT.json"
        assert p.read_text(encoding="utf-8") == before[n]


def test_stage_outcome_readout_always_present():
    stages = _full_stages(skip={4, 9})
    syn = evaluate_final_fa("SYN", stages)
    assert set(syn.stage_outcomes.keys()) == {f"s{i}" for i in range(1, 10)}
    assert syn.stage_outcomes["s4"] == "missing"
    assert syn.stage_outcomes["s9"] == "missing"


def test_extract_carries_from_artifacts():
    stages = _full_stages(
        extras={
            6: {"stage7_handoff_flags": ["S6_H7_ACQ_RETURN_OPACITY"]},
            8: {
                "s7_h8_carries": ["S7_H8_DILUTION_MATERIAL"],
                "s8_h9_carries": ["S8_H9_CYCLE_SENSITIVE_VALUATION"],
            },
            9: {"s9_hfa_carries": ["S9_HFA_GEO_MATERIAL"]},
        }
    )
    c = extract_carries(stages)
    assert "S6_H7_ACQ_RETURN_OPACITY" in c["s6_h7"]
    assert "S7_H8_DILUTION_MATERIAL" in c["s7_h8"]
    assert "S8_H9_CYCLE_SENSITIVE_VALUATION" in c["s8_h9"]
    assert "S9_HFA_GEO_MATERIAL" in c["s9_hfa"]


def test_orange_never_technical_eligible():
    stages = _full_stages(skip={5})
    syn = evaluate_final_fa("SYN", stages)
    assert syn.final_state == "ORANGE"
    assert syn.technical_eligible is False


def test_stage_rr_alone_not_auto_final_review():
    """Stage process REVIEW_REQUIRED alone must not auto Final FA REVIEW."""
    stages = _full_stages(outcomes={6: "REVIEW_REQUIRED", 8: "REVIEW_REQUIRED"})
    syn = evaluate_final_fa("SYN", stages)
    # Without hard criteria → inside color (ORANGE lean from soft challenges possible)
    assert syn.final_state in {"GREEN", "ORANGE"}
    assert syn.final_state != "REVIEW_REQUIRED"
