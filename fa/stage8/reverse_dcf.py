"""Reverse DCF — first-class embedded expectations (Plan §0.E).

Smallest useful solve: implied FCFF/revenue growth path holding margins /
reinvestment / discount-class / terminal policy approximately fixed.
Expectations vocab (LOCKED):
  conservative | plausible | demanding | heroic | incoherent_with_evidence | unknown
Never cheap/expensive. Never BUY/SELL.
"""
from __future__ import annotations

from typing import Any

from .dcf import (
    RESEARCH_CANDIDATE_DEFAULT_HORIZON_YEARS,
    RESEARCH_CANDIDATE_DISCOUNT_BY_CLASS,
    RESEARCH_CANDIDATE_TERMINAL_G,
    _pv_annuity_growth,
    _terminal_perpetuity,
)
from .calc import equity_iv_from_enterprise, per_share

EXPECTATIONS_VOCAB = (
    "conservative",
    "plausible",
    "demanding",
    "heroic",
    "incoherent_with_evidence",
    "unknown",
)

# RESEARCH_CANDIDATE calibration bands for implied growth → vocab (NOT gates / NOT cheap-expensive)
_RESEARCH_IMPLIED_GROWTH_BANDS = {
    "conservative": (-1.0, 0.02),
    "plausible": (0.02, 0.07),
    "demanding": (0.07, 0.12),
    "heroic": (0.12, 0.25),
}


def _enterprise_value_at_growth(
    *,
    base_fcff: float,
    growth: float,
    discount: float,
    years: int,
    terminal_g: float,
) -> float | None:
    pv_explicit, cfs = _pv_annuity_growth(base_fcff, growth, discount, years)
    final = cfs[-1] if cfs else base_fcff
    term = _terminal_perpetuity(final, g=terminal_g, discount=discount, years=years)
    if term.get("pv_terminal") is None:
        return None
    return pv_explicit + float(term["pv_terminal"])


