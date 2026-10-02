"""Stage 4 archetype adaptation — ONE PRIMARY + SECONDARY_TRAITS + ~1–3 drivers.

No company hardcoding. No score blend / multi-primary. Routine automated;
material ambiguity → REVIEW_REQUIRED classification path.
"""
from __future__ import annotations

from typing import Any

from ..models import ArchetypeAdaptation
from .questions import PRIMARY_ARCHETYPES

# Model-specific dashboard slot examples (Plan §11B.4) — NOT_APPLICABLE when unused
_MODEL_SLOTS: dict[str, str] = {
    "A1": "volume_concentrate_unit_proxy",
    "A2": "arr_nrr_or_deferred_rpo",
    "A3": "payments_volume_vs_yield",
    "A4": "cycle_normalized_volume_asp_backlog",
    "A5": "backlog_book_to_bill",
    "A6": "comps_traffic_ticket",
    "A7": "organic_bridge_quality",
    "A8": "price_vs_volume_split",
    "A9": "load_occupancy_capacity_yield",
    "A10": "volume_capacity_plus_platform_driver",
    "A11": "explicit_or_not_applicable",
}

# Keyword → archetype signals (generic; no ticker hardcoding)
_ARCHETYPE_SIGNALS: list[tuple[str, list[str], list[str]]] = [
    # primary_id, positive keywords, secondary trait tags when hit
    (
        "A2",
        [
            "saas",
            "software as a service",
            "subscription software",
            "arr ",
            "annual recurring revenue",
            "net revenue retention",
            "cloud software",
            "recurring software",
        ],
        ["recurring_revenue"],
    ),
    (
        "A3",
        [
            "payment network",
            "payments platform",
            "card network",
            "transaction volume",
            "take rate",
            "take-rate",
            "payment processing",
            "merchant acquiring",
            "payment services",
            "payments volume",
            "payment volume",
            "electronic payments",
            "consumer payments",
            "card transactions",
            "money movement",
            "payments network",
        ],
        ["network_effects"],
    ),
    (
        "A4",
        [
            "semiconductor",
            "gpu",
            "foundry",
            "wafer",
            "chip design",
            "fabless",
            "asic",
            "datacenter gpu",
        ],
        ["technology_platform", "cyclical"],
    ),
    (
        "A9",
        [
            "cruise",
            "airline",
            "hotel occupancy",
            "load factor",
            "passenger capacity",
            "available seat",
            "room nights",
        ],
        ["capacity_cyclical"],
    ),
    (
        "A8",
        [
            "commodity",
            "iron ore",
            "copper mining",
            "oil and gas exploration",
            "bulk commodity",
            "spot price",
            "mining and metals",
        ],
        ["commodity_cyclical"],
    ),
    (
        "A6",
        [
            "same-store sales",
            "comparable store",
            "retail stores",
            "store footprint",
            "square footage",
            "e-commerce retail",
        ],
        ["retail_distribution"],
    ),
    (
        "A5",
        [
            "capital equipment",
            "industrial manufacturer",
            "book-to-bill",
            "heavy machinery",
            "factory automation",
            "backlog of orders",
        ],
        ["capital_intensive"],
    ),
    (
        "A7",
        [
            "bolt-on acquisition",
            "acquisitive compounder",
            "roll-up",
            "serial acquirer",
            "acquisition strategy",
            "inorganic growth strategy",
            "cash paid for acquisitions",
            "acquired businesses",
            "completed the acquisition",
            "business combinations",
        ],
        ["acquisitive"],
    ),
    (
        "A1",
        [
            "branded beverage",
            "consumer brand",
            "concentrate",
            "sparkling soft drink",
            "packaged food brand",
            "trademark beverage",
            "bottling system",
            "household brand",
        ],
        ["mature_franchise"],
    ),
    (
        "A10",
        [
            "electric vehicle manufacturer",
            "energy generation and storage",
            "autonomous driving platform",
            "hardware and software platform",
            "manufacturer and technology platform",
        ],
        ["hybrid_tech_mfr"],
    ),
]


def _text_blob(
    thesis_summary: str | None,
    business_notes: str | None,
    semantic_text: str | None,
    extra: str | None = None,
) -> str:
    parts = [thesis_summary or "", business_notes or "", semantic_text or "", extra or ""]
    return " ".join(parts).lower()


