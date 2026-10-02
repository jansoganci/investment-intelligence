"""Stage 6 evaluate + report — outcomes contextual; non-terminating; dual view."""
from __future__ import annotations

from fa.models import Stage6SemanticReview
from fa.stage6.evaluate import evaluate_stage6
from fa.stage6.report import render_stage6_markdown
from fa.stage6.questions import STAGE6_OUTCOMES


def _periods(*, gw=200.0, intang=100.0, n=5, ic_growth=80.0, op_growth=5.0):
    out = []
    for i in range(n):
        out.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "operating_income": 100 + i * op_growth,
                    "pretax_income": 90 + i * op_growth,
                    "income_tax": 20,
                    "total_assets": 1000 + i * ic_growth,
                    "cash_and_equivalents": 40,
                    "accounts_payable": 30,
                    "deferred_revenue_current": 20,
                    "goodwill": gw,
                    "intangibles": intang,
                    "capex": -25,
                    "depreciation_amortization": 20,
                    "business_acquisitions_cash": 50 if i > 2 else 10,
                    "equity_parent": 600,
                    "total_debt": 200,
                    "inventory": 15,
                    "receivables": 40,
                    "dividends_paid": -10,
                    "share_repurchases": -5,
                },
            }
        )
    return out


def test_fi_refused_too_hard():
    report = evaluate_stage6(
        "BANKX",
        _periods(),
        gate0_class="financial_institution",
        semantic=Stage6SemanticReview(filled=True, review_source="fixture"),
    )
    assert report.process_outcome == "TOO_HARD"
    assert report.terminates_later_stages is False
    assert report.refuse_reason


def test_a7_dual_view_mandatory():
    sem = Stage6SemanticReview(
        filled=True,
        review_source="fixture",
        acquisition_context_notes="bolt-on acquisitions and purchase accounting",
        runway_notes="reinvestment via acquisitions",
        maint_capex_status="NOT_DISCLOSED",
    )
    report = evaluate_stage6(
        "SYNTH_ACQ",
        _periods(),
        semantic=sem,
        thesis_summary="acquisitive compounder software platforms bolt-on M&A",
        thesis_capital="reinvest via acquisitions",
        force_primary="A7",
        stage4_archetype={
            "primary_archetype": "A7",
            "primary_label": "Acquisitive compounder",
            "secondary_traits": ["acquisitive"],
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
            "why": "test",
        },
    )
    assert report.archetype.primary_archetype == "A7"
    assert report.dual_roic is not None
    assert report.dual_roic.dual_view_mandatory is True
    assert report.dual_roic.dual_view_emitted is True
    assert report.dual_roic.tangible_ne_ma_success is True
    assert report.terminates_later_stages is False
    assert report.process_outcome in STAGE6_OUTCOMES
    assert len(report.benchmark_results) == 8
    assert all(b.dimension_id.startswith("RC") for b in report.benchmark_results)
    md = render_stage6_markdown(report)
    assert "No RED/ORANGE/GREEN" in md
    assert "Incremental ROIC ≠ Stage 5 IOM" in md or "≠ Stage 5 IOM" in md
    assert "Dashboard 1" in md
    assert report.runway_label in {"ample", "limited", "unclear", "not_applicable"}


def test_incremental_not_meaningful_when_flat_ic():
    # Flat IC → ΔIC≈0 → not_meaningful
    periods = []
    for i in range(4):
        periods.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "operating_income": 200 + i * 20,
                    "pretax_income": 180 + i * 20,
                    "income_tax": 40,
                    "total_assets": 500,  # flat
                    "cash_and_equivalents": 20,
                    "accounts_payable": 10,
                    "deferred_revenue_current": 5,
                    "goodwill": 0,
                    "intangibles": 0,
                    "equity_parent": 400,
                    "total_debt": 50,
                },
            }
        )
    report = evaluate_stage6(
        "SYNTH_LIGHT",
        periods,
        semantic=Stage6SemanticReview(filled=True, review_source="fixture"),
        force_primary="A3",
    )
    assert any(
        w.meaning_class == "not_meaningful" for w in report.incremental_roic_windows
    )
    assert report.terminates_later_stages is False


def test_d10_elevates_review_required():
    # Growing IC with falling/negative incremental NOPAT path
    periods = []
    ops = [100, 90, 70, 40]  # declining OP
    assets = [800, 1000, 1300, 1700]  # rising IC
    for i, (op, ta) in enumerate(zip(ops, assets)):
        periods.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "operating_income": op,
                    "pretax_income": op - 10,
                    "income_tax": 15,
                    "total_assets": ta,
                    "cash_and_equivalents": 20,
                    "accounts_payable": 15,
                    "deferred_revenue_current": 10,
                    "goodwill": 100,
                    "intangibles": 50,
                    "business_acquisitions_cash": 200,
                    "equity_parent": 500,
                    "total_debt": 300,
                },
            }
        )
    report = evaluate_stage6(
        "SYNTH_DESTROY",
        periods,
        semantic=Stage6SemanticReview(
            filled=True,
            review_source="fixture",
            acquisition_context_notes="serial acquisitions",
            # no investment_phase_notes → D10 can fire
        ),
        force_primary="A7",
        stage4_archetype={
            "primary_archetype": "A7",
            "secondary_traits": ["acquisitive"],
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
        },
    )
    assert report.d10_elevated is True
    assert report.process_outcome == "REVIEW_REQUIRED"
    assert "S6_H7_PERSISTENT_VALUE_DESTRUCTIVE_REINVEST" in report.stage7_handoff_flags
    assert report.terminates_later_stages is False
