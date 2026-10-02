"""Architecture pressure tests with SYNTHETIC fixtures (not production ticker hardcodes)."""
from __future__ import annotations

from fa.stage4.archetype import propose_archetype
from fa.stage4.evaluate import evaluate_stage4
from fa.models import Stage4SemanticReview


def _sem(**notes):
    return Stage4SemanticReview(filled=True, review_source="fixture", **notes)


def _rev_periods(values, ma=None):
    out = []
    for i, v in enumerate(values):
        fields = {
            "revenue": v,
            "net_income": v * 0.2,
            "capex": v * 0.05,
            "operating_cash_flow": v * 0.25,
            "shares_diluted_weighted": 1000,
            "diluted_eps": (v * 0.2) / 1000,
        }
        if ma is not None:
            fields["business_acquisitions_cash"] = ma if i == len(values) - 1 else 0
        out.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": fields,
            }
        )
    return out


def test_synthetic_semiconductor_nvidia_like():
    thesis = "semiconductor gpu datacenter gpu wafer fabless chip design"
    arch = propose_archetype(thesis_summary=thesis)
    assert arch.primary_archetype == "A4"
    report = evaluate_stage4(
        "synthetic_semiconductor",
        _rev_periods([100, 130, 200, 280]),  # boom path
        semantic=_sem(cycle_notes="cyclical recovery in datacenter", volume_price_mix_notes="ASP up"),
        thesis_summary=thesis,
        thesis_runway="AI accelerator demand",
    )
    assert report.archetype.primary_archetype == "A4"
    assert any(t.get("id") in {"FP2", "FP10"} for t in report.false_positive_tags)
    assert report.process_outcome in {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED"}
    assert report.terminates_later_stages is False


def test_synthetic_hybrid_tesla_like():
    thesis = (
        "electric vehicle manufacturer energy generation and storage "
        "hardware and software platform manufacturer and technology platform"
    )
    arch = propose_archetype(thesis_summary=thesis)
    assert arch.primary_archetype in {"A10", "A5", "A4"}
    report = evaluate_stage4(
        "synthetic_ev_platform",
        _rev_periods([50, 80, 120, 150]),
        semantic=_sem(runway_claim_notes="capacity expansion", volume_price_mix_notes="volume growth"),
        thesis_summary=thesis,
        thesis_runway="vehicle + energy platform",
    )
    # Hybrid: one PRIMARY + traits; may REVIEW if ambiguous
    assert report.archetype.primary_archetype in {"A10", "A5", "A4", "A11"}
    assert len(report.archetype.model_specific_drivers) <= 3


def test_synthetic_visa_like_payments():
    thesis = "payment network card network transaction volume take rate merchant acquiring"
    report = evaluate_stage4(
        "synthetic_payments_network",
        _rev_periods([100, 110, 121, 133]),
        semantic=_sem(
            volume_price_mix_notes="transaction volume increased",
        ),
        thesis_summary=thesis,
        thesis_runway="payments volume geo",
    )
    assert report.archetype.primary_archetype == "A3"
    assert report.archetype.classification_path == "AUTOMATED"


def test_synthetic_saas():
    thesis = "saas subscription software arr annual recurring revenue net revenue retention cloud software"
    report = evaluate_stage4(
        "synthetic_saas_platform",
        _rev_periods([40, 55, 75, 100]),
        semantic=_sem(
            recurring_notes="ARR and net retention discussed",
            backlog_rpo_notes="RPO increased",
            dilution_notes="share-based compensation",
        ),
        thesis_summary=thesis,
        thesis_runway="seat expansion",
    )
    assert report.archetype.primary_archetype == "A2"
    assert report.archetype.model_slot_status == "set"


def test_synthetic_rio_like_commodity():
    thesis = "iron ore copper mining bulk commodity spot price mining and metals"
    report = evaluate_stage4(
        "synthetic_commodity_miner",
        _rev_periods([200, 150, 180, 160]),
        semantic=_sem(cycle_notes="cyclical peak and trough", volume_price_mix_notes="price vs volume"),
        thesis_summary=thesis,
        thesis_runway="cost curve",
        extend_full_cycle=True,
    )
    assert report.archetype.primary_archetype == "A8"
    assert any(t.get("id") == "FP2" for t in report.false_positive_tags)


def test_synthetic_nclh_like_travel():
    thesis = "cruise passenger capacity load factor room nights hotel occupancy"
    report = evaluate_stage4(
        "synthetic_cruise_travel",
        _rev_periods([80, 40, 90, 120]),  # rebound path
        semantic=_sem(
            cycle_notes="post-pandemic recovery rebound from weak prior period",
            volume_price_mix_notes="occupancy and yield",
        ),
        thesis_summary=thesis,
        thesis_runway="capacity vs demand",
    )
    assert report.archetype.primary_archetype == "A9"
    assert any(t.get("id") in {"FP2", "FP5"} for t in report.false_positive_tags)


def test_no_production_ticker_hardcodes_in_stage4_modules():
    """Production modules must not hardcode KO/NVDA/TSLA/etc as logic branches."""
    from pathlib import Path
    import re

    root = Path("/workspace/investment_intelligence/fa/stage4")
    forbidden = re.compile(r'\b(KO|NVDA|TSLA|VISA|"V"|ADBE|RIO|NCLH)\b')
    for path in root.glob("*.py"):
        text = path.read_text()
        # allow mentions in comments about UAT? Prefer zero ticker literals in code strings
        # Strip comments
        code = "\n".join(
            ln for ln in text.splitlines() if not ln.strip().startswith("#")
        )
        # Visa keyword in archetype signals is the word 'payment' not ticker V
        hits = forbidden.findall(code)
        # Filter common false positives
        hits = [h for h in hits if h not in {"V"}]  # lone V too noisy; check "VISA" ticker style
        assert not hits, f"{path.name} has ticker hardcodes: {hits}"
