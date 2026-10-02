"""Wave 4 regression — B4 disruption wording, C3 growth basis, C2 duration, C1 dual-series."""
from __future__ import annotations

from fa.comparability import (
    annotate_yoy_rows_with_breaks,
    attach_disclosed_comparable_companion,
    detect_comparability_breaks,
    window_crosses_break,
)
from fa.stage2.calc import compute_stage2_metrics
from fa.stage2.evaluate import _prior_year_period
from fa.stage4.calc import (
    annotate_duration,
    compute_stage4_metrics,
    is_fifty_three_week_duration,
    period_duration_days,
)
from fa.stage6.calc import compute_stage6_metrics
from fa.stage9.evaluate import (
    _disruption_breaker_copy,
    _disruption_monitor_only_copy,
    _fintech_disruption_wording_supported,
    _build_breakers,
)
from fa.models import Stage9SemanticFinding, Stage9SemanticReview


# ---------------------------------------------------------------------------
# B4 — archetype/evidence-conditioned disruption wording
# ---------------------------------------------------------------------------


def test_w4_b4_no_fintech_wording_without_support():
    assert _fintech_disruption_wording_supported("A7", None) is False
    assert _fintech_disruption_wording_supported("A6", None) is False
    mon = _disruption_monitor_only_copy(fintech_ok=False)
    assert "fintech" not in mon.lower()
    mech, _ind, mons = _disruption_breaker_copy(fintech_ok=False)
    assert "fintech" not in mech.lower()
    assert not any("fintech" in m.lower() for m in mons)
    assert not any("multi-homing" in m.lower() for m in mons)


def test_w4_b4_fintech_wording_when_a3_or_evidence():
    assert _fintech_disruption_wording_supported("A3", None) is True
    sem = Stage9SemanticReview(
        findings=[
            Stage9SemanticFinding(
                topic="competition",
                excerpt="We are a global financial technology company competing with fintechs.",
                evidence_kind="CLAIM",
            )
        ],
        filled=True,
    )
    assert _fintech_disruption_wording_supported("A7", sem) is True
    mon = _disruption_monitor_only_copy(fintech_ok=True)
    assert "fintech" in mon.lower()
    mech, _, mons = _disruption_breaker_copy(fintech_ok=True)
    assert "fintech" in mech.lower()


def test_w4_b4_breaker_assembly_industrial_no_fintech_monitor():
    """DE/DHR/AZO-like: disruption topic without fintech evidence → no fintech monitor."""
    sem = Stage9SemanticReview(
        findings=[
            Stage9SemanticFinding(
                topic="disruption",
                excerpt="Competition and technological change may affect our agricultural equipment business.",
                evidence_kind="CLAIM",
            ),
            Stage9SemanticFinding(
                topic="moat_attack_surface",
                excerpt="Competitors may develop alternative products that erode share.",
                evidence_kind="CLAIM",
            ),
        ],
        filled=True,
    )
    breakers, monitors = _build_breakers(
        gate2={},
        semantic=sem,
        primary="A7",
        concentration={},
        regulatory_posture="unknown",
    )
    for b in breakers:
        blob = f"{b.mechanism} {' '.join(b.monitoring_variables or [])}".lower()
        assert "fintech" not in blob
        assert "multi-homing" not in blob
    assert monitors, "expected monitor-only disruption seed"
    for m in monitors:
        assert "fintech" not in m.lower()


# ---------------------------------------------------------------------------
# C3 — Stage 2 revenue growth basis
# ---------------------------------------------------------------------------


def _period(key, ptype, rev, **extra):
    return {
        "period_key": key,
        "period_type": ptype,
        "fields": {"revenue": rev, **extra},
    }


def test_w4_c3_qoq_labeled_and_yoy_companion():
    """DE-like: −5.69% is QoQ Q3 vs Q2; YoY companion separate."""
    cur = _period("2026Q3", "Q", 12_608_000_000)
    prior = _period("2026Q2", "Q", 13_369_000_000)
    yoy = _period("2025Q3", "Q", 12_018_000_000)
    calc = compute_stage2_metrics(cur, prior, prior_yoy=yoy)
    m = calc.metrics
    assert abs(m["revenue_growth_qoq"] - (-0.05692273169272197)) < 1e-9
    assert m["revenue_growth"] == m["revenue_growth_qoq"]
    assert m["revenue_growth_basis"] == "sequential_prior_period"
    assert "not FY YoY" in (m.get("revenue_growth_label") or "")
    assert m["revenue_growth_yoy"] is not None
    assert abs(m["revenue_growth_yoy"] - ((12_608e9 - 12_018e9) / 12_018e9 * 1e-9 / 1e-9)) < 1e-6 or abs(
        m["revenue_growth_yoy"] - ((12_608_000_000 - 12_018_000_000) / 12_018_000_000)
    ) < 1e-9
    assert m["revenue_growth_yoy_basis"] == "same_shape_prior_year_period"


