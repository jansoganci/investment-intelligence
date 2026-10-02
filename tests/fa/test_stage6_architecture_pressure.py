"""Architecture pressure with SYNTHETIC fixtures (no production ticker hardcodes)."""
from __future__ import annotations

from fa.models import Stage6SemanticReview
from fa.stage6.evaluate import evaluate_stage6
from fa.stage6.archetype import adapt_from_stage4, dual_view_mandatory_for


def _sem(**notes):
    return Stage6SemanticReview(filled=True, review_source="fixture", **notes)


def _capital_periods(
    values_op,
    values_ta,
    *,
    gw=0.0,
    intang=0.0,
    acq=0.0,
):
    out = []
    for i, (op, ta) in enumerate(zip(values_op, values_ta)):
        out.append(
            {
                "period_key": f"FY{2021+i}",
                "period_type": "FY",
                "version_id": "v1",
                "fields": {
                    "operating_income": op,
                    "pretax_income": op * 0.9,
                    "income_tax": op * 0.18,
                    "total_assets": ta,
                    "cash_and_equivalents": ta * 0.03,
                    "accounts_payable": ta * 0.02,
                    "deferred_revenue_current": ta * 0.04,
                    "goodwill": gw,
                    "intangibles": intang,
                    "capex": -ta * 0.01,
                    "depreciation_amortization": ta * 0.008,
                    "business_acquisitions_cash": acq,
                    "equity_parent": ta * 0.5,
                    "total_debt": ta * 0.2,
                    "inventory": ta * 0.01,
                    "receivables": ta * 0.03,
                    "dividends_paid": -5,
                },
            }
        )
    return out


def test_synthetic_rop_like_a7_dual():
    """A7 acquisitive compounder pressure — dual spine mandatory; no ticker literal in prod."""
    report = evaluate_stage6(
        "synthetic_acq_compounder",
        _capital_periods(
            [180, 200, 220, 240, 260],
            [8000, 9000, 11000, 13000, 15000],
            gw=5000,
            intang=2500,
            acq=800,
        ),
        semantic=_sem(
            acquisition_context_notes="bolt-on acquisitions purchase accounting PPA",
            runway_notes="reinvestment via acquisitions and software platforms",
            maint_capex_status="NOT_DISCLOSED",
        ),
        thesis_summary="acquisitive compounder niche software platforms",
        thesis_capital="deploy capital via bolt-on M&A",
        force_primary="A7",
        stage4_archetype={
            "primary_archetype": "A7",
            "primary_label": "Acquisitive compounder",
            "secondary_traits": ["acquisitive", "recurring_revenue"],
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
            "why": "synthetic",
        },
    )
    assert report.archetype.primary_archetype == "A7"
    assert report.dual_roic.dual_view_mandatory is True
    assert report.dual_roic.dual_view_emitted is True
    assert report.dual_roic.ic_inclusive is not None
    assert report.dual_roic.ic_tangible is not None
    assert report.dual_roic.ic_tangible < report.dual_roic.ic_inclusive
    assert (report.calc.metrics.get("dual_roic") or {}).get("goodwill", 0) > 0
    assert report.terminates_later_stages is False
    assert any(t.get("id") == "FP-R10" for t in report.false_positive_tags)
    assert report.process_outcome in {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED"}


def test_synthetic_visa_like_capital_light():
    """Capital-light / unstable denom / ΔIC pathology — no ticker hardcode."""
    # Nearly flat assets, rising OP → ΔIC≈0
    report = evaluate_stage6(
        "synthetic_payments_network",
        _capital_periods(
            [800, 900, 1000, 1100, 1200],
            [500, 500, 500, 500, 500],  # flat IC → ΔIC≈0 pathology
            gw=50,
            intang=20,
        ),
        semantic=_sem(
            runway_notes="capital-light network; capital returned via buybacks",
            capital_destination_notes="share repurchase program excess cash",
            maint_capex_status="NOT_DISCLOSED",
        ),
        thesis_summary="payment network card network take rate",
        force_primary="A3",
    )
    assert report.archetype.primary_archetype == "A3"
    assert any(
        w.meaning_class == "not_meaningful" for w in report.incremental_roic_windows
    )
    assert any(t.get("id") == "FP-R7" for t in report.false_positive_tags)
    assert report.terminates_later_stages is False
    # High ROIC optics must not auto-fail or auto-PROCEED alone
    assert report.process_outcome in {"PROCEED", "CONDITIONAL", "REVIEW_REQUIRED", "TOO_HARD"}


def test_reuse_stage4_archetype_capital_drivers():
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
    assert dual_view_mandatory_for(adapted.primary_archetype, adapted.secondary_traits)
    assert any(d["id"] == "dual_spine_mandatory" for d in adapted.model_specific_drivers)


def test_maint_capex_unknown_when_undisclosed():
    report = evaluate_stage6(
        "synthetic_industrial",
        _capital_periods([50, 55, 60, 65], [400, 420, 450, 480], gw=0, intang=0),
        semantic=_sem(maint_capex_status="NOT_DISCLOSED"),
        force_primary="A5",
    )
    assert "UNKNOWN" in " ".join(report.reinvestment_composition_bullets) or any(
        "UNKNOWN" in m or "Maint CapEx" in m for m in report.monitors
    )
    # Must not invent maint CapEx number
    assert report.calc.metrics["reinvestment_composition"]["no_forced_maint_capex"] is True


def test_stage5_archetype_reuse_when_stage4_absent():
    """When Stage 4 CURRENT missing, Stage 5 archetype dict must be preferred over heuristic."""
    adapted = adapt_from_stage4(
        {
            "primary_archetype": "A3",
            "primary_label": "Network / payments platform",
            "secondary_traits": ["network_effects"],
            "classification_path": "AUTOMATED",
            "confidence": "MEDIUM",
            "provenance": "stage5_reuse",
            "why": "from stage5 CURRENT",
        }
    )
    assert adapted.primary_archetype == "A3"
    assert adapted.provenance == "stage5_reuse"
    assert dual_view_mandatory_for(adapted.primary_archetype, adapted.secondary_traits) is False
    assert any(d["id"] == "capital_light_outlets" for d in adapted.model_specific_drivers)


def test_non_a7_dual_conflict_emits_s6_h7_dual_view():
    """Material inclusive vs tangible spread → S6_H7_DUAL_VIEW_CONFLICT even for A3."""
    report = evaluate_stage6(
        "synthetic_network_with_gw",
        _capital_periods(
            [800, 900, 1000, 1100, 1200],
            [5000, 5200, 5400, 5600, 5800],
            gw=2000,
            intang=1500,
        ),
        semantic=_sem(maint_capex_status="NOT_DISCLOSED"),
        force_primary="A3",
        stage4_archetype={
            "primary_archetype": "A3",
            "primary_label": "Network / payments platform",
            "secondary_traits": ["network_effects"],
            "classification_path": "AUTOMATED",
            "confidence": "HIGH",
            "provenance": "stage5_reuse",
            "why": "synthetic",
        },
    )
    assert report.archetype.primary_archetype == "A3"
    assert report.dual_roic.dual_view_emitted is True
    assert "S6_H7_DUAL_VIEW_CONFLICT" in report.stage7_handoff_flags
    # ACQ opacity is A7/mandatory-path only
    assert "S6_H7_ACQ_RETURN_OPACITY" not in report.stage7_handoff_flags
    assert report.terminates_later_stages is False
