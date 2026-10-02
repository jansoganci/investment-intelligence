"""Architecture pressure tests with SYNTHETIC fixtures (not production ticker hardcodes)."""
from __future__ import annotations

from fa.models import Stage5SemanticReview
from fa.stage5.evaluate import evaluate_stage5
from fa.stage5.archetype import adapt_from_stage4


def _sem(**notes):
    return Stage5SemanticReview(filled=True, review_source="fixture", **notes)


def _margin_periods(values, op_frac=0.2, gm_frac=0.4):
    out = []
    for i, v in enumerate(values):
        out.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "revenue": v,
                    "gross_profit": v * gm_frac,
                    "operating_income": v * op_frac,
                    "cost_of_revenue": v * (1 - gm_frac),
                    "sbc_expense": v * 0.02,
                },
            }
        )
    return out


def test_synthetic_ko_like_mature_franchise():
    thesis = "branded beverage concentrate household brand bottling system sparkling soft drink"
    report = evaluate_stage5(
        "synthetic_mature_beverage",
        _margin_periods([400, 410, 420, 430, 440], op_frac=0.28, gm_frac=0.60),
        semantic=_sem(
            pricing_power_notes="pricing power brand premium pass-through",
            margin_bridge_notes="gross margin stable with price/mix",
            cost_advantage_notes="operating leverage",
            input_cost_notes="sweetener and aluminum commodity costs",
        ),
        thesis_summary=thesis,
        thesis_margins="stable franchise economics",
        force_primary="A1",
    )
    assert report.archetype.primary_archetype == "A1"
    assert "MATURE_FRANCHISE_ECONOMICS_OK" in report.context_tags
    assert report.terminates_later_stages is False
    assert report.process_outcome in {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED"}


def test_synthetic_visa_like_payments():
    thesis = "payment network card network transaction volume take rate merchant acquiring"
    report = evaluate_stage5(
        "synthetic_payments_network",
        _margin_periods([100, 110, 121, 133], op_frac=0.55, gm_frac=0.75),
        semantic=_sem(
            pricing_power_notes="take rate discussed",
            cost_advantage_notes="network opex leverage operating leverage",
            unit_econ_notes="take-rate vs volume",
        ),
        thesis_summary=thesis,
        force_primary="A3",
    )
    assert report.archetype.primary_archetype == "A3"
    assert report.archetype.model_slot == "take_rate"


def test_synthetic_saas_sbc():
    thesis = "saas subscription software arr cloud software"
    report = evaluate_stage5(
        "synthetic_saas",
        _margin_periods([40, 55, 75, 100], op_frac=0.05, gm_frac=0.80),
        semantic=_sem(
            sbc_nongaap_notes="share-based compensation and non-GAAP adjusted operating margin",
            investment_phase_notes="investment phase operating leverage negative",
            margin_bridge_notes="gross margin durable",
        ),
        thesis_summary=thesis,
        force_primary="A2",
    )
    assert report.archetype.primary_archetype == "A2"
    assert any(t.get("id") in {"FP5", "FP12"} for t in report.false_positive_tags)


def test_synthetic_cyclical_peak_watch():
    thesis = "commodity iron ore copper mining bulk commodity spot price"
    report = evaluate_stage5(
        "synthetic_commodity",
        _margin_periods([80, 90, 200, 250], op_frac=0.40, gm_frac=0.55),
        semantic=_sem(
            cycle_peak_notes="cyclical peak margins and commodity price windfall",
        ),
        thesis_summary=thesis,
        force_primary="A8",
        extend_full_cycle=True,
    )
    assert report.archetype.primary_archetype == "A8"
    assert "CYCLE_PEAK_MARGIN_RISK" in report.context_tags
    assert any(t.get("id") == "FP1" for t in report.false_positive_tags)


def test_synthetic_ses_retailer():
    thesis = "retailer everyday low price scale economies shared with customers"
    report = evaluate_stage5(
        "synthetic_ses_retail",
        _margin_periods([200, 210, 220, 230], op_frac=0.04, gm_frac=0.25),
        semantic=_sem(
            ses_notes="scale economies shared with customers everyday low price",
            cost_advantage_notes="scale advantage cost productivity",
        ),
        thesis_summary=thesis,
        force_primary="A6",
    )
    assert "SCALE_ECONOMIES_SHARED_OK" in report.context_tags
    # SES is context tag, not outcome
    assert report.process_outcome in {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}


def test_reuse_stage4_archetype():
    adapted = adapt_from_stage4(
        {
            "primary_archetype": "A7",
            "primary_label": "Acquisitive compounder",
            "secondary_traits": ["acquisitive"],
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
            "why": "from stage4",
        }
    )
    assert adapted.primary_archetype == "A7"
    assert adapted.provenance == "stage4_reuse"
    assert any(d["id"] == "organic_vs_acquired_margin" for d in adapted.model_specific_drivers)