def test_w4_c3_missing_yoy_no_gate_null_only():
    cur = _period("2026Q3", "Q", 100)
    prior = _period("2026Q2", "Q", 110)
    calc = compute_stage2_metrics(cur, prior, prior_yoy=None)
    assert calc.metrics["revenue_growth_qoq"] is not None
    assert calc.metrics["revenue_growth_yoy"] is None
    assert "prior_year_period_not_available" in calc.null_reasons.get("revenue_growth_yoy", "")


def test_w4_c3_prior_year_period_helper():
    periods = [
        _period("2026Q3", "Q", 1),
        _period("2026Q2", "Q", 1),
        _period("2025Q3", "Q", 1),
        _period("FY2025", "FY", 1),
        _period("FY2024", "FY", 1),
    ]
    assert _prior_year_period(periods[0], periods)["period_key"] == "2025Q3"
    assert _prior_year_period(_period("FY2025", "FY", 1), periods)["period_key"] == "FY2024"


# ---------------------------------------------------------------------------
# C2 — duration disclosure
# ---------------------------------------------------------------------------


def test_w4_c2_duration_days_and_53_week_flag():
    # COST-like FY2023: 2022-08-29 → 2023-09-03 inclusive ≈ 371
    doc = {
        "period_key": "FY2023",
        "period_type": "FY",
        "period_start": "2022-08-29",
        "period_end": "2023-09-03",
        "fields": {"revenue": 242_290_000_000},
    }
    dur = period_duration_days(doc)
    assert dur == 371
    assert is_fifty_three_week_duration(dur) is True
    meta = annotate_duration(doc)
    assert meta["fifty_three_week"] is True


def test_w4_c2_unequal_duration_yoy_flagged_no_normalize():
    periods = [
        {
            "period_key": "FY2022",
            "period_type": "FY",
            "period_start": "2021-08-30",
            "period_end": "2022-08-28",  # 364d
            "fields": {"revenue": 226_954_000_000},
        },
        {
            "period_key": "FY2023",
            "period_type": "FY",
            "period_start": "2022-08-29",
            "period_end": "2023-09-03",  # 371d
            "fields": {"revenue": 242_290_000_000},
        },
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "period_start": "2023-09-04",
            "period_end": "2024-09-01",
            "fields": {"revenue": 254_453_000_000},
        },
    ]
    calc = compute_stage4_metrics(periods)
    yoy = calc.metrics["revenue_yoy"]
    pair = next(r for r in yoy if r["from_period"] == "FY2022" and r["to_period"] == "FY2023")
    assert pair["unequal_duration"] is True
    assert pair["duration_normalized"] is False
    assert pair["week_adjusted_value"] is None
    assert pair["duration_honesty_flag"] == "UNEQUAL_DURATION_COMPARISON"
    assert pair["to_fifty_three_week"] is True
    # Reported arithmetic preserved (not week-adjusted)
    assert pair["fraction"] is not None


# ---------------------------------------------------------------------------
# C1 — dual-series / COMPARABILITY_BREAK
# ---------------------------------------------------------------------------


def _dhr_like_periods():
    """Regression shape only — Veralto cliff; no ticker hardcode in production path."""
    return [
        {
            "period_key": f"FY{y}",
            "period_type": "FY",
            "period_start": f"{y}-01-01",
            "period_end": f"{y}-12-31",
            "fields": {"revenue": rev},
        }
        for y, rev in [
            (2021, 29_453_000_000),
            (2022, 31_471_000_000),
            (2023, 23_890_000_000),
            (2024, 23_875_000_000),
            (2025, 24_568_000_000),
        ]
    ]


def test_w4_c1_cliff_with_perimeter_cue_flags_break_no_recast():
    periods = _dhr_like_periods()
    breaks = detect_comparability_breaks(
        periods,
        semantic_texts=[
            "Veralto Separation presented as discontinued operations; "
            "statements for all periods presented reflect this business as a discontinued operation."
        ],
    )
    assert breaks
    pair = next(
        b for b in breaks if b["from_period"] == "FY2022" and b["to_period"] == "FY2023"
    )
    assert pair["honesty_flag"] == "COMPARABILITY_BREAK"
    assert pair["series"] == "as_reported"
    assert pair["comparable_companion"] is None
    assert pair["model_reconstruction"] is False

    calc = compute_stage4_metrics(
        periods,
        semantic_texts=[
            "discontinued operations; spin separation of the environmental business"
        ],
    )
    yoy = calc.metrics["revenue_yoy"]
    cliff = next(r for r in yoy if r["from_period"] == "FY2022" and r["to_period"] == "FY2023")
    assert cliff["comparability_break"] is True
    assert cliff["honesty_flag"] == "COMPARABILITY_BREAK"
    assert cliff["series"] == "as_reported"
    assert cliff["clean_organic_yoy"] is False
    # As-reported arithmetic preserved (not overwritten / not nulled away)
    assert cliff["fraction"] is not None
    assert abs(cliff["fraction"] - ((23_890e9 - 31_471e9) / 31_471e9)) < 1e-6 or abs(
        cliff["fraction"] - ((23_890_000_000 - 31_471_000_000) / 31_471_000_000)
    ) < 1e-9
    assert calc.metrics["revenue_series_primary"] == "as_reported"
    assert calc.metrics["comparable_companion_present"] is False


