"""Near-term contractual obligations + gross_debt: sum vs includes-flag."""
from __future__ import annotations

from fa.stage2.calc import compute_stage2_metrics


def _doc(fields):
    return {"period_key": "FY2025", "version_id": "v001", "fields": fields}


def test_separate_std_and_cpltd_sum_not_max():
    """Case separate: std + cpltd + lease_c; gross adds ltd (no max)."""
    r = compute_stage2_metrics(
        _doc(
            {
                "short_term_debt": 100,
                "current_portion_ltd": 50,
                "lease_liability_current": 10,
                "long_term_debt": 200,
            }
        )
    )
    assert r.metrics["near_term_contractual_obligations"] == 160
    assert r.metrics["gross_debt"] == 350  # 100+50+200


def test_includes_flag_omits_cpltd():
    """Case includes: flag True → near_term = std + lease; gross = std + ltd only."""
    r = compute_stage2_metrics(
        _doc(
            {
                "short_term_debt": 150,  # includes cpltd
                "current_portion_ltd": 50,
                "lease_liability_current": 10,
                "long_term_debt": 200,
                "short_term_debt_includes_current_ltd": True,
            }
        )
    )
    assert r.metrics["near_term_contractual_obligations"] == 160  # 150+10
    assert r.metrics["gross_debt"] == 350  # 150+200; cpltd not added


def test_only_std_plus_leases():
    r = compute_stage2_metrics(
        _doc(
            {
                "short_term_debt": 100,
                "lease_liability_current": 10,
                "long_term_debt": 200,
            }
        )
    )
    assert r.metrics["near_term_contractual_obligations"] == 110
    assert r.metrics["gross_debt"] == 300


def test_only_cpltd_plus_leases():
    r = compute_stage2_metrics(
        _doc(
            {
                "current_portion_ltd": 50,
                "lease_liability_current": 10,
                "long_term_debt": 200,
            }
        )
    )
    assert r.metrics["near_term_contractual_obligations"] == 60
    assert r.metrics["gross_debt"] == 250  # 50+200


def test_ko_shaped_numbers_additive():
    """KO-shaped: Loans/notes + CPLTD + current leases (separate BS lines)."""
    r = compute_stage2_metrics(
        _doc(
            {
                "short_term_debt": 1_551_000_000,
                "current_portion_ltd": 1_822_000_000,
                "lease_liability_current": 321_000_000,
                "short_term_debt_includes_current_ltd": False,
            }
        )
    )
    assert r.metrics["near_term_contractual_obligations"] == 3_694_000_000


def test_null_when_all_near_term_components_missing():
    r = compute_stage2_metrics(_doc({"long_term_debt": 100}))
    assert r.metrics["near_term_contractual_obligations"] is None
    assert "near_term_contractual_obligations" in r.null_reasons


def test_flag_false_explicit_same_as_missing():
    r_missing = compute_stage2_metrics(
        _doc({"short_term_debt": 100, "current_portion_ltd": 50, "lease_liability_current": 10})
    )
    r_false = compute_stage2_metrics(
        _doc(
            {
                "short_term_debt": 100,
                "current_portion_ltd": 50,
                "lease_liability_current": 10,
                "short_term_debt_includes_current_ltd": False,
            }
        )
    )
    assert r_missing.metrics["near_term_contractual_obligations"] == 160
    assert r_false.metrics["near_term_contractual_obligations"] == 160
    assert r_false.metrics["gross_debt"] == 150  # std+cpltd, no ltd
