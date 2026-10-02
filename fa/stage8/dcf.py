"""Minimal FCFF DCF + dual-terminal CROSS-CHECKS (Plan §0.D/G).

Scenarios: conservative | central | optimistic.
Default ~5Y explicit + terminal. Selective extend hook (not rigid 10Y engine).
Discount class + sensitivity — numeric defaults = RESEARCH_CANDIDATE / NOT_LOCKED.
NEVER average terminals. NEVER silent override.
Companions (OE/FCFE) labeled, not second scored truth.
"""
from __future__ import annotations

from typing import Any

from .calc import equity_iv_from_enterprise, per_share

# ---------------------------------------------------------------------------
# RESEARCH_CANDIDATE / NOT_LOCKED numeric defaults — architecture locked; values not gates
# ---------------------------------------------------------------------------
RESEARCH_CANDIDATE_DISCOUNT_BY_CLASS = {
    "low_uncertainty_franchise": 0.08,
    "standard_opco": 0.10,
    "high_uncertainty": 0.12,
    "cyclical_elevated": 0.13,
}
RESEARCH_CANDIDATE_SENSITIVITY_SPREAD = 0.02  # ±200 bps around class rate
RESEARCH_CANDIDATE_DEFAULT_HORIZON_YEARS = 5
RESEARCH_CANDIDATE_TERMINAL_G = {
    "conservative": 0.02,
    "central": 0.025,
    "optimistic": 0.03,
}
# Honest name: multiple is applied to final-year FCFF (EV/FCFF-like), NOT EBITDA.
# Prior alias EXIT_EBITDA_MULTIPLE was a naming defect (multiple≠EBITDA basis).
RESEARCH_CANDIDATE_EXIT_FCFF_MULTIPLE = {
    "conservative": 10.0,
    "central": 12.0,
    "optimistic": 14.0,
}
# Backward-compatible alias — do not use for new code; values identical.
RESEARCH_CANDIDATE_EXIT_EBITDA_MULTIPLE = RESEARCH_CANDIDATE_EXIT_FCFF_MULTIPLE
# Scenario FCFF growth paths (annual) — soft interpretive; NOT production gates
RESEARCH_CANDIDATE_FCFF_GROWTH = {
    "conservative": -0.02,
    "central": 0.04,
    "optimistic": 0.08,
}
# A7: haircut central growth when acq opacity — still not a gate
RESEARCH_CANDIDATE_A7_GROWTH_HAIRCUT = 0.02

SCENARIOS = ("conservative", "central", "optimistic")


def choose_discount_class(
    *,
    primary_archetype: str | None,
    uncertainty_drivers: list[str] | None = None,
    normalization_uncertainty: str | None = None,
) -> str:
    """Qualitative required-return class — not a quality score / not CAPM."""
    drivers = set(uncertainty_drivers or [])
    if primary_archetype in {"A8", "A9"}:
        return "cyclical_elevated"
    if normalization_uncertainty in {"extreme", "unanalyzable"} or "no_cash_base" in drivers:
        return "high_uncertainty"
    if primary_archetype == "A7" and (
        "s6_acq_return_opacity" in drivers or "recurring_ma_opacity" in drivers
    ):
        return "high_uncertainty"
    if primary_archetype in {"A1", "A3"} and normalization_uncertainty == "low":
        return "low_uncertainty_franchise"
    if primary_archetype in {"A10", "A11"}:
        return "high_uncertainty"
    return "standard_opco"


def _pv_annuity_growth(
    base_fcff: float,
    growth: float,
    discount: float,
    years: int,
) -> tuple[float, list[float]]:
    """PV of explicit forecast FCFF path."""
    cashflows = []
    pv = 0.0
    f = base_fcff
    for t in range(1, years + 1):
        f = f * (1.0 + growth)
        cashflows.append(f)
        pv += f / ((1.0 + discount) ** t)
    return pv, cashflows