def solve_implied_fcff_growth(
    *,
    target_enterprise_value: float | None,
    base_fcff: float | None,
    discount_class: str = "standard_opco",
    horizon_years: int | None = None,
    terminal_g: float | None = None,
    growth_low: float = -0.05,
    growth_high: float = 0.30,
    tol_rel: float = 0.005,
    max_iter: int = 60,
) -> dict[str, Any]:
    """Binary-search implied constant FCFF growth that matches target EV (smallest solve)."""
    if target_enterprise_value is None or target_enterprise_value <= 0:
        return {
            "constructible": False,
            "why": "Target enterprise value missing/non-positive — reverse DCF unknown",
            "implied_fcff_growth": None,
        }
    if base_fcff is None or base_fcff <= 0:
        return {
            "constructible": False,
            "why": "Base FCFF missing/non-positive — reverse DCF unknown",
            "implied_fcff_growth": None,
        }

    years = horizon_years or RESEARCH_CANDIDATE_DEFAULT_HORIZON_YEARS
    r = RESEARCH_CANDIDATE_DISCOUNT_BY_CLASS.get(
        discount_class, RESEARCH_CANDIDATE_DISCOUNT_BY_CLASS["standard_opco"]
    )
    g_term = terminal_g if terminal_g is not None else RESEARCH_CANDIDATE_TERMINAL_G["central"]
    if r <= g_term:
        return {
            "constructible": False,
            "why": f"Discount {r} <= terminal g {g_term} — reverse DCF undefined",
            "implied_fcff_growth": None,
        }

    lo, hi = growth_low, growth_high
    v_lo = _enterprise_value_at_growth(
        base_fcff=base_fcff, growth=lo, discount=r, years=years, terminal_g=g_term
    )
    v_hi = _enterprise_value_at_growth(
        base_fcff=base_fcff, growth=hi, discount=r, years=years, terminal_g=g_term
    )
    if v_lo is None or v_hi is None:
        return {
            "constructible": False,
            "why": "Terminal undefined on search bounds",
            "implied_fcff_growth": None,
        }

    # Outside bounds — boundary is NOT a solved point estimate
    search_range = {"growth_low": lo, "growth_high": hi}
    if target_enterprise_value < v_lo:
        residual = float(target_enterprise_value) - float(v_lo)
        residual_rel = residual / float(target_enterprise_value) if target_enterprise_value else None
        return {
            "constructible": True,
            "implied_fcff_growth": None,
            "implied_fcff_growth_lower_bound": None,
            "implied_fcff_growth_upper_bound": lo,
            "bound": "below_search_low",
            "solve_status": "unresolved_below_search_range",
            "lower_bound_only": False,
            "upper_bound_only": True,
            "root_found": False,
            "search_range": search_range,
            "variable_solved": "constant_fcff_growth",
            "discount_rate": r,
            "terminal_g": g_term,
            "horizon_years": years,
            "matched_ev": v_lo,
            "target_ev": target_enterprise_value,
            "price_value_residual_ev": residual,
            "price_value_residual_rel": residual_rel,
            "note": (
                f"Implied FCFF growth < {lo:.0%} (search floor) — upper_bound_only; "
                "NOT a solved point estimate; expectations lean conservative/low"
            ),
            "numerics_tag": "RESEARCH_CANDIDATE_NOT_LOCKED",
        }
    if target_enterprise_value > v_hi:
        residual = float(target_enterprise_value) - float(v_hi)
        residual_rel = residual / float(target_enterprise_value) if target_enterprise_value else None
        return {
            "constructible": True,
            "implied_fcff_growth": None,
            "implied_fcff_growth_lower_bound": hi,
            "implied_fcff_growth_upper_bound": None,
            "bound": "above_search_high",
            "solve_status": "unresolved_above_search_range",
            "lower_bound_only": True,
            "upper_bound_only": False,
            "root_found": False,
            "search_range": search_range,
            "variable_solved": "constant_fcff_growth",
            "discount_rate": r,
            "terminal_g": g_term,
            "horizon_years": years,
            "matched_ev": v_hi,
            "target_ev": target_enterprise_value,
            "price_value_residual_ev": residual,
            "price_value_residual_rel": residual_rel,
            "note": (
                f"Implied FCFF growth > {hi:.0%} (search ceiling) — lower_bound_only; "
                "NOT a solved point estimate; expectations lean heroic/extreme"
            ),
            "numerics_tag": "RESEARCH_CANDIDATE_NOT_LOCKED",
        }

    mid = 0.0
    v_mid = None
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        v_mid = _enterprise_value_at_growth(
            base_fcff=base_fcff, growth=mid, discount=r, years=years, terminal_g=g_term
        )
        if v_mid is None:
            return {
                "constructible": False,
                "why": "Terminal undefined mid-search",
                "implied_fcff_growth": None,
            }
        if abs(v_mid - target_enterprise_value) / target_enterprise_value <= tol_rel:
            break
        if v_mid < target_enterprise_value:
            lo = mid
        else:
            hi = mid

    residual = (
        float(target_enterprise_value) - float(v_mid) if v_mid is not None else None
    )
    residual_rel = (
        residual / float(target_enterprise_value)
        if residual is not None and target_enterprise_value
        else None
    )
    return {
        "constructible": True,
        "implied_fcff_growth": mid,
        "implied_fcff_growth_lower_bound": None,
        "implied_fcff_growth_upper_bound": None,
        "bound": "interior",
        "solve_status": "root_found",
        "lower_bound_only": False,
        "upper_bound_only": False,
        "root_found": True,
        "search_range": search_range,
        "variable_solved": "constant_fcff_growth",
        "discount_rate": r,
        "terminal_g": g_term,
        "horizon_years": years,
        "matched_ev": v_mid,
        "target_ev": target_enterprise_value,
        "price_value_residual_ev": residual,
        "price_value_residual_rel": residual_rel,
        "solve": "binary_search_constant_fcff_growth",
        "held_fixed": [
            "discount_class_central_rate",
            "terminal_g_central",
            "horizon",
            "base_fcff",
        ],
        "numerics_tag": "RESEARCH_CANDIDATE_NOT_LOCKED",
    }