def test_w4_c1_cliff_alone_without_cue_not_auto_break():
    """Cyclical decline without perimeter cue must not force COMPARABILITY_BREAK."""
    periods = [
        {
            "period_key": "FY2023",
            "period_type": "FY",
            "fields": {"revenue": 61_251_000_000},
        },
        {
            "period_key": "FY2024",
            "period_type": "FY",
            "fields": {"revenue": 51_716_000_000},
        },
    ]
    breaks = detect_comparability_breaks(periods, semantic_texts=None)
    assert breaks == []


def test_w4_c1_disclosed_companion_attached_never_overwrites_as_reported():
    breaks = detect_comparability_breaks(
        _dhr_like_periods(),
        explicit_breaks=[
            {
                "from_period": "FY2022",
                "to_period": "FY2023",
                "reason": "explicit_test_break",
            }
        ],
    )
    companion = [
        {
            "period_key": "FY2022",
            "revenue": 20_000_000_000,
            "source": "10-K continuing ops disclosure",
            "statement_basis": "continuing_operations",
        }
    ]
    b = attach_disclosed_comparable_companion(breaks[0], companion_series=companion)
    assert b["comparable_companion"]["series"] == "comparable_continuing_ops_disclosed"
    assert b["comparable_companion"]["model_reconstruction"] is False
    # As-reported series identity unchanged
    assert b["series"] == "as_reported"


def test_w4_c1_stage6_window_knows_break_series():
    periods = _dhr_like_periods()
    # Minimal IC/NOPAT fields so windows can form
    for p in periods:
        f = p["fields"]
        f.update(
            {
                "operating_income": f["revenue"] * 0.2,
                "total_assets": f["revenue"] * 1.5,
                "cash_and_equivalents": 1_000_000_000,
                "short_term_debt": 0,
                "long_term_debt": 5_000_000_000,
                "goodwill": 10_000_000_000,
                "intangibles": 2_000_000_000,
            }
        )
    calc = compute_stage6_metrics(
        periods,
        semantic_texts=["discontinued operations after spin separation"],
    )
    assert calc.metrics["roic_series_primary"] == "as_reported"
    assert calc.metrics["comparability_breaks"]
    wins = calc.metrics.get("incremental_roic_windows") or []
    crossed = [w for w in wins if w.get("comparability_break")]
    assert crossed, "expected at least one multi-year window to cross FY2022→FY2023 break"
    for w in crossed:
        assert w.get("series") == "as_reported"
        assert w.get("honesty_flag") == "COMPARABILITY_BREAK"


def test_w4_c1_stage4_harvest_surfaces_perimeter_cue_from_filing_text():
    """Wave 4 C1 harvest gap: Stage4 _KEYWORD_MAP must surface disc-ops/spin cues.

    Regression shape uses DHR-like revenue cliff + real Veralto-style MD&A language
    (no ticker hardcode in production harvest path).
    """
    from fa.stage4.semantic import heuristic_stage4_semantic, semantic_text_blob
    from fa.comparability import semantic_suggests_perimeter_break

    # General disclosed language (spin / discontinued / continuing) — not ticker-specific
    filing_text = (
        "Veralto Corporation Separation. On September 30, 2023, the Company completed "
        "the separation of its former Environmental & Applied Solutions business. "
        "DISCONTINUED OPERATIONS includes the results of the disposed business. "
        "Financial data refer to continuing operations only. The spin-off of the "
        "former segment is presented as a discontinued operation."
    )
    rev = heuristic_stage4_semantic(filing_text, source_label="fixture_10k_mdna")
    peri = [f for f in rev.findings if f.topic == "comparability_perimeter"]
    assert peri, "expected comparability_perimeter harvest hit"
    assert peri[0].evidence_kind == "FACT"
    blob = semantic_text_blob(rev)
    assert semantic_suggests_perimeter_break(blob)

    calc = compute_stage4_metrics(_dhr_like_periods(), semantic_texts=[blob])
    cliff = next(
        r
        for r in calc.metrics["revenue_yoy"]
        if r["from_period"] == "FY2022" and r["to_period"] == "FY2023"
    )
    assert cliff["honesty_flag"] == "COMPARABILITY_BREAK"
    assert cliff["series"] == "as_reported"
    assert cliff["comparable_companion"] is None
    assert cliff["fraction"] is not None
    assert calc.metrics["revenue_series_primary"] == "as_reported"
    assert calc.metrics["comparable_companion_present"] is False