def _terminal_perpetuity(
    final_fcff: float,
    *,
    g: float,
    discount: float,
    years: int,
) -> dict[str, Any]:
    if discount <= g:
        return {
            "method": "perpetual_growth",
            "terminal_value": None,
            "pv_terminal": None,
            "g": g,
            "null_reason": f"discount={discount} <= g={g} — perpetuity undefined",
        }
    tv = final_fcff * (1.0 + g) / (discount - g)
    pv = tv / ((1.0 + discount) ** years)
    return {
        "method": "perpetual_growth",
        "terminal_value": tv,
        "pv_terminal": pv,
        "g": g,
        "null_reason": None,
    }


def _terminal_exit_multiple(
    final_fcff: float,
    *,
    multiple: float,
    discount: float,
    years: int,
) -> dict[str, Any]:
    """Exit-multiple on final-year FCFF (EV/FCFF-like CROSS-CHECK).

    Vocabulary: EXIT_FCFF_MULTIPLE — NOT EV/EBITDA / NOT EV/EBIT.
    Formula: TV = final_year_FCFF × exit_fcff_multiple; PV = TV / (1+r)^N.
    """
    tv = final_fcff * multiple
    pv = tv / ((1.0 + discount) ** years)
    return {
        "method": "exit_multiple",
        "terminal_basis": "FCFF",
        "terminal_basis_vocabulary": "EXIT_FCFF_MULTIPLE",
        "formula": "TV = final_year_FCFF * exit_fcff_multiple; PV = TV / (1+r)^N",
        "not_ebitda": True,
        "not_ebit": True,
        "terminal_value": tv,
        "pv_terminal": pv,
        "exit_fcff_multiple": multiple,
        "exit_multiple_on_fcff_proxy": multiple,  # compat alias
        "note": (
            "Exit multiple applied to final-year FCFF (EXIT_FCFF_MULTIPLE / EV/FCFF-like) "
            "as CROSS-CHECK — NOT EV/EBITDA; not silent peer-median circularity (FP-V17 watch)"
        ),
        "null_reason": None,
    }