def classify_expectations(
    implied_growth: float | None,
    *,
    stage4_growth_hint: float | None = None,
    constructible: bool = True,
    a7: bool = False,
    s6_opacity: bool = False,
    solve_status: str | None = None,
    lower_bound_only: bool = False,
    upper_bound_only: bool = False,
    bound_growth: float | None = None,
) -> tuple[str, str]:
    """
    Map implied growth → locked expectations vocab.
    ≠ cheap/expensive. Demanding can be fair if S4–6 duration supports it.
    A7 + acquisition-return opacity → uncertainty / REVIEW lean, not incoherent.
    incoherent_with_evidence only on actual contradictory prior-stage evidence.
    Boundary solves (ceiling/floor) must NOT be phrased as point estimates.
    """
    # Boundary / unresolved above search ceiling — still classifiable from bound
    if constructible and (lower_bound_only or solve_status == "unresolved_above_search_range"):
        bg = float(bound_growth) if bound_growth is not None else (
            float(implied_growth) if implied_growth is not None else None
        )
        if bg is None:
            return "unknown", "Reverse DCF ceiling unresolved without bound — expectations=unknown"
        label = "heroic"
        why = (
            f"Implied FCFF growth > {bg:.1%} (search-ceiling lower_bound_only; "
            f"unresolved_above_search_range — NOT a solved point estimate) "
            f"→ expectations={label} (vocab≠cheap/expensive)"
        )
        # fall through to opacity / contradiction checks via g=bg
        g = bg
    elif constructible and (upper_bound_only or solve_status == "unresolved_below_search_range"):
        bg = float(bound_growth) if bound_growth is not None else (
            float(implied_growth) if implied_growth is not None else None
        )
        if bg is None:
            return "unknown", "Reverse DCF floor unresolved without bound — expectations=unknown"
        label = "conservative"
        why = (
            f"Implied FCFF growth < {bg:.1%} (search-floor upper_bound_only; "
            f"unresolved_below_search_range — NOT a solved point estimate) "
            f"→ expectations={label} (vocab≠cheap/expensive)"
        )
        g = bg
    elif not constructible or implied_growth is None:
        return "unknown", "Reverse DCF unconstructible — expectations=unknown"
    else:
        g = float(implied_growth)
        # Heroic ceiling breach
        if g >= _RESEARCH_IMPLIED_GROWTH_BANDS["heroic"][1]:
            label = "heroic"
        elif g >= _RESEARCH_IMPLIED_GROWTH_BANDS["heroic"][0]:
            label = "heroic"
        elif g >= _RESEARCH_IMPLIED_GROWTH_BANDS["demanding"][0]:
            label = "demanding"
        elif g >= _RESEARCH_IMPLIED_GROWTH_BANDS["plausible"][0]:
            label = "plausible"
        else:
            label = "conservative"

        why = f"Implied FCFF growth≈{g:.1%} → expectations={label} (vocab≠cheap/expensive)"

    # Opacity / A7 widens uncertainty and REVIEW lean — NOT evidence contradiction.
    # incoherent_with_evidence requires actual contradictory prior-stage evidence
    # (e.g. Stage4 growth hint << implied heroic). A7 + S6_H7_ACQ_RETURN_OPACITY alone
    # must NOT force incoherent_with_evidence.
    if label in {"heroic", "demanding"} and a7 and s6_opacity:
        why += (
            "; A7 + S6 acquisition-return opacity — uncertainty↑ / REVIEW lean "
            "(opacity ≠ evidence contradiction; not incoherent_with_evidence)"
        )

    # Real contradiction only: Stage4 growth hint << implied heroic band
    if stage4_growth_hint is not None and label == "heroic":
        if stage4_growth_hint < 0.05:
            return (
                "incoherent_with_evidence",
                why
                + f"; Stage4 growth hint≈{stage4_growth_hint:.1%} << implied — incoherent_with_evidence",
            )

    if label == "demanding":
        why += "; demanding can be fair if Stage 4–6 duration supports it (FP-V15: not auto-SELL)"
    return label, why


def run_reverse_dcf(
    *,
    market_bridge: dict[str, Any] | None,
    base_fcff: float | None,
    discount_class: str,
    primary_archetype: str | None = None,
    s6_flags: list[str] | None = None,
    stage4_revenue_cagr: float | None = None,
) -> dict[str, Any]:
    """First-class reverse DCF package."""
    bridge = market_bridge or {}
    target_ev = bridge.get("enterprise_value")
    solve = solve_implied_fcff_growth(
        target_enterprise_value=target_ev,
        base_fcff=base_fcff,
        discount_class=discount_class,
    )
    a7 = primary_archetype == "A7"
    s6_opacity = "S6_H7_ACQ_RETURN_OPACITY" in (s6_flags or [])
    bound_g = None
    if solve.get("lower_bound_only"):
        bound_g = solve.get("implied_fcff_growth_lower_bound")
    elif solve.get("upper_bound_only"):
        bound_g = solve.get("implied_fcff_growth_upper_bound")
    label, why = classify_expectations(
        solve.get("implied_fcff_growth"),
        stage4_growth_hint=stage4_revenue_cagr,
        constructible=bool(solve.get("constructible")),
        a7=a7,
        s6_opacity=s6_opacity,
        solve_status=solve.get("solve_status"),
        lower_bound_only=bool(solve.get("lower_bound_only")),
        upper_bound_only=bool(solve.get("upper_bound_only")),
        bound_growth=bound_g,
    )

    # Also express equity-implied per-share check (informational)
    eq_mkt = bridge.get("equity_market_cap")
    shares = bridge.get("shares_used")
    mkt_ps = per_share(eq_mkt, shares) if eq_mkt and shares else None

    return {
        "constructible": bool(solve.get("constructible")),
        "solve": solve,
        "expectations_label": label,
        "expectations_why": why,
        "market_price_per_share": mkt_ps,
        "target_enterprise_value": target_ev,
        "base_fcff": base_fcff,
        "vocab_locked": list(EXPECTATIONS_VOCAB),
        "never_cheap_expensive": True,
        "never_buy_sell": True,
        "a7_no_free_organic_acq_growth": a7,
        "first_class": True,
    }
