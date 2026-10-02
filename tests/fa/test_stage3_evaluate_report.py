"""Stage 3 evaluate / report / FI stop / outcomes / no thresholds / no later-stage kill."""
from __future__ import annotations

from fa.models import Stage3SemanticFinding, Stage3SemanticReview
from fa.stage3.evaluate import evaluate_stage3
from fa.stage3.questions import MUST_QUESTIONS, SHOULD_QUESTIONS, STAGE3_OUTCOMES
from fa.stage3.report import render_stage3_markdown
from fa.stage3.semantic import heuristic_stage3_semantic, load_stage3_semantic_from_fixture


def _healthy_periods():
    return [
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "version_id": "v001",
            "fields": {
                "operating_cash_flow": 600,
                "net_income": 500,
                "capex": 100,
                "depreciation_amortization": 80,
                "sbc_expense": 20,
                "revenue": 2000,
                "receivables": 180,
                "inventory": 120,
                "accounts_payable": 90,
                "deferred_revenue_current": 30,
            },
        },
        {
            "period_key": "FY2025",
            "period_type": "FY",
            "version_id": "v001",
            "fields": {
                "operating_cash_flow": 700,
                "net_income": 550,
                "capex": 110,
                "depreciation_amortization": 85,
                "sbc_expense": 22,
                "revenue": 2200,
                "receivables": 190,
                "inventory": 130,
                "accounts_payable": 95,
                "deferred_revenue_current": 35,
            },
        },
    ]


def test_question_spine_frozen():
    assert [q[0] for q in MUST_QUESTIONS] == [f"S3-M{i}" for i in range(1, 9)]
    assert [q[0] for q in SHOULD_QUESTIONS] == [f"S3-S{i}" for i in range(1, 6)]


def test_outcome_enum_only_four():
    assert STAGE3_OUTCOMES == {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}
    sem = Stage3SemanticReview(
        filled=True,
        review_source="fixture",
        maintenance_capex_status="UNKNOWN",
    )
    report = evaluate_stage3("SYNTH", _healthy_periods(), semantic=sem)
    assert report.process_outcome in STAGE3_OUTCOMES
    assert "BLOCKED" not in report.process_outcome


def test_fi_hard_stop():
    report = evaluate_stage3(
        "BANKX",
        _healthy_periods(),
        gate0_class="financial_institution",
        semantic=Stage3SemanticReview(filled=True, maintenance_capex_status="UNKNOWN"),
    )
    assert report.process_outcome == "TOO_HARD"
    assert report.refuse_reason
    assert report.terminates_later_stages is False
    assert "OUT OF SCOPE" in (report.refuse_reason or "") or "out of scope" in (
        report.refuse_reason or ""
    ).lower() or "HARD OUT OF SCOPE" in (report.refuse_reason or "") or "Financial Institutions" in (
        report.refuse_reason or ""
    )


def test_maintenance_unknown_by_default():
    report = evaluate_stage3(
        "SYNTH",
        _healthy_periods(),
        semantic=Stage3SemanticReview(filled=True, maintenance_capex_status="UNKNOWN"),
    )
    assert report.semantic.maintenance_capex_status == "UNKNOWN"
    m3 = next(a for a in report.question_answers if a.question_id == "S3-M3")
    assert "UNKNOWN" in m3.answer_summary


def test_maintenance_disclosed_with_evidence():
    sem = load_stage3_semantic_from_fixture(
        notes_payload={
            "maintenance_capex_status": "DISCLOSED_WITH_EVIDENCE",
            "maintenance_capex_evidence": "10-K Note 5: maintenance CapEx disclosed as 40",
            "maintenance_capex_amount": 40,
            "review_source": "fixture",
        }
    )
    assert sem.maintenance_capex_status == "DISCLOSED_WITH_EVIDENCE"
    report = evaluate_stage3("SYNTH", _healthy_periods(), semantic=sem)
    m3 = next(a for a in report.question_answers if a.question_id == "S3-M3")
    assert "DISCLOSED_WITH_EVIDENCE" in m3.answer_summary