def run_fcff_scenarios(
    *,
    base_fcff: float | None,
    discount_class: str,
    primary_archetype: str | None = None,
    horizon_years: int | None = None,
    selective_extend: bool = False,
    bridge: dict[str, Any] | None = None,
    growth_overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    FCFF default DCF → enterprise → equity via bridge.
    Dual terminal CROSS-CHECKS per scenario — never averaged.
    """
    if base_fcff is None or base_fcff <= 0:
        return {
            "applicable": False,
            "why": "FCFF/base cash not meaningful or non-positive — DCF NOT_APPLICABLE",
            "scenarios": {},
            "dual_terminal_policy": "cross_checks_never_average",
            "no_terminal_average": True,
        }

    years = horizon_years or RESEARCH_CANDIDATE_DEFAULT_HORIZON_YEARS
    if selective_extend:
        years = max(years, 7)  # selective extend hook — still not a 10Y line-item engine

    r_central = RESEARCH_CANDIDATE_DISCOUNT_BY_CLASS.get(
        discount_class, RESEARCH_CANDIDATE_DISCOUNT_BY_CLASS["standard_opco"]
    )
    spread = RESEARCH_CANDIDATE_SENSITIVITY_SPREAD
    discount_band = {
        "class": discount_class,
        "central_rate": r_central,
        "low_rate": r_central - spread,
        "high_rate": r_central + spread,
        "note": "RESEARCH_CANDIDATE / NOT_LOCKED numeric defaults — sensitivity across band; not CAPM",
    }

    growth = dict(RESEARCH_CANDIDATE_FCFF_GROWTH)
    if primary_archetype == "A7":
        # Do not treat acquired growth as free organic — haircut central/opt paths
        growth["central"] = max(-0.05, growth["central"] - RESEARCH_CANDIDATE_A7_GROWTH_HAIRCUT)
        growth["optimistic"] = max(0.0, growth["optimistic"] - RESEARCH_CANDIDATE_A7_GROWTH_HAIRCUT)
        growth["conservative"] = min(growth["conservative"], -0.03)
    if growth_overrides:
        growth.update(growth_overrides)

    bridge = bridge or {}
    debt = bridge.get("gross_debt")
    cash = bridge.get("cash_and_equivalents")
    sti = bridge.get("sti_subtracted")
    lease_add = bridge.get("lease_add_to_debt") or 0.0
    shares = bridge.get("shares_used")

    scenarios: dict[str, Any] = {}
    equity_per_share_by_method: dict[str, dict[str, float | None]] = {
        "perpetual_growth": {},
        "exit_multiple": {},
    }

    for name in SCENARIOS:
        g_path = growth[name]
        # Map scenario to discount within band (cons→high rate, opt→low rate)
        if name == "conservative":
            r = discount_band["high_rate"]
        elif name == "optimistic":
            r = discount_band["low_rate"]
        else:
            r = discount_band["central_rate"]

        pv_explicit, cfs = _pv_annuity_growth(base_fcff, g_path, r, years)
        final_fcff = cfs[-1] if cfs else base_fcff

        term_g = RESEARCH_CANDIDATE_TERMINAL_G[name]
        # Guard: g must stay below economy-ish; flag if optimistic g high
        term_perp = _terminal_perpetuity(final_fcff, g=term_g, discount=r, years=years)
        mult = RESEARCH_CANDIDATE_EXIT_FCFF_MULTIPLE[name]
        term_exit = _terminal_exit_multiple(final_fcff, multiple=mult, discount=r, years=years)

        # Enterprise IV per terminal method — CROSS-CHECKS, not averaged
        ent_perp = None
        ent_exit = None
        if term_perp.get("pv_terminal") is not None:
            ent_perp = pv_explicit + float(term_perp["pv_terminal"])
        if term_exit.get("pv_terminal") is not None:
            ent_exit = pv_explicit + float(term_exit["pv_terminal"])

        eq_perp = equity_iv_from_enterprise(
            ent_perp, gross_debt=debt, cash=cash, sti=sti, lease_add=lease_add
        )
        eq_exit = equity_iv_from_enterprise(
            ent_exit, gross_debt=debt, cash=cash, sti=sti, lease_add=lease_add
        )
        ps_perp = per_share(eq_perp, shares)
        ps_exit = per_share(eq_exit, shares)
        equity_per_share_by_method["perpetual_growth"][name] = ps_perp
        equity_per_share_by_method["exit_multiple"][name] = ps_exit

        # Terminal dominance flag (share of enterprise PV)
        def _dom(ent, pv_term):
            if ent is None or not ent or pv_term is None:
                return None
            return float(pv_term) / float(ent)

        scenarios[name] = {
            "fcff_growth": g_path,
            "discount_rate": r,
            "horizon_years": years,
            "pv_explicit_fcff": pv_explicit,
            "final_year_fcff": final_fcff,
            "terminal_perpetual_growth": term_perp,
            "terminal_exit_multiple": term_exit,
            "enterprise_iv_perpetual": ent_perp,
            "enterprise_iv_exit": ent_exit,
            "equity_iv_perpetual": eq_perp,
            "equity_iv_exit": eq_exit,
            "equity_iv_per_share_perpetual": ps_perp,
            "equity_iv_per_share_exit": ps_exit,
            # Explicit: no average of dual terminals
            "averaged_terminal_iv": None,
            "no_terminal_average": True,
            "terminal_dominance_perpetual": _dom(ent_perp, term_perp.get("pv_terminal")),
            "terminal_dominance_exit": _dom(ent_exit, term_exit.get("pv_terminal")),
        }

    # Range from CROSS-CHECK methods separately (never blended into one truth number)
    def _range(method_key: str) -> dict[str, Any]:
        vals = [
            equity_per_share_by_method[method_key].get(s)
            for s in SCENARIOS
            if equity_per_share_by_method[method_key].get(s) is not None
        ]
        if not vals:
            return {"low": None, "high": None, "central": None}
        return {
            "low": min(vals),
            "high": max(vals),
            "central": equity_per_share_by_method[method_key].get("central"),
            "unit": "equity_iv_per_share",
        }

    perp_range = _range("perpetual_growth")
    exit_range = _range("exit_multiple")

    # Disagreement between central terminals
    c_perp = equity_per_share_by_method["perpetual_growth"].get("central")
    c_exit = equity_per_share_by_method["exit_multiple"].get("central")
    disagreement = None
    disagreement_large = False
    if c_perp and c_exit and c_perp != 0:
        disagreement = abs(c_perp - c_exit) / abs(c_perp)
        # Contextual lean — RESEARCH_CANDIDATE 25% relative gap; not a hard gate
        disagreement_large = disagreement > 0.25

    dual_note = (
        "Dual terminal CROSS-CHECKS produced (perpetual-growth + exit-multiple). "
        "NEVER averaged; NEVER silent override. Disagreement elevates VA8 uncertainty."
    )
    if disagreement is not None:
        dual_note += f" Central relative disagreement≈{disagreement:.1%}."
        if disagreement_large:
            dual_note += " Large disagreement — REVIEW_REQUIRED candidacy (contextual)."

    companions = {
        "owner_earnings": {
            "status": "labeled_companion",
            "note": "OE companion available via normalization when CapEx known — not second scored truth",
        },
        "fcfe": {
            "status": "not_primary",
            "note": "FCFE companion out of primary path in v1 thin DCF — FCFF default",
        },
    }

    return {
        "applicable": True,
        "method": "FCFF",
        "base_fcff": base_fcff,
        "horizon_years": years,
        "selective_extend": selective_extend,
        "discount_band": discount_band,
        "growth_paths": growth,
        "growth_path_provenance": "RESEARCH_CANDIDATE_DEFAULT",
        "growth_note": (
            "RESEARCH_CANDIDATE growth paths; A7 haircut applied when archetype=A7 "
            "(no free-organic acquired growth)"
            if primary_archetype == "A7"
            else "RESEARCH_CANDIDATE growth paths — grounded loosely in S3–6 scale, not oversized forecast engine"
        ),
        "exit_multiple_basis": {
            "metric": "FCFF",
            "vocabulary": "EXIT_FCFF_MULTIPLE",
            "formula": "TV = final_year_FCFF * exit_fcff_multiple",
            "not_ebitda": True,
            "multiples_by_scenario": dict(RESEARCH_CANDIDATE_EXIT_FCFF_MULTIPLE),
            "provenance": "RESEARCH_CANDIDATE_DEFAULT",
        },
        "terminal_g_by_scenario": dict(RESEARCH_CANDIDATE_TERMINAL_G),
        "horizon_years_default": RESEARCH_CANDIDATE_DEFAULT_HORIZON_YEARS,
        "assumption_provenance": {
            "fcff_growth": "RESEARCH_CANDIDATE_DEFAULT",
            "discount_rates": "RESEARCH_CANDIDATE_DEFAULT (class-mapped; not CAPM)",
            "terminal_g": "RESEARCH_CANDIDATE_DEFAULT",
            "exit_fcff_multiple": "RESEARCH_CANDIDATE_DEFAULT",
            "horizon": "RESEARCH_CANDIDATE_DEFAULT",
            "op_margin": "NOT_MODELED_SEPARATELY (embedded in FCFF base)",
            "fcf_margin": "NOT_MODELED_SEPARATELY (embedded in FCFF base)",
            "reinvestment": "NOT_MODELED_SEPARATELY (embedded in FCFF path)",
            "rev_growth": "NOT_MODELED_SEPARATELY (FCFF growth is the solved/path variable)",
        },
        "scenarios": scenarios,
        "iv_range_perpetual_growth": perp_range,
        "iv_range_exit_multiple": exit_range,
        # Combined descriptive envelope (min of lows, max of highs) — NOT an averaged fair value
        "iv_range_envelope_descriptive": {
            "low": min(
                x
                for x in (perp_range.get("low"), exit_range.get("low"))
                if x is not None
            )
            if any(x is not None for x in (perp_range.get("low"), exit_range.get("low")))
            else None,
            "high": max(
                x
                for x in (perp_range.get("high"), exit_range.get("high"))
                if x is not None
            )
            if any(x is not None for x in (perp_range.get("high"), exit_range.get("high")))
            else None,
            "note": (
                "Descriptive envelope across CROSS-CHECK methods + scenarios — "
                "NOT a mechanical average fair value; methods remain separate exhibits"
            ),
        },
        "terminal_disagreement_central_rel": disagreement,
        "terminal_disagreement_large": disagreement_large,
        "dual_terminal_note": dual_note,
        "no_terminal_average": True,
        "no_method_average": True,
        "companions": companions,
        "numerics_tag": "RESEARCH_CANDIDATE_NOT_LOCKED",
    }