def _score_archetypes(blob: str) -> tuple[dict[str, int], dict[str, list[str]]]:
    scores: dict[str, int] = {k: 0 for k in PRIMARY_ARCHETYPES}
    trait_hits: dict[str, list[str]] = {k: [] for k in PRIMARY_ARCHETYPES}
    for aid, kws, traits in _ARCHETYPE_SIGNALS:
        for kw in kws:
            if kw in blob:
                scores[aid] += 1
                for t in traits:
                    if t not in trait_hits[aid]:
                        trait_hits[aid].append(t)
    return scores, trait_hits


def _drivers_for(primary: str, traits: list[str], blob: str) -> list[dict[str, Any]]:
    """Select ~1–3 evidence-backed model-specific drivers."""
    drivers: list[dict[str, Any]] = []
    slot = _MODEL_SLOTS.get(primary)

    catalog = {
        "A1": [
            ("unit_volume_proxy", "volume / concentrate / unit proxy"),
            ("pricing_mix", "pricing and mix durability"),
            ("geo_whitespace", "geo / occasion white space"),
        ],
        "A2": [
            ("arr_nrr", "ARR/NRR or deferred/RPO (source-semantic)"),
            ("retention", "retention / expansion quality"),
            ("sbc_dilution", "SBC / dilution vs growth"),
        ],
        "A3": [
            ("payments_volume", "payments / transaction volume"),
            ("yield_take_rate", "yield / take-rate optics"),
            ("network_coverage", "network coverage / geo"),
        ],
        "A4": [
            ("cycle_position", "cycle vs share honesty"),
            ("asp_volume", "ASP vs volume split"),
            ("backlog_quality", "backlog / allocation quality"),
        ],
        "A5": [
            ("backlog", "backlog / book-to-bill"),
            ("capacity", "capacity utilization"),
            ("product_line_ma", "M&A product-line honesty"),
        ],
        "A6": [
            ("comps", "comps / traffic / ticket"),
            ("footage", "footage vs density"),
            ("cannibalization", "cannibalization awareness"),
        ],
        "A7": [
            ("organic_bridge", "organic bridge quality (mandatory emphasis)"),
            ("bolt_on_fit", "bolt-on franchise fit"),
            ("roll_up_eps", "roll-up EPS optics watch"),
        ],
        "A8": [
            ("price_vs_volume", "price vs volume split"),
            ("cycle_window", "cycle window honesty"),
            ("cost_curve", "cost-curve / volume resilience"),
        ],
        "A9": [
            ("occupancy_load", "load factor / occupancy"),
            ("capacity_yield", "capacity vs yield"),
            ("rebound_base", "rebound / base-effect honesty"),
        ],
        "A10": [
            ("volume_capacity", "volume / capacity path"),
            ("platform_driver", "platform / software adjacency"),
            ("thesis_model_fit", "thesis vs observed model fit"),
        ],
        "A11": [
            ("explicit_driver", "explicitly chosen driver"),
        ],
    }
    candidates = catalog.get(primary, catalog["A11"])
    for key, label in candidates[:3]:
        evidence = []
        # lightweight evidence presence from blob
        tokens = key.replace("_", " ").split()
        if any(t in blob for t in tokens if len(t) > 3):
            evidence.append(f"text hit near '{key}'")
        if traits:
            evidence.append(f"traits={traits}")
        drivers.append(
            {
                "id": key,
                "label": label,
                "evidence": evidence or ["archetype-default slot; confirm with disclosure"],
                "status": "proposed",
            }
        )
    return drivers[:3]