def test_material_warning_escalation_carry_forward():
    sem = Stage3SemanticReview(
        filled=True,
        review_source="fixture",
        maintenance_capex_status="UNKNOWN",
        findings=[
            Stage3SemanticFinding(
                topic="factoring",
                citation="Note 7",
                classification="note",
                materiality_judgment="material",
                materiality_reason="Management discloses material receivables factoring program",
                escalate_to_human=True,
            )
        ],
    )
    report = evaluate_stage3("SYNTH", _healthy_periods(), semantic=sem)
    assert report.process_outcome == "REVIEW_REQUIRED"
    assert report.terminates_later_stages is False
    assert any("factoring" in c.lower() or "Factoring" in c or "factoring" in c for c in report.carry_forward_concerns) or any(
        "factoring" in w.lower() for w in report.cash_quality_warnings
    )


def test_no_mechanical_later_stage_block():
    sem = Stage3SemanticReview(
        filled=True,
        review_source="fixture",
        maintenance_capex_status="UNKNOWN",
        findings=[
            Stage3SemanticFinding(
                topic="unusual_cash",
                citation="MD&A",
                classification="mdna",
                materiality_judgment="material",
                materiality_reason="Serial non-recurring cash",
                escalate_to_human=True,
            )
        ],
    )
    report = evaluate_stage3("SYNTH", _healthy_periods(), semantic=sem)
    assert report.terminates_later_stages is False
    assert report.process_outcome == "REVIEW_REQUIRED"
    md = render_stage3_markdown(report)
    assert "does not alone terminate later stages" in md.lower() or "does not alone mechanically terminate" in md.lower() or "terminates_later_stages: False" in md


def test_report_shape_adhd_template():
    report = evaluate_stage3(
        "SYNTH",
        _healthy_periods(),
        semantic=Stage3SemanticReview(filled=True, maintenance_capex_status="UNKNOWN"),
    )
    md = render_stage3_markdown(report)
    for section in [
        "# Stage 3 — Cash Generation —",
        "## Outcome",
        "## Why",
        "## Cash conversion",
        "## Working capital",
        "## CapEx / reinvestment reality",
        "## Cash quality warnings",
        "## What is strong",
        "## What can break",
        "## Monitors",
        "## Missing / ambiguous",
        "## Sources",
    ]:
        assert section in md
    # No color / threshold language as investment rules
    assert "RED" not in md or "No RED" in md
    assert "pass/fail" in md.lower() or "No numeric" in md
    low = md.lower()
    assert "threshold" not in low.split("no numeric")[0] or "no numeric investment thresholds" in low


def test_no_threshold_color_score_in_module_contract():
    import fa.stage3.evaluate as ev
    import fa.stage3.calc as calc
    import inspect

    for mod in (ev, calc):
        src = inspect.getsource(mod)
        assert "RED" not in src or "No RED" in src or "no color" in src.lower()
        # No Stage 4 implementation
        assert "stage4" not in src.lower()
        assert "run_stage4" not in src


def test_heuristic_semantic_path():
    sem = heuristic_stage3_semantic(
        "The company uses supply chain finance and mentions restructuring charges."
    )
    assert sem.review_source == "heuristic"
    assert sem.maintenance_capex_status == "UNKNOWN"
    topics = {f.topic for f in sem.findings}
    assert "supplier_finance" in topics or "restructuring" in topics


def test_capex_conflict_drives_review_path():
    periods = _healthy_periods()
    periods[-1]["field_uncertainty"] = {"capex": "CapEx taxonomy conflict: tags disagree"}
    report = evaluate_stage3(
        "SYNTH",
        periods,
        semantic=Stage3SemanticReview(filled=True, maintenance_capex_status="UNKNOWN"),
    )
    assert report.process_outcome == "REVIEW_REQUIRED"
    assert any("CapEx conflict" in c or "capex" in c.lower() for c in report.carry_forward_concerns)


def test_fa_pipeline_still_has_no_run_stage3():
    """Stage 3 entrypoint lives under fa.stage3 — do not wire into analyze_company."""
    import fa.pipeline as pipe
    import fa.stage3.pipeline as s3pipe

    assert not hasattr(pipe, "run_stage3")
    assert "stage3" not in dir(pipe)
    assert hasattr(s3pipe, "run_stage3")
