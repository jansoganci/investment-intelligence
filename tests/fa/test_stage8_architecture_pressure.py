"""Architecture pressure with SYNTHETIC fixtures (no production ticker hardcodes)."""
from __future__ import annotations

from fa.stage8.evaluate import evaluate_stage8
from fa.stage8.report import render_stage8_markdown


def _periods(*, a7=False, n=5, base_year=2021):
    out = []
    for i in range(n):
        fields = {
            "operating_cash_flow": 800 + i * 40,
            "capex": 50 + i * 2,
            "business_acquisitions_cash": (400 + i * 80) if a7 else 0.0,
            "cash_and_equivalents": 200.0,
            "total_debt": 1500.0 + i * 50,
            "shares_diluted_weighted": 100.0 + i * 0.5,
            "shares_outstanding": 99.0 + i * 0.4,
            "revenue": 5000 + i * 200,
            "net_income": 600 + i * 30,
            "sbc_expense": 40 + i,
            "operating_income": 700 + i * 20,
        }
        out.append(
            {
                "period_key": f"FY{base_year+i}",
                "period_type": "FY",
                "version_id": "v1",
                "period_end": f"{base_year+i}-12-31",
                "reporting_currency": "USD",
                "fields": fields,
            }
        )
    return out


def test_synthetic_a7_review_non_terminating_no_buy_sell():
    report = evaluate_stage8(
        "synthetic_acq_compounder",
        _periods(a7=True),
        market_price=120.0,
        price_currency="USD",
        price_as_of="2026-09-29T14:00:00+00:00",
        price_source="unit_test_quote",
        force_primary="A7",
        stage6_artifact={
            "process_outcome": "REVIEW_REQUIRED",
            "stage7_handoff_flags": [
                "S6_H7_DUAL_VIEW_CONFLICT",
                "S6_H7_ACQ_RETURN_OPACITY",
            ],
            "archetype": {"primary_archetype": "A7"},
        },
        stage7_artifact={
            "process_outcome": "REVIEW_REQUIRED",
            "alignment_label": "aligned",
            "s6_handoff_flags_consumed": ["S6_H7_ACQ_RETURN_OPACITY"],
        },
    )
    assert report.process_outcome in {"REVIEW_REQUIRED", "CONDITIONAL"}
    assert report.terminates_later_stages is False
    assert report.a7_dual_exhibits is True
    assert "S6_H7_ACQ_RETURN_OPACITY" in report.s6_handoff_flags_consumed
    assert len(report.va_lenses) == 8
    md = render_stage8_markdown(report)
    assert "BUY" not in md or "No BUY" in md or "no BUY" in md.lower()
    assert "SELL" not in md.replace("NEVER", "").replace("never", "") or "no BUY/SELL" in md
    assert "CROSS-CHECK" in md or "cross-check" in md.lower() or "CROSS-CHECKS" in md
    assert report.dual_terminal_note is not None
    # expectations vocab not cheap/expensive
    assert report.expectations_label in {
        "conservative",
        "plausible",
        "demanding",
        "heroic",
        "incoherent_with_evidence",
        "unknown",
    }
    assert report.expectations_label not in {"cheap", "expensive"}


def test_missing_price_leads_unknown_freshness_review_or_hard():
    report = evaluate_stage8(
        "synthetic_no_price",
        _periods(a7=False),
        market_price=None,
        price_currency="USD",
        price_as_of=None,
        price_source=None,
        force_primary="A3",
    )
    assert report.staleness_class == "UNKNOWN"
    assert report.price_sensitive_suppressed is True
    assert report.terminates_later_stages is False
    assert report.process_outcome in {"REVIEW_REQUIRED", "TOO_HARD"}


def test_va_lenses_no_weighted_average_field():
    report = evaluate_stage8(
        "synthetic_standard",
        _periods(a7=False),
        market_price=55.0,
        price_currency="USD",
        price_as_of="2026-09-29T14:00:00+00:00",
        price_source="unit_test",
        force_primary="A1",
    )
    d = report.to_dict()
    assert "weighted_va_score" not in d
    assert "averaged_valuation_score" not in d
    assert "fair_value_point" not in d
    assert report.calc.metrics.get("no_method_average") is True