def propose_archetype(
    *,
    thesis_summary: str | None = None,
    business_notes: str | None = None,
    semantic_text: str | None = None,
    calc_hints: dict[str, Any] | None = None,
    force_primary: str | None = None,
) -> ArchetypeAdaptation:
    """
    Propose exactly one PRIMARY_ARCHETYPE + traits + drivers.
    No ticker hardcoding. Material ambiguity → classification_path=REVIEW_REQUIRED.
    """
    blob = _text_blob(thesis_summary, business_notes, semantic_text)
    scores, trait_hits = _score_archetypes(blob)

    # Optional calc hints (e.g. high M&A cash → acquisitive trait — not PRIMARY alone)
    hints = calc_hints or {}
    ma_series = hints.get("ma_cash_fy_series") or []
    ma_hits = sum(1 for r in ma_series if (r.get("value") or 0) and abs(r["value"]) > 0)
    if ma_hits >= 2:
        scores["A7"] = scores.get("A7", 0) + 1
        trait_hits.setdefault("A7", []).append("acquisitive")
    # Material M&A cash vs latest revenue → stronger acquisitive signal (still not forced PRIMARY)
    rev_series = hints.get("revenue_fy_series") or []
    latest_rev = None
    for r in reversed(rev_series):
        if r.get("value") is not None:
            latest_rev = abs(float(r["value"]))
            break
    latest_ma = None
    for r in reversed(ma_series):
        if r.get("value") is not None and abs(float(r["value"])) > 0:
            latest_ma = abs(float(r["value"]))
            break
    if latest_rev and latest_ma and latest_ma / latest_rev >= 0.05:
        scores["A7"] = scores.get("A7", 0) + 2
        if "acquisitive" not in trait_hits.setdefault("A7", []):
            trait_hits["A7"].append("acquisitive")

    if force_primary and force_primary in PRIMARY_ARCHETYPES:
        primary = force_primary
        confidence = "HIGH"
        ambiguity = None
        path = "AUTOMATED"
        evidence = [f"force_primary={force_primary} (test/fixture override — not production ticker hardcode)"]
    else:
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_id, best_score = ranked[0]
        second_id, second_score = ranked[1]
        evidence = [f"top_scores={[(k, v) for k, v in ranked[:5] if v > 0]}"]

        if best_score == 0:
            primary = "A11"
            confidence = "LOW"
            ambiguity = "No archetype keyword evidence — default A11 Other/mixed"
            path = "REVIEW_REQUIRED"
        elif best_score == second_score and best_score > 0:
            # Hybrid / ambiguous: pick one PRIMARY, attach other as SECONDARY_TRAIT
            primary = best_id
            confidence = "MEDIUM"
            ambiguity = (
                f"Tied evidence between {best_id} and {second_id} — "
                f"PRIMARY={best_id}; secondary trait from {second_id}; human if material"
            )
            path = "REVIEW_REQUIRED"
        elif second_score > 0 and best_score - second_score <= 1 and best_score >= 2:
            primary = best_id
            confidence = "MEDIUM"
            ambiguity = (
                f"Close call {best_id}({best_score}) vs {second_id}({second_score}) — "
                "hybrid traits attached; escalate only if material"
            )
            # Hybrid routine path stays automated unless scores are very close AND both high
            path = "AUTOMATED" if best_score - second_score >= 1 else "REVIEW_REQUIRED"
        else:
            primary = best_id
            confidence = "HIGH" if best_score >= 2 else "MEDIUM"
            ambiguity = None
            path = "AUTOMATED"

    # Secondary traits from primary + close runners
    secondary: list[str] = list(trait_hits.get(primary) or [])
    ranked_all = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    for aid, sc in ranked_all[1:4]:
        if sc > 0 and aid != primary:
            tag = f"trait_from_{aid}"
            if tag not in secondary:
                secondary.append(tag)
            for t in trait_hits.get(aid) or []:
                if t not in secondary:
                    secondary.append(t)

    # A10 hybrid: if manufacturer+tech signals both present
    if scores.get("A4", 0) > 0 and scores.get("A5", 0) > 0 and primary in {"A4", "A5", "A10"}:
        if "hybrid_tech_mfr" not in secondary:
            secondary.append("hybrid_tech_mfr")
        if primary != "A10" and scores.get("A10", 0) >= 0 and (
            "manufacturer and technology" in blob or "hardware and software" in blob
        ):
            # Prefer A10 as PRIMARY when explicit hybrid language
            primary = "A10"
            path = "AUTOMATED"
            confidence = "MEDIUM"
            ambiguity = (ambiguity or "") + " Hybrid language → PRIMARY A10 + traits"

    drivers = _drivers_for(primary, secondary, blob)
    slot = _MODEL_SLOTS.get(primary)
    slot_status = "set" if slot and primary != "A11" else "NOT_APPLICABLE"
    if primary == "A11":
        slot_status = "NOT_APPLICABLE"
        slot = None

    why = (
        f"PRIMARY={primary} ({PRIMARY_ARCHETYPES[primary]}); "
        f"traits={secondary[:5]}; drivers={[d['id'] for d in drivers]}; "
        f"path={path}; confidence={confidence}"
    )
    if ambiguity:
        why += f"; ambiguity={ambiguity}"

    return ArchetypeAdaptation(
        primary_archetype=primary,
        primary_label=PRIMARY_ARCHETYPES[primary],
        secondary_traits=secondary,
        model_specific_drivers=drivers,
        model_slot=slot,
        model_slot_status=slot_status,
        classification_path=path,
        confidence=confidence,
        ambiguity_notes=ambiguity,
        evidence=evidence,
        provenance="heuristic_text_signals",
        why=why,
    )


def assert_single_primary(adaptation: ArchetypeAdaptation) -> None:
    """Invariant: exactly one PRIMARY from A1–A11."""
    assert adaptation.primary_archetype in PRIMARY_ARCHETYPES
    # No multi-primary field exists by construction
