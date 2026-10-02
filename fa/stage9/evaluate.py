"""Stage 9 evaluate — ER1–ER8 exhibits + NON-TERMINATING outcomes.

No scores/colors/BUY-SELL/numeric risk gates/averaged external-risk score.
No final FA synthesis. No Stage 5 pricing-power redo / no Stage 1 thesis restatement.
ER8: prefer 3–7 material falsifiers — NOT a giant risk register.
"""
from __future__ import annotations

from typing import Any

from ..ids import utc_now
from ..models import (
    ArchetypeAdaptation,
    ERLensResult,
    QuestionAnswer,
    Stage9ProcessOutcome,
    Stage9Report,
    Stage9SemanticReview,
    ThesisBreaker,
)
from .calc import compute_stage9_metrics
from .handoff import build_prior_handoff
from .questions import (
    ER_LENSES,
    EXTERNAL_RISK_EMPHASIS_BY_ARCHETYPE,
    FALSE_POSITIVE_CATALOGUE,
    MUST_QUESTIONS,
    PRIMARY_ARCHETYPES,
    S8_H9_FORWARDABLE,
    S9_HFA_CARRIES,
    SHOULD_QUESTIONS,
    STAGE9_OUTCOMES,
)
from .semantic import (
    excerpt_has_concentration_quant,
    excerpt_has_disruption_substance,
    excerpt_has_geo_footprint,
    excerpt_has_geo_substance,
    excerpt_has_primary_legal,
    semantic_cues_from_review,
    semantic_text_blob,
)


def _soft_commodity_archetype_from_semantic(
    semantic: Stage9SemanticReview | None,
) -> ArchetypeAdaptation | None:
    """Soft A8 when filings show commodity/price-taker cues and no prior Stage 5–8 archetype.

    Generic (no ticker hardcode). LOW confidence / semantic_soft — not a grade; enables
    windfall≠franchise + capital-cycle honesty packaging for commodity UAT pressure.
    """
    if semantic is None:
        return None
    blob = " ".join(
        str(x or "")
        for x in (
            semantic.industry_structure_notes,
            semantic.macro_cycle_notes,
            semantic.concentration_notes,
            semantic.breaker_notes,
            semantic.competition_notes,
            semantic_text_blob(semantic),
        )
    ).lower()
    commodity_hit = any(
        x in blob
        for x in (
            "commodit",
            "iron ore",
            "copper price",
            "price-taker",
            "metals and mining",
            "mining and metals",
        )
    )
    cycle_hit = any(
        x in blob
        for x in (
            "commodity price",
            "commodity demand",
            "capital allocation",
            "capital cycle",
            "price volatility",
        )
    )
    if not (commodity_hit and cycle_hit):
        return None
    pid = "A8"
    return ArchetypeAdaptation(
        primary_archetype=pid,
        primary_label=PRIMARY_ARCHETYPES.get(pid, pid),
        secondary_traits=["commodity_cyclical"],
        model_specific_drivers=[
            {"id": x} for x in EXTERNAL_RISK_EMPHASIS_BY_ARCHETYPE.get(pid, [])
        ],
        model_slot="external_risk",
        model_slot_status="set",
        classification_path="AUTOMATED",
        confidence="LOW",
        provenance="semantic_soft_commodity",
        why=(
            "Soft A8 from commodity/price-cycle semantic cues (no prior Stage 5–8 "
            "archetype) — windfall≠franchise packaging only; not a grade"
        ),
    )


def _adapt_archetype(
    prior: dict[str, Any] | None,
    force_primary: str | None,
    semantic: Stage9SemanticReview | None = None,
) -> ArchetypeAdaptation | None:
    if force_primary:
        pid = force_primary.upper()
        return ArchetypeAdaptation(
            primary_archetype=pid,
            primary_label=PRIMARY_ARCHETYPES.get(pid, pid),
            secondary_traits=[],
            model_specific_drivers=[
                {"id": x} for x in EXTERNAL_RISK_EMPHASIS_BY_ARCHETYPE.get(pid, [])
            ],
            model_slot="external_risk",
            model_slot_status="set",
            classification_path="FORCED",
            confidence="HIGH",
            provenance="force_primary",
            why=f"Forced primary={pid} for Stage 9 packaging test",
        )
    if prior and prior.get("primary_archetype"):
        pid = str(prior["primary_archetype"])
        return ArchetypeAdaptation(
            primary_archetype=pid,
            primary_label=prior.get("primary_label") or PRIMARY_ARCHETYPES.get(pid, pid),
            secondary_traits=list(prior.get("secondary_traits") or []),
            model_specific_drivers=[
                {"id": x} for x in EXTERNAL_RISK_EMPHASIS_BY_ARCHETYPE.get(pid, [])
            ],
            model_slot="external_risk",
            model_slot_status="set",
            classification_path=prior.get("classification_path") or "REUSED",
            confidence=prior.get("confidence") or "MEDIUM",
            provenance=prior.get("provenance") or "prior_reuse",
            why=prior.get("why")
            or f"Reused prior archetype {pid} for external-risk emphasis (not a grade)",
        )
    return _soft_commodity_archetype_from_semantic(semantic)


def _topics(semantic: Stage9SemanticReview | None) -> set[str]:
    if not semantic:
        return set()
    return {f.topic for f in semantic.findings}


def _findings_for(semantic: Stage9SemanticReview | None, *topics: str) -> list:
    if not semantic:
        return []
    want = set(topics)
    return [f for f in semantic.findings if f.topic in want]


def _evidence_kind_for(semantic: Stage9SemanticReview | None, *topics: str) -> str:
    hits = _findings_for(semantic, *topics)
    if not hits:
        return "UNKNOWN"
    # Prefer strongest present label without inventing FACT
    order = ["FACT", "GUIDANCE", "CLAIM", "INFERENCE", "UNKNOWN"]
    kinds = {f.evidence_kind for f in hits}
    for k in order:
        if k in kinds:
            return k
    return "INFERENCE"




def _primary_legal_hits(semantic: Stage9SemanticReview | None, *topics: str) -> list:
    """Findings whose excerpts cite named agency/order/judgment/open case — not RF boilerplate."""
    return [
        f
        for f in _findings_for(semantic, *topics)
        if excerpt_has_primary_legal(f.excerpt)
    ]


def _best_primary_legal_source_tie(semantic: Stage9SemanticReview | None) -> str:
    import re as _re

    hits = _primary_legal_hits(semantic, "antitrust", "regulatory")
    if not hits:
        return "no primary-legal excerpt — Risk Factors/Government Regulation boilerplate only"

    def _rank(h) -> tuple:
        ex = (h.excerpt or "").lower()
        # Prefer agency enforcement / fresh judgment over long-running MDL class refs
        if "department of justice" in ex or " doj " in f" {ex} ":
            tier = 0
        elif "european commission" in ex or " ftc " in f" {ex} ":
            tier = 1
        elif "handed down" in ex or "consent decree" in ex or "consent order" in ex:
            tier = 2
        elif "mdl" in ex or "multidistrict" in ex:
            tier = 3
        elif "legal matters" in ex:
            tier = 4
        else:
            tier = 5
        return (tier, 0 if h.section == "10-K" else 1)

    h = sorted(hits, key=_rank)[0]
    date_hint = ""
    # Prefer DOJ/CAT dating phrases when present
    for pat in (
        r"Department of Justice on ([A-Z][a-z]+ \d{1,2}, \d{4})",
        r"On ([A-Z][a-z]+ \d{1,2}, \d{4}), Visa was served",
        r"handed down.{0,40}?([A-Z][a-z]+ \d{1,2}, \d{4})",
        r"([A-Z][a-z]+ \d{1,2}, \d{4})",
    ):
        m = _re.search(pat, h.excerpt or "")
        if m:
            date_hint = m.group(1) if m.lastindex else m.group(0)
            break
    status = "open_action_disclosed"
    ex_l = (h.excerpt or "").lower()
    if "department of justice" in ex_l or " doj " in f" {ex_l} ":
        status = "DOJ_matter_disclosed_open"
    elif "handed down" in ex_l:
        status = "judgment_disclosed"
    elif "mdl" in ex_l:
        status = "MDL_class_action_ongoing_disclosed"
    bits = [
        f"form={h.section or '?'}",
        f"accession={h.accession or '?'}",
        f"evidence={h.evidence_kind}",
        f"status={status}",
        f"mechanism=antitrust/competition_law_constraint_on_rules_fees_model",
    ]
    if date_hint:
        bits.append(f"date_in_excerpt={date_hint}")
    head = (h.excerpt or "").replace("\n", " ")[:160]
    bits.append(f"excerpt={head!r}")
    return "primary-legal: " + "; ".join(bits)




def _er5_named_legal_facts(semantic: Stage9SemanticReview | None) -> list[dict]:
    """Wave 3 / SD-W3-ER5: all material named legal facts with provenance (multi-issue)."""
    import re as _re

    facts: list[dict] = []
    seen_excerpts: set[str] = set()
    for f in _primary_legal_hits(semantic, "antitrust", "regulatory", "environmental_permitting"):
        ex = (f.excerpt or "").strip()
        key = ex[:120].lower()
        if key in seen_excerpts:
            continue
        seen_excerpts.add(key)
        date_hint = None
        for pat in (
            r"On ([A-Z][a-z]+ \d{1,2}, \d{4})",
            r"([A-Z][a-z]+ \d{1,2}, \d{4})",
        ):
            m = _re.search(pat, ex)
            if m:
                date_hint = m.group(1)
                break
        status = "named_primary_legal_disclosed"
        ex_l = ex.lower()
        if "settlement" in ex_l and ("ftc" in ex_l or "doj" in ex_l or "plaintiff states" in ex_l):
            status = "settlement_disclosed"
        elif "consent" in ex_l:
            status = "consent_order_or_decree_disclosed"
        elif "lawsuit" in ex_l or "complaint" in ex_l:
            status = "open_or_disclosed_action"
        elif "judgment" in ex_l or "handed down" in ex_l:
            status = "judgment_disclosed"
        facts.append(
            {
                "topic": f.topic,
                "evidence_kind": f.evidence_kind,
                "source_form": f.section,
                "accession": f.accession,
                "date_in_excerpt": date_hint,
                "status": status,
                "excerpt": ex[:240],
                "escalate_to_human": bool(f.escalate_to_human),
            }
        )
    return facts


def _thesis_link_supported_for_legal(
    *,
    excerpt: str | None,
    gate2: dict,
    regulatory_posture: str,
) -> tuple[bool, str]:
    """SD-W3-ER8: promote ER5 legal → ER8 only with supported thesis/moat/ops link.

    Returns (supported, reason). Ambiguous → (False, ...): do not auto-promote.
    """
    import re as _re

    ex = excerpt or ""
    ex_l = ex.lower()
    # Operating / economics / moat / aftermarket / repair / fees / model constraints
    ops_moat = bool(
        _re.search(
            r"repair|right[- ]to[- ]repair|aftermarket|dealer|farmer"
            r"|fee|pricing|business\s+model|network\s+rules?"
            r"|interchange|licensing|parts?\s+availability|operating\s+economics"
            r"|competitive\s+position|moat|franchise|customer\s+lock"
            r"|forced\s+(?:rule|fee|access)|consent\s+(?:decree|order).{0,40}"
            r"(?:business|operat|fee|repair)"
            r"|repair\s+resources",
            ex_l,
            flags=_re.I,
        )
    )
    # Gate2 kill-shot overlap (words from kill-shot appearing in legal excerpt)
    g2_text = " ".join(
        str(gate2.get(k) or "")
        for k in ("kill_shot_primary", "kill_shot_secondary", "advantage_type")
    ).lower()
    g2_overlap = False
    if g2_text.strip():
        tokens = [w for w in _re.findall(r"[a-z]{4,}", g2_text) if w not in {
            "that", "this", "with", "from", "have", "will", "would", "could", "their", "about"
        }]
        hits = [w for w in tokens if w in ex_l]
        g2_overlap = len(hits) >= 2

    if ops_moat:
        return True, "legal excerpt ties to operating/moat/repair/fee/model economics"
    if g2_overlap and regulatory_posture in {"sword", "both"}:
        return True, "legal excerpt overlaps Gate2 falsifier language under sword/both posture"
    if regulatory_posture in {"sword", "both"} and ops_moat:
        return True, "sword posture with operating linkage"
    # Named agency alone without ops/moat/Gate2 link → ambiguous (do not auto-promote)
    return False, "thesis link materially ambiguous — preserve ER5 evidence; no auto ER8 promote"



def _fintech_disruption_wording_supported(
    primary: str | None,
    semantic: Stage9SemanticReview | None,
    archetype: ArchetypeAdaptation | None = None,
) -> bool:
    """SD-W4-B4: fintech/payments/network diction only when archetype or evidence supports it.

    Supported when PRIMARY is A3, secondary traits include payments/network signals,
    or semantic excerpts mention fintech / payments / multi-homing / financial technology
    in disruption/competition/moat/attack-surface neighborhoods (not universal template).
    """
    if primary == "A3":
        return True
    traits: list[str] = []
    if archetype is not None:
        traits.extend(str(t).lower() for t in (archetype.secondary_traits or []))
    # Traits may also arrive embedded on semantic-less path via primary-only; still check
    trait_blob = " ".join(traits)
    if any(
        t in trait_blob
        for t in (
            "payments",
            "payment_network",
            "network_effects",
            "fintech",
            "card_network",
        )
    ):
        return True
    if semantic is None:
        return False
    findings = list(getattr(semantic, "findings", None) or [])
    texts: list[str] = []
    for f in findings:
        topic = (getattr(f, "topic", None) or "").lower()
        if topic in {
            "disruption",
            "moat_attack_surface",
            "competition",
            "industry_structure",
            "moat_stress",
        } or "disrupt" in topic or "attack" in topic:
            texts.append(getattr(f, "excerpt", None) or "")
    # Also scan disruption_notes / competition_notes if present
    for attr in ("disruption_notes", "competition_notes", "moat_stress_notes", "industry_structure_notes"):
        v = getattr(semantic, attr, None)
        if isinstance(v, str):
            texts.append(v)
        elif isinstance(v, list):
            texts.extend(str(x) for x in v)
    blob = " ".join(texts).lower()
    cues = (
        "fintech",
        "financial technology",
        "payment network",
        "payments network",
        "multi-homing",
        "multihoming",
        "card network",
        "issuer/acquirer",
        "payment platform",
        "digital payments",
        "electronic payments",
    )
    return any(c in blob for c in cues)


def _disruption_breaker_copy(*, fintech_ok: bool) -> tuple[str, list[str], list[str]]:
    """Return (mechanism, indicators, monitors) — SD-W4-B4 conditioned wording."""
    if fintech_ok:
        return (
            "Credible substitute / fintech / multi-homing trajectory erodes claimed advantage",
            [
                "Share or pricing pressure with named attacker economics",
                "Multi-homing or disintermediation evidence (not headline)",
            ],
            ["fintech/network share shifts", "issuer/acquirer multi-homing"],
        )
    return (
        "Credible substitute / alternative-process trajectory erodes claimed advantage",
        [
            "Share or pricing pressure with named substitute economics",
            "Disintermediation or alternative-process evidence (not headline)",
        ],
        ["substitute share shifts", "alternative process adoption"],
    )


def _disruption_monitor_only_copy(*, fintech_ok: bool) -> str:
    if fintech_ok:
        return (
            "TB_DISRUPTION monitoring only — fintech/attack-surface language lacks "
            "mechanism+exposure+attacker-economics substance (CLAIM alone ≠ strong breaker)"
        )
    return (
        "TB_DISRUPTION monitoring only — disruption/attack-surface language lacks "
        "mechanism+exposure+attacker-economics substance (CLAIM alone ≠ strong breaker)"
    )


def _finding_has_risk_triple(f) -> bool:
    return bool(f.mechanism and f.exposure and f.excerpt and len(f.excerpt) > 40)

def _build_breakers(
    *,
    gate2: dict[str, Any],
    semantic: Stage9SemanticReview | None,
    primary: str | None,
    concentration: dict[str, str],
    regulatory_posture: str,
) -> list[ThesisBreaker]:
    """Assemble 3–7 observable falsifiers — deepen Gate2 / Risk Factors; no encyclopedic doom."""
    breakers: list[ThesisBreaker] = []
    n = 0

    def add(**kwargs: Any) -> None:
        nonlocal n
        if len(breakers) >= 7:
            return
        n += 1
        bid = kwargs.pop("breaker_id", None) or f"TB{n}"
        breakers.append(ThesisBreaker(breaker_id=bid, **kwargs))

    if gate2.get("kill_shot_primary"):
        add(
            breaker_id="TB_G2_PRIMARY",
            mechanism=str(gate2["kill_shot_primary"]),
            observable_indicators=[
                "Gate2 primary kill-shot indicators from Stage 1 hypothesis",
                "External attack/erosion evidence vs claimed advantage",
            ],
            monitoring_variables=list(gate2.get("monitoring_variables") or [])[:4]
            or ["named Gate2 monitoring variables (if present)"],
            evidence_label="INFERENCE",
            linked_er_lenses=["ER2", "ER8"],
            active_fact=False,
            source_tie="Gate2 kill_shot_primary (hypothesis)",
        )
    if gate2.get("kill_shot_secondary"):
        add(
            breaker_id="TB_G2_SECONDARY",
            mechanism=str(gate2["kill_shot_secondary"]),
            observable_indicators=["Gate2 secondary kill-shot trajectory"],
            monitoring_variables=list(gate2.get("monitoring_variables") or [])[:3]
            or ["secondary kill-shot monitors"],
            evidence_label="INFERENCE",
            linked_er_lenses=["ER2", "ER8"],
            source_tie="Gate2 kill_shot_secondary (hypothesis)",
        )

    topics = _topics(semantic)
    monitors_seed: list[str] = []  # CLAIM/INFERENCE-only thin items → monitoring, not strong breakers

    primary_legal = _primary_legal_hits(semantic, "antitrust", "regulatory")
    if primary_legal or "antitrust" in topics or "regulatory" in topics:
        # Generic Risk Factors boilerplate must NOT be ACTIVE breaker (Plan §0.E / D7).
        # Wave 3 / SD-W3-ER8: promote ER5 legal → ER8 ONLY with supported thesis link.
        if primary_legal:
            # Prefer settlement / lawsuit / repair-ops excerpts for thesis-link judgment (not thin RF bullets)
            def _legal_rank(h):
                ex = (h.excerpt or "").lower()
                score = 0
                if "settlement" in ex and ("ftc" in ex or "doj" in ex):
                    score -= 100
                if "lawsuit" in ex or "complaint" in ex:
                    score -= 50
                if "repair" in ex or "aftermarket" in ex or "dealer" in ex:
                    score -= 40
                if "consent" in ex:
                    score -= 30
                score += 0 if excerpt_has_primary_legal(h.excerpt) else 10
                score += 0 if (h.section or "") in {"10-K", "10-Q"} else 5
                return (score, -(len(h.excerpt or "")))

            ranked = sorted(primary_legal, key=_legal_rank)
            best_ex = ranked[0].excerpt
            # Promote if ANY material named fact has supported thesis link (multi-issue ER5)
            linked = False
            link_why = "thesis link materially ambiguous — preserve ER5 evidence; no auto ER8 promote"
            for h in ranked:
                ok, why = _thesis_link_supported_for_legal(
                    excerpt=h.excerpt,
                    gate2=gate2,
                    regulatory_posture=regulatory_posture,
                )
                if ok:
                    linked = True
                    link_why = why
                    best_ex = h.excerpt
                    break
            if linked:
                # Mechanism: prefer excerpt-grounded ops constraint over network-only boilerplate
                mech = (
                    "Adverse regulatory / legal action constrains ownership thesis, moat, "
                    "or operating economics (named primary-legal FACT)"
                )
                add(
                    breaker_id="TB_REG_SWORD",
                    mechanism=mech,
                    observable_indicators=[
                        "Material adverse order / consent / settlement / legislation",
                        "Forced access, repair, fee, or model changes with durable economics impact",
                    ],
                    monitoring_variables=[
                        "open regulatory/antitrust actions",
                        "settlement compliance / consent oversight",
                        "thesis-linked operating or moat indicators",
                    ],
                    evidence_label="FACT",
                    linked_er_lenses=["ER5", "ER8"],
                    active_fact=True,
                    source_tie=_best_primary_legal_source_tie(semantic) + f"; thesis_link={link_why}",
                )
            else:
                # Preserve ER5 evidence; do NOT auto-promote; HITL/REVIEW exception path
                monitors_seed.append(
                    "TB_REG_SWORD not auto-promoted — named primary-legal FACT preserved on ER5 but "
                    f"thesis link ambiguous ({link_why}); HITL/REVIEW_REQUIRED exception path "
                    f"(SD-W3-ER8); source={_best_primary_legal_source_tie(semantic)}"
                )
        else:
            monitors_seed.append(
                "TB_REG_SWORD monitoring only — regulatory/antitrust language is CLAIM/boilerplate "
                "without named primary-legal action (DOJ/FTC/EC/order/judgment/MDL); "
                f"source={_best_primary_legal_source_tie(semantic)}"
            )

    disruption_hits = [
        f
        for f in _findings_for(semantic, "disruption", "moat_attack_surface")
        if _finding_has_risk_triple(f)
        or excerpt_has_disruption_substance(f.excerpt)
    ]
    if disruption_hits:
        if primary in {"A8", "A9"}:
            tb_mech = (
                "Technology / process / substitute trajectory erodes cost curve or volume franchise"
            )
            tb_ind = [
                "Cost-curve or volume share pressure with named mechanism",
                "Substitute process economics (not weather/ops headline)",
            ]
            tb_mon = ["cost_curve_vs_peers", "substitute_process_adoption"]
        else:
            # SD-W4-B4: archetype/evidence-conditioned wording (no universal fintech template)
            fintech_ok = _fintech_disruption_wording_supported(primary, semantic)
            tb_mech, tb_ind, tb_mon = _disruption_breaker_copy(fintech_ok=fintech_ok)
        add(
            breaker_id="TB_DISRUPTION",
            mechanism=tb_mech,
            observable_indicators=tb_ind,
            monitoring_variables=tb_mon,
            evidence_label=_evidence_kind_for(semantic, "disruption", "moat_attack_surface"),
            linked_er_lenses=["ER3", "ER2", "ER8"],
            active_fact=False,
            source_tie="disruption mechanism+exposure semantic (not headline)",
        )
    elif "disruption" in topics or "moat_attack_surface" in topics:
        fintech_ok = _fintech_disruption_wording_supported(primary, semantic)
        monitors_seed.append(_disruption_monitor_only_copy(fintech_ok=fintech_ok))
    if any(concentration.get(a) in {"high", "extreme"} for a in concentration):
        axes = [a for a, v in concentration.items() if v in {"high", "extreme"}]
        # Map ER4 axis → semantic topic; FACT disclosure can back a breaker (still not ACTIVE).
        axis_topic = {
            "customer": "concentration_customer",
            "supplier": "concentration_supplier",
            "geo": "concentration_geo",
            "product": "concentration_product",
            "distribution": "concentration_distribution",
        }
        conc_fact_hits = [
            f
            for f in _findings_for(
                semantic,
                "concentration_customer",
                "concentration_supplier",
                "concentration_geo",
            )
            if (f.evidence_kind or "").upper() == "FACT"
            and f.excerpt
            and len(f.excerpt) > 40
        ]
        # FACT must land on the high/extreme axes — unrelated-axis FACT (e.g. named
        # largest-customer without quant while geo=high CLAIM) must not back the breaker.
        high_topics = {axis_topic[a] for a in axes if a in axis_topic}
        axis_fact = [
            f
            for f in conc_fact_hits
            if f.topic in high_topics
        ]
        # Quantitative materiality for customer axis: escalate flag / quant marker
        material_axis_fact = [
            f
            for f in axis_fact
            if f.topic != "concentration_customer"
            or f.escalate_to_human
            or excerpt_has_concentration_quant(f.excerpt)
        ]
        if material_axis_fact:
            add(
                breaker_id="TB_CONCENTRATION",
                mechanism=f"Material concentration shock on axes={axes}",
                observable_indicators=[
                    f"{a} concentration label={concentration[a]}" for a in axes
                ],
                monitoring_variables=[f"{a}_concentration_disclosure" for a in axes],
                evidence_label="FACT",
                linked_er_lenses=["ER4", "ER8"],
                active_fact=False,  # descriptive FACT ≠ ACTIVE sword; INFERENCE alone never ACTIVE
                source_tie=(
                    "ER4 concentration FACT disclosure (descriptive; not auto-fail); "
                    f"e.g. {(material_axis_fact[0].excerpt or '')[:120]}"
                ),
            )
        else:
            # Labels / INFERENCE / named-customer-without-quant → monitor
            monitors_seed.append(
                "TB_CONCENTRATION monitoring only — high/extreme labels lack material "
                "FACT on those axes (INFERENCE alone ≠ ACTIVE; largest-customer without "
                f"disclosed revenue share ≠ automatic material) (axes={axes})"
            )
    geo_hits = [
        f
        for f in _findings_for(semantic, "geopolitical")
        if _finding_has_risk_triple(f) or excerpt_has_geo_substance(f.excerpt)
    ]
    if geo_hits:
        add(
            breaker_id="TB_GEO",
            mechanism="Geopolitical / sanctions / export-control shock hits footprint",
            observable_indicators=["sanctions expansion", "cross-border volume shock"],
            monitoring_variables=["geo footprint disclosures", "sanctions list changes"],
            evidence_label=_evidence_kind_for(semantic, "geopolitical"),
            linked_er_lenses=["ER6", "ER8"],
            active_fact=False,
            source_tie="geo footprint+mechanism semantic (not fear headline)",
        )
    elif "geopolitical" in topics:
        monitors_seed.append(
            "TB_GEO monitoring only — geopolitical language without clear footprint+mechanism "
            "(CLAIM alone ≠ strong breaker; FP-E10)"
        )
    # Cycle breaker: strong only for A8/A9 (windfall≠franchise) or when cycle class is not unknown
    # with substantive macro exposure — bare consumer-spend CLAIM → monitoring
    macro_hits = _findings_for(semantic, "macro_cycle")
    cycle_strong = primary in {"A8", "A9"} or (
        bool(macro_hits)
        and any(
            x in ((f.excerpt or "") + (f.mechanism or "")).lower()
            for f in macro_hits
            for x in ("recession", "downturn", "cyclical", "mid-cycle", "peak")
        )
    )
    if cycle_strong:
        add(
            breaker_id="TB_CYCLE",
            mechanism="Cycle / demand shock exposes windfall≠franchise or volume fragility",
            observable_indicators=[
                "volume or price trough vs mid-cycle honesty",
                "peak-margin narrative failure",
            ],
            monitoring_variables=["cycle indicators relevant to archetype", "mid-cycle metrics"],
            evidence_label=_evidence_kind_for(semantic, "macro_cycle")
            if "macro_cycle" in topics
            else "INFERENCE",
            linked_er_lenses=["ER7", "ER8"],
            active_fact=False,
            source_tie="ER7 macro/cycle + archetype soft",
        )
    elif "macro_cycle" in topics:
        monitors_seed.append(
            "TB_CYCLE monitoring only — macro/consumer-spend CLAIM without cycle-position "
            "or A8/A9 windfall≠franchise substance"
        )

    # Ensure at least 3 when Gate2 thin — seed from structure without kitchen-sink
    if len(breakers) < 3:
        add(
            breaker_id="TB_STRUCTURE",
            mechanism="Industry structure shift reduces surplus capture by the OpCo",
            observable_indicators=[
                "buyer/supplier power shift",
                "entry barrier erosion with evidence",
            ],
            monitoring_variables=["structure map refresh from 10-K Competition"],
            evidence_label=_evidence_kind_for(semantic, "industry_structure", "competition"),
            linked_er_lenses=["ER1", "ER8"],
            source_tie="ER1 structure map",
        )
    if len(breakers) < 3:
        add(
            breaker_id="TB_ADVANTAGE_EROSION",
            mechanism="External erosion of claimed Gate2 advantage type without Stage 1 rewrite",
            observable_indicators=["advantage_type under attack with mechanism+exposure"],
            monitoring_variables=["Gate2 advantage monitoring (hypothesis)"],
            evidence_label="INFERENCE",
            linked_er_lenses=["ER2", "ER8"],
            source_tie="Gate2 advantage_type hypothesis",
        )

    # Cap at 7
    return breakers, monitors_seed[:7]


def _fp_tags(
    *,
    semantic: Stage9SemanticReview | None,
    primary: str | None,
    s8_h9: list[str],
    breakers: list[ThesisBreaker],
) -> list[dict[str, Any]]:
    """FP-E flags — flags not auto-fails; no count→outcome."""
    tags: list[dict[str, Any]] = []
    topics = _topics(semantic)
    blob = semantic_text_blob(semantic).lower()

    def add(fp_id: str, why: str, counter: str, severity: str = "medium") -> None:
        desc = next((d for i, d, *_ in [(a[0], a[1], a[2]) for a in FALSE_POSITIVE_CATALOGUE] if i == fp_id), fp_id)
        # catalogue tuples are (id, desc, severity)
        for item in FALSE_POSITIVE_CATALOGUE:
            if item[0] == fp_id:
                desc = item[1]
                severity = item[2]
                break
        tags.append(
            {
                "id": fp_id,
                "description": desc,
                "severity": severity,
                "why": why,
                "counterexample": counter,
            }
        )

    if "disruption" in topics and ("ai" in blob or "artificial intelligence" in blob):
        add(
            "FP-E3",
            "Disruption language present — require attacker economics, not AI headline",
            "Mechanism+exposure+evidence required before ER3 conclusion",
        )
    if "regulatory" in topics or "antitrust" in topics:
        add(
            "FP-E4",
            "Regulation present — barrier vs sword honesty required (not safe-moat assumption)",
            "ER5 posture must allow sword",
        )
    if primary in {"A8", "A9"}:
        add(
            "FP-E7",
            "Cyclical archetype — peak earnings ≠ franchise proof",
            "ER7 mid-cycle honesty / windfall≠franchise",
        )
    if "competition" in topics:
        add(
            "FP-E8",
            "Competitors named in 10-K ≠ automatic intense-rivalry score",
            "ER1 structure map is semantic, no Porter score",
        )
    if "geopolitical" in topics:
        add(
            "FP-E10",
            "Geopolitical language without clear footprint → UNKNOWN over fake certainty",
            "ER6 requires footprint+mechanism",
        )
    if "S8_H9_EXPECTATIONS_DEMANDING" in s8_h9 or "S8_H9_CYCLE_SENSITIVE_VALUATION" in s8_h9:
        add(
            "FP-E11",
            "Stage 8 valuation carries forwarded — cheapness does not cure external risk",
            "Stage 8 ⊥ Stage 9; no valuation redo",
        )
    if not topics:
        add(
            "FP-E12",
            "Sparse semantic hits — silence ≠ no external risk",
            "Deepen 10-K Business/Competition/Risk Factors",
        )
    add(
        "FP-E1",
        "Headline-only items discarded — risk triple required",
        "mechanism+exposure+evidence",
        "high",
    )
    if primary == "A3" or (semantic and semantic.industry_structure_notes):
        add(
            "FP-E2",
            "Do not infer durable moat from margins/returns alone (Stage 5 hypothesis soft only)",
            "ER2 stresses Gate2 externally; no S5 pricing-power redo",
        )
    # Dedup by id preserving order
    seen: set[str] = set()
    out = []
    for t in tags:
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        out.append(t)
    return out


def _decide_outcome(
    *,
    gate0_class: str,
    usable: bool,
    semantic_filled: bool,
    breakers: list[ThesisBreaker],
    carries: list[str],
    conflicts: list[str],
    escalate: bool,
    concentration: dict[str, str],
    escalate_reason: str | None = None,
) -> tuple[Stage9ProcessOutcome, list[str]]:
    why: list[str] = []
    if gate0_class != "operating":
        why.append("Gate0 ≠ operating → TOO_HARD (FI/commodity out of Stage 9 v1 scope)")
        return "TOO_HARD", why
    if not usable:
        why.append("Not evaluable — no Normalized periods and empty semantic → TOO_HARD")
        return "TOO_HARD", why

    active_fact = [b for b in breakers if b.active_fact]
    # Substantive ER causes only — flag count ≠ outcome; CLAIM carries alone ≠ mechanical RR.
    review_cues: list[str] = []
    if active_fact:
        review_cues.append(
            "active FACT breaker(s)="
            + str([b.breaker_id for b in active_fact])
            + " (primary-legal / named open action — not Risk Factors boilerplate)"
        )
    if "S9_HFA_MOAT_DURABILITY_STRESSED" in carries:
        review_cues.append("moat durability stressed (external attack vs Gate2 hypothesis)")
    if "S9_HFA_CONCENTRATION_EXTREME" in carries:
        review_cues.append("concentration extreme (descriptive; not auto-fail)")
    if conflicts:
        review_cues.append("S1–8 conflicts surfaced")
    if escalate:
        # Caller passes escalate only for primary-legal FACT or material concentration FACT.
        # Soft A8/LOW, commodity class, CLAIM count, inactive GEO/CYCLE must NOT land here.
        review_cues.append(
            escalate_reason
            or (
                "semantic escalate_to_human on primary-legal FACT and/or material "
                "concentration FACT (not soft A8/LOW / commodity class / CLAIM count / "
                "inactive GEO-CYCLE)"
            )
        )
    # REGULATORY_MATERIAL contributes to RR only alongside active FACT / escalate
    # (carry alone from thin CLAIM must not force RR)
    if (
        "S9_HFA_REGULATORY_MATERIAL" in carries
        and (active_fact or escalate)
    ):
        review_cues.append("regulatory material backed by primary-legal / escalate")

    if review_cues:
        why.append("REVIEW_REQUIRED candidacy from: " + "; ".join(review_cues))
        why.append(
            "NON-TERMINATING — no BUY/SELL/RED; no mechanical sector-risk kill; "
            "labels are evidence not a count formula; flag count ≠ outcome"
        )
        return "REVIEW_REQUIRED", why

    cond_cues: list[str] = []
    if not semantic_filled:
        cond_cues.append("semantic incomplete — deepen filings")
    if any(v == "unknown" for v in concentration.values()):
        cond_cues.append("concentration axes largely unknown")
    if "S9_HFA_CYCLE_PEAK_RISK" in carries:
        cond_cues.append("cycle peak risk carry — monitors")
    if "S9_HFA_GEO_MATERIAL" in carries:
        cond_cues.append("geo material carry — monitoring (CLAIM/footprint; not auto-RR)")
    if "S9_HFA_DISRUPTION_MECHANISM" in carries:
        cond_cues.append("disruption mechanism carry — monitoring (not auto-RR without FACT breaker)")
    if "S9_HFA_REGULATORY_MATERIAL" in carries and not active_fact:
        cond_cues.append("regulatory material without active FACT breaker — monitors")
    if len(breakers) < 3:
        cond_cues.append("fewer than 3 assembled breakers")

    if cond_cues:
        why.append("CONDITIONAL from: " + "; ".join(cond_cues))
        return "CONDITIONAL", why

    why.append(
        "MUST answered honestly; ER pack coherent; no material unresolved FACT breaker — "
        "PROCEED with evidence (Stage 9 non-terminating; no final FA synthesis)"
    )
    return "PROCEED", why


def evaluate_stage9(
    ticker: str,
    periods: list[dict[str, Any]],
    *,
    gate0_class: str = "operating",
    sources: list[str] | None = None,
    semantic: Stage9SemanticReview | None = None,
    thesis_summary: str | None = None,
    business_notes: str | None = None,
    prior_archetype: dict[str, Any] | None = None,
    stage1_artifact: dict[str, Any] | None = None,
    stage2_artifact: dict[str, Any] | None = None,
    stage3_artifact: dict[str, Any] | None = None,
    stage4_artifact: dict[str, Any] | None = None,
    stage5_artifact: dict[str, Any] | None = None,
    stage6_artifact: dict[str, Any] | None = None,
    stage7_artifact: dict[str, Any] | None = None,
    stage8_artifact: dict[str, Any] | None = None,
    unresolved_major_conflict: bool = False,
    force_primary: str | None = None,
) -> Stage9Report:
    sources = list(sources or [])
    handoff = build_prior_handoff(
        stage1=stage1_artifact,
        stage2=stage2_artifact,
        stage3=stage3_artifact,
        stage4=stage4_artifact,
        stage5=stage5_artifact,
        stage6=stage6_artifact,
        stage7=stage7_artifact,
        stage8=stage8_artifact,
    )
    if prior_archetype and not handoff.get("prior_archetype"):
        handoff["prior_archetype"] = prior_archetype
        handoff["primary_archetype"] = prior_archetype.get("primary_archetype")

    archetype = _adapt_archetype(handoff.get("prior_archetype"), force_primary, semantic)
    primary = (archetype.primary_archetype if archetype else None) or handoff.get(
        "primary_archetype"
    )

    cues = semantic_cues_from_review(semantic)
    s8_h9 = [c for c in (handoff.get("s8_h9_carries") or []) if c in S8_H9_FORWARDABLE]
    calc = compute_stage9_metrics(
        periods,
        semantic_cues=cues,
        primary_archetype=primary,
        s8_h9=s8_h9,
    )
    concentration = dict(calc.metrics.get("concentration_axes") or {})
    cycle_class = str(calc.metrics.get("cycle_position_class") or "unknown")

    periods_sorted = sorted(
        [p for p in periods if p.get("period_type") == "FY"],
        key=lambda d: d.get("period_key") or "",
    )
    periods_used = [
        {
            "period_key": p.get("period_key") or "",
            "version_id": p.get("version_id") or "",
            "period_type": p.get("period_type") or "FY",
        }
        for p in periods_sorted[-5:]
    ]

    gate2 = handoff.get("gate2_hypothesis") or {}
    topics = _topics(semantic)
    q_lookup = {qid: qtext for qid, qtext in list(MUST_QUESTIONS) + list(SHOULD_QUESTIONS)}
    answers: list[QuestionAnswer] = []

    def ans(qid: str, status: str, summary: str, refs: list[str] | None = None, must: bool = True) -> None:
        answers.append(
            QuestionAnswer(
                question_id=qid,
                question=q_lookup.get(qid, qid),
                status=status,  # type: ignore[arg-type]
                answer_summary=summary,
                evidence=list(refs or []),
                must=must,
            )
        )

    # --- ER lenses ---
    er_lenses: list[ERLensResult] = []
    industry_bullets: list[str] = []
    moat_bullets: list[str] = []
    disruption_bullets: list[str] = []
    concentration_bullets: list[str] = []
    reg_geo_bullets: list[str] = []
    macro_bullets: list[str] = []
    breaker_fp_bullets: list[str] = []
    why: list[str] = []
    carry: list[str] = []
    monitors: list[str] = []
    gaps: list[str] = []
    conflicts: list[str] = list(handoff.get("conflicts_seed") or [])
    s9_carries: list[str] = []

    # ER1
    er1_sum = (
        (semantic.industry_structure_notes if semantic else None)
        or (semantic.competition_notes if semantic else None)
        or "Industry structure map thin — deepen 10-K Business/Competition"
    )
    industry_bullets.append(f"structure_notes={str(er1_sum)[:220]}")
    industry_bullets.append("No Porter score; semantic five-forces-style map only")
    industry_bullets.append(
        f"external_risk_emphasis={EXTERNAL_RISK_EMPHASIS_BY_ARCHETYPE.get(primary or '', [])}"
    )
    if primary:
        industry_bullets.append(f"primary_engine_archetype={primary} (soft reuse; not a grade)")
    er_lenses.append(
        ERLensResult(
            lens_id="ER1",
            lens_name="Industry Structure Map",
            summary=str(er1_sum)[:300],
            why="Source-first Competition/Business semantic; no Porter score; no warehouse",
            labels={"porter_score": None, "no_industry_warehouse": True},
            evidence=[f.excerpt or f.topic for f in _findings_for(semantic, "industry_structure", "competition")[:3]],
            mechanism="industry_structure_governs_surplus_capture",
            exposure="value_capture_vs_rivals_buyers_suppliers_substitutes",
            evidence_label=_evidence_kind_for(semantic, "industry_structure", "competition"),
        )
    )
    ans(
        "S9-M1",
        "answered" if ("industry_structure" in topics or "competition" in topics) else "partial",
        f"ER1 structure pack; archetype={primary}; no Porter score",
        ["ER1"],
    )

    # ER2 — hypotheses only
    adv = gate2.get("advantage_type")
    moat_bullets.append(
        "ER2 locked: Gate2/S1/S5 consumed as hypotheses only — "
        "NO Stage 5 pricing-power redo; NO Stage 1 thesis restatement"
    )
    if adv:
        moat_bullets.append(
            f"Gate2 advantage_type hypothesis pointer={adv!r} — external erosion test only"
        )
    else:
        moat_bullets.append("Gate2 advantage_type absent — moat stress limited; UNKNOWN lean")
        gaps.append("Gate2 advantage_type hypothesis missing")
    attack_hits = _findings_for(semantic, "moat_attack_surface", "disruption", "antitrust")
    moat_stressed = bool(attack_hits) and bool(adv)
    if moat_stressed:
        moat_bullets.append(
            "External attack/substitute/regulatory-sword surfaces present vs Gate2 claim — "
            "stress noted (not a new moat grade)"
        )
        s9_carries.append("S9_HFA_MOAT_DURABILITY_STRESSED")
    moat_bullets.append(
        f"S5 durability soft-consume present={handoff.get('s5_durability_hypothesis', {}).get('present')} "
        f"(hypothesis support only; no_pricing_power_redo=True)"
    )
    # Explicitly refuse to emit Stage 1 one_sentence as Stage 9 deliverable
    if gate2.get("one_sentence_pointer"):
        moat_bullets.append(
            "Stage 1 one_sentence kept as pointer only — not restated as Stage 9 thesis prose"
        )
    er_lenses.append(
        ERLensResult(
            lens_id="ER2",
            lens_name="Moat Durability Stress",
            summary=(
                "External erosion test vs Gate2 hypothesis"
                if adv
                else "Gate2 hypothesis thin — durability stress limited"
            ),
            why="Hypotheses-only consume; windfall≠franchise honesty; no moat grade gate",
            labels={
                "moat_grade_awarded": None,
                "gate2_advantage_present": bool(adv),
                "externally_stressed": moat_stressed,
                "no_s5_pricing_power_redo": True,
                "no_s1_thesis_restatement": True,
            },
            evidence=[f.excerpt or f.topic for f in attack_hits[:3]],
            mechanism="external_attack_substitute_entry_or_regulatory_sword",
            exposure="claimed_advantage_erosion",
            evidence_label=_evidence_kind_for(semantic, "moat_attack_surface", "disruption"),
            escalate_to_human=moat_stressed,
        )
    )
    ans(
        "S9-M2",
        "answered",
        f"ER2 external stress; gate2_adv={bool(adv)}; stressed={moat_stressed}; no S5 redo / no S1 restatement",
        ["ER2"],
    )

    # ER3
    disruption_hits = _findings_for(semantic, "disruption")
    disruption_substantive = [
        f
        for f in disruption_hits
        if (f.mechanism and f.exposure and f.excerpt)
        or excerpt_has_disruption_substance(f.excerpt)
    ]
    if disruption_substantive:
        disruption_bullets.append(
            f"disruption_notes={(semantic.disruption_notes if semantic else '')[:220]}"
        )
        disruption_bullets.append(
            "Require mechanism+exposure+evidence — anti FP-E3 headline theatre"
        )
        s9_carries.append("S9_HFA_DISRUPTION_MECHANISM")
    elif disruption_hits:
        disruption_bullets.append(
            f"disruption language present but thin (CLAIM/ecosystem naming) — "
            f"notes={(semantic.disruption_notes if semantic else '')[:180]}"
        )
        disruption_bullets.append(
            "No S9_HFA_DISRUPTION_MECHANISM — uncertainty/monitoring, not packaged as fact"
        )
        monitors.append(
            "ER3 disruption CLAIM without attacker-economics substance — monitoring only"
        )
        gaps.append("ER3 disruption mechanism thin (CLAIM ≠ carry)")
    else:
        disruption_bullets.append(
            "No clear disruption mechanism excerpt — UNKNOWN over fake certainty"
        )
        gaps.append("ER3 disruption mechanism thin")
    er_lenses.append(
        ERLensResult(
            lens_id="ER3",
            lens_name="Disruption Mechanism",
            summary=(semantic.disruption_notes if semantic and semantic.disruption_notes else "UNKNOWN/thin"),
            why="Christensen-honest: mechanism+exposure+evidence; anti-headline",
            labels={"headline_only_discarded": True},
            evidence=[f.excerpt or f.topic for f in disruption_hits[:3]],
            mechanism=(disruption_hits[0].mechanism if disruption_hits else None),
            exposure=(disruption_hits[0].exposure if disruption_hits else None),
            evidence_label=_evidence_kind_for(semantic, "disruption"),
        )
    )
    ans(
        "S9-M3",
        "answered" if disruption_hits else "partial",
        f"ER3 disruption hits={len(disruption_hits)}",
        ["ER3"],
    )

    # ER4
    for axis, label in concentration.items():
        concentration_bullets.append(
            f"{axis}={label} (descriptive; thresholds NOT_LOCKED; not auto-fail)"
        )
    if any(v == "extreme" for v in concentration.values()):
        s9_carries.append("S9_HFA_CONCENTRATION_EXTREME")
        concentration_bullets.append(
            "extreme label → possible REVIEW lean + carry — still NON-TERMINATING / not auto-fail"
        )
    if semantic and semantic.concentration_notes:
        concentration_bullets.append(f"semantic={semantic.concentration_notes[:220]}")
    # Named largest-customer without revenue-share quant → uncertainty monitor (not RR)
    named_no_quant = [
        f
        for f in _findings_for(semantic, "concentration_customer")
        if f.excerpt
        and len(f.excerpt) > 40
        and not f.escalate_to_human
        and not excerpt_has_concentration_quant(f.excerpt)
    ]
    if named_no_quant:
        concentration_bullets.append(
            "largest-customer / named customer disclosed without quantitative revenue "
            "share — monitoring/uncertainty (largest customer alone ≠ automatic material)"
        )
        monitors.append(
            "ER4 customer concentration named without disclosed revenue share — "
            "monitoring/uncertainty (not material FACT escalate)"
        )
    er_lenses.append(
        ERLensResult(
            lens_id="ER4",
            lens_name="Concentration Map",
            summary=str(concentration),
            why="Descriptive axes only; no numeric kill gate",
            labels={**concentration, "no_auto_fail": True},
            evidence=[semantic.concentration_notes] if semantic and semantic.concentration_notes else [],
            mechanism="concentration_dependency",
            exposure="earnings_or_ops_sensitivity",
            evidence_label=_evidence_kind_for(
                semantic, "concentration_customer", "concentration_supplier", "concentration_geo"
            ),
        )
    )
    ans("S9-M4", "answered", f"ER4 axes={concentration}", ["ER4"])

    # ER5 + ER6 (dashboard combines)
    reg_hits = _findings_for(
        semantic, "regulatory", "antitrust", "environmental_permitting"
    )
    geo_hits = _findings_for(semantic, "geopolitical")
    if reg_hits and any(f.topic == "antitrust" for f in reg_hits):
        regulatory_posture = "both"  # networks often barrier+sword
    elif reg_hits:
        regulatory_posture = "sword"  # presence of material reg language → honesty toward sword
    else:
        regulatory_posture = "unknown"
    reg_geo_bullets.append(f"regulatory_posture={regulatory_posture} (barrier vs sword honesty)")
    if semantic and semantic.regulatory_notes:
        reg_geo_bullets.append(f"regulatory={semantic.regulatory_notes[:220]}")
    primary_legal_reg = _primary_legal_hits(semantic, "antitrust", "regulatory", "environmental_permitting")
    named_legal_facts = _er5_named_legal_facts(semantic)
    if named_legal_facts:
        # SD-W3-ER5: surface ALL material named facts (no singular-primary collapse; no rank score)
        reg_geo_bullets.append(
            f"ER5 named_legal_facts_count={len(named_legal_facts)} "
            "(multi-issue; each preserved separately; no numeric rank score)"
        )
        for i, fact in enumerate(named_legal_facts, 1):
            reg_geo_bullets.append(
                f"ER5_LEGAL_{i}: status={fact.get('status')}; "
                f"form={fact.get('source_form')}; accession={fact.get('accession')}; "
                f"date={fact.get('date_in_excerpt')}; "
                f"excerpt={(fact.get('excerpt') or '')[:180]!r}"
            )
    if primary_legal_reg:
        s9_carries.append("S9_HFA_REGULATORY_MATERIAL")
        reg_geo_bullets.append(
            "S9_HFA_REGULATORY_MATERIAL — primary-legal / named action(s) surfaced "
            f"(n={len(named_legal_facts) or len(primary_legal_reg)}; not RF boilerplate; "
            "closed/settled may remain visible if still relevant)"
        )
    elif reg_hits:
        env_hits = [f for f in reg_hits if f.topic == "environmental_permitting"]
        if env_hits:
            reg_geo_bullets.append(
                "ER5 environmental/permitting coverage: env regulation, permitting/"
                "licensing, mine approvals, remediation/closure, and/or env litigation "
                f"language present (CLAIM; n={len(env_hits)}) — not ESG vendor grade"
            )
        reg_geo_bullets.append(
            "Regulatory/antitrust CLAIM language present — monitoring; "
            "no S9_HFA_REGULATORY_MATERIAL without primary-legal FACT"
        )
        monitors.append(
            "ER5 regulatory CLAIM/boilerplate without primary-legal — monitoring only"
        )
    # GEO_MATERIAL needs geo mechanism + company footprint exposure + evidence.
    # China demand / revenue concentration ≠ auto geo (ER4). Russia-Ukraine price-vol
    # without ops/sanctions footprint ≠ GEO_MATERIAL overstatement.
    geo_material_hits = [
        f
        for f in geo_hits
        if f.excerpt
        and excerpt_has_geo_substance(f.excerpt)
        and excerpt_has_geo_footprint(f.excerpt)
    ]
    if semantic and semantic.geopolitical_notes:
        reg_geo_bullets.append(f"geopolitical={semantic.geopolitical_notes[:220]}")
    if geo_material_hits:
        s9_carries.append("S9_HFA_GEO_MATERIAL")
        reg_geo_bullets.append(
            "S9_HFA_GEO_MATERIAL — geo mechanism+footprint exposure+evidence "
            "(factual carry; still NON-TERMINATING; China demand ≠ auto geo)"
        )
    elif geo_hits or (semantic and semantic.geopolitical_notes):
        # Substance without footprint (e.g. Russia-Ukraine commodity price shock) → monitor
        thin_reason = (
            "geo shock without company footprint exposure"
            if any(excerpt_has_geo_substance(f.excerpt) for f in geo_hits if f.excerpt)
            else "CLAIM without clear footprint+mechanism"
        )
        reg_geo_bullets.append(
            f"Geopolitical {thin_reason} — monitoring; "
            "no S9_HFA_GEO_MATERIAL (uncertainty ≠ fact; demand/concentration ≠ geo HFA)"
        )
        monitors.append("ER6 geo CLAIM thin — monitoring only (FP-E10)")
    elif not geo_hits:
        reg_geo_bullets.append("Geopolitical footprint opaque → UNKNOWN (no country-risk score)")
    er_lenses.append(
        ERLensResult(
            lens_id="ER5",
            lens_name="Regulatory / Policy Envelope",
            summary=f"posture={regulatory_posture}",
            why="Primary legal/company sources; no headline-count score; barrier vs sword",
            labels={"posture": regulatory_posture, "no_headline_score": True},
            evidence=[f.excerpt or f.topic for f in reg_hits[:3]],
            mechanism="regulatory_or_antitrust_constraint_or_barrier",
            exposure="rules_fees_model_constraints",
            evidence_label=(
                "FACT"
                if primary_legal_reg
                else _evidence_kind_for(
                    semantic, "regulatory", "antitrust", "environmental_permitting"
                )
            ),
            escalate_to_human=bool(primary_legal_reg),
        )
    )
    er_lenses.append(
        ERLensResult(
            lens_id="ER6",
            lens_name="Geopolitical Exposure",
            summary=(semantic.geopolitical_notes if semantic and semantic.geopolitical_notes else "UNKNOWN/opaque"),
            why="Footprint+mechanism; no country-risk engine",
            labels={"no_country_risk_engine": True},
            evidence=[f.excerpt or f.topic for f in geo_hits[:3]],
            mechanism=(geo_hits[0].mechanism if geo_hits else None),
            exposure=(geo_hits[0].exposure if geo_hits else None),
            evidence_label=_evidence_kind_for(semantic, "geopolitical"),
        )
    )
    ans(
        "S9-M5",
        "answered" if reg_hits else "partial",
        f"ER5 posture={regulatory_posture}",
        ["ER5"],
    )
    ans(
        "S9-M6",
        "answered" if geo_hits else "partial",
        f"ER6 geo hits={len(geo_hits)}; UNKNOWN when opaque",
        ["ER6"],
    )

    # ER7
    macro_hits = _findings_for(semantic, "macro_cycle")
    macro_bullets.append(f"cycle_position_class={cycle_class} (descriptive ≠ prediction; prepare≠predict)")
    macro_bullets.append(f"S8_H9 soft-linked={s8_h9} (no Stage 8 valuation redo)")
    if primary in {"A8", "A9"}:
        macro_bullets.append("A8/A9 mid-cycle honesty mandatory soft — windfall≠franchise")
        if cycle_class == "late" or cues.get("peak_cycle_language"):
            s9_carries.append("S9_HFA_CYCLE_PEAK_RISK")
    if semantic and semantic.macro_cycle_notes:
        macro_bullets.append(f"macro_notes={semantic.macro_cycle_notes[:220]}")
    macro_bullets.append("ER9 capital-cycle merged into ER1+ER7 — no standalone scored lens")
    er_lenses.append(
        ERLensResult(
            lens_id="ER7",
            lens_name="Macro / Cycle Context",
            summary=f"cycle_position_class={cycle_class}",
            why="Exposure+context not forecast; soft-link S8_H9_*; Marks prepare≠predict",
            labels={
                "cycle_position_class": cycle_class,
                "not_a_prediction": True,
                "s8_h9": s8_h9,
            },
            evidence=[f.excerpt or f.topic for f in macro_hits[:3]],
            mechanism="macro_or_cycle_demand_sensitivity",
            exposure="volume_mix_or_price_under_cycle",
            evidence_label=_evidence_kind_for(semantic, "macro_cycle"),
        )
    )
    ans(
        "S9-M7",
        "answered",
        f"ER7 cycle_class={cycle_class}; S8_H9={s8_h9}",
        ["ER7"],
    )

    # ER8 breakers
    breakers, breaker_monitors = _build_breakers(
        gate2=gate2,
        semantic=semantic,
        primary=primary,
        concentration=concentration,
        regulatory_posture=regulatory_posture,
    )
    for m in breaker_monitors:
        monitors.append(m)
    if any(b.active_fact for b in breakers):
        s9_carries.append("S9_HFA_THESIS_BREAKER_ACTIVE")
    breaker_fp_bullets.append(
        f"breaker_count={len(breakers)} (prefer 3–7; NOT giant risk register)"
    )
    for b in breakers:
        breaker_fp_bullets.append(
            f"{b.breaker_id}: {b.mechanism[:160]} [{b.evidence_label}]"
        )
    fp_tags = _fp_tags(
        semantic=semantic, primary=primary, s8_h9=s8_h9, breakers=breakers
    )
    breaker_fp_bullets.append(
        f"FP-E tags={[t['id'] for t in fp_tags]} — flags not auto-fails; no count→outcome"
    )
    er_lenses.append(
        ERLensResult(
            lens_id="ER8",
            lens_name="Thesis Breakers & Monitoring",
            summary=f"{len(breakers)} falsifiers assembled",
            why="Small observable set; deepen Gate2 monitors; not encyclopedic doom",
            labels={"count": len(breakers), "not_giant_register": True, "max": 7},
            evidence=[b.breaker_id for b in breakers],
            mechanism="observable_falsifiers",
            exposure="thesis_break_if_indicators_trigger",
            evidence_label="INFERENCE",
            escalate_to_human=any(b.active_fact for b in breakers),
        )
    )
    ans(
        "S9-M8",
        "answered" if 3 <= len(breakers) <= 7 else "partial",
        f"ER8 breakers={len(breakers)} (target 3–7)",
        ["ER8"],
    )

    # Conflicts with S1–8
    if unresolved_major_conflict:
        conflicts.append("Unresolved Normalized major conflict surfaced — no silent override")
    if thesis_summary and gate2.get("advantage_type") is None and stage1_artifact:
        conflicts.append(
            "Stage 1 artifact present but Gate2 advantage_type empty — thesis/Gate2 tension monitor"
        )
    # Soft: do not treat missing Stage 8 as conflict
    missing_prior = [
        name
        for name, art in (
            ("stage5", stage5_artifact),
            ("stage6", stage6_artifact),
        )
        if art is None
    ]
    if missing_prior:
        monitors.append(f"Prior artifacts absent (soft): {missing_prior} — Stage 9 still runs")
    ans(
        "S9-M9",
        "answered",
        f"conflicts={conflicts or 'none'}; no silent S1–8 override; no rewrite",
        ["conflicts"],
    )

    s9_carries = [c for c in dict.fromkeys(s9_carries) if c in S9_HFA_CARRIES]

    usable = bool(periods_sorted) or bool(semantic and semantic.filled)
    # RR escalate paths (FACT only): quantitative material concentration_customer OR primary-legal.
    # Largest-customer alone without revenue-share quant → NOT escalate.
    # Soft A8/LOW, commodity class, CLAIM count, inactive GEO/CYCLE breakers → NOT escalate.
    conc_escalate = any(
        f.escalate_to_human
        and f.topic == "concentration_customer"
        and f.excerpt
        and len(f.excerpt) > 40
        and excerpt_has_concentration_quant(f.excerpt)
        for f in (semantic.findings if semantic else [])
    )
    primary_legal_escalate = any(
        f.escalate_to_human
        and f.topic in {"antitrust", "regulatory"}
        and f.excerpt
        and len(f.excerpt) > 40
        and excerpt_has_primary_legal(f.excerpt)
        for f in (semantic.findings if semantic else [])
    )
    escalate = conc_escalate or primary_legal_escalate
    esc_bits = []
    if primary_legal_escalate:
        esc_bits.append("primary-legal FACT")
    if conc_escalate:
        esc_bits.append("quantitative material concentration FACT")
    escalate_reason = (
        "semantic escalate_to_human on "
        + " + ".join(esc_bits)
        + " (not soft A8/LOW / commodity class / CLAIM count / inactive GEO-CYCLE)"
        if esc_bits
        else None
    )

    process_outcome, outcome_why = _decide_outcome(
        gate0_class=gate0_class,
        usable=usable,
        semantic_filled=bool(semantic and semantic.filled),
        breakers=breakers,
        carries=s9_carries,
        conflicts=conflicts,
        escalate=escalate,
        concentration=concentration,
        escalate_reason=escalate_reason,
    )
    why.extend(outcome_why)
    assert process_outcome in STAGE9_OUTCOMES
    why.append(
        f"process_outcome={process_outcome} (SYSTEM_INFERENCE from ER synthesis; "
        "terminates_later_stages=False; no final FA synthesis; no BUY/SELL)"
    )

    for c in s9_carries:
        carry.append(f"Final-FA carry: {c}")
    if s8_h9:
        carry.append(f"Forward S8_H9={s8_h9} (no valuation redo)")
    for b in breakers:
        if b.active_fact:
            carry.append(f"Active FACT breaker {b.breaker_id}: {b.mechanism[:120]}")

    ans(
        "S9-M10",
        "answered",
        (
            f"process_outcome={process_outcome}; S9_HFA={s9_carries}; FP-E={[t['id'] for t in fp_tags]}; "
            "NON-TERMINATING; no final FA synthesis; no scores/colors/BUY-SELL"
        ),
        [process_outcome, "terminates_later_stages=False"],
    )

    for qid, qtext in SHOULD_QUESTIONS:
        if qid == "S9-S1":
            ans(
                qid,
                "answered",
                f"secondary_traits={(archetype.secondary_traits if archetype else [])}",
                must=False,
            )
        elif qid == "S9-S2":
            ans(qid, "answered", "ER9 merged into ER1+ER7", must=False)
        elif qid == "S9-S3":
            ans(
                qid,
                "answered",
                f"windfall≠franchise soft for primary={primary}",
                must=False,
            )
        elif qid == "S9-S4":
            ans(
                qid,
                "answered",
                f"disclosed_customer={calc.metrics.get('disclosed_top_customer_pct')}; else semantic",
                must=False,
            )
        elif qid == "S9-S5":
            ans(qid, "answered", f"S8_H9 forwarded={s8_h9}", must=False)
        else:
            ans(qid, "partial", qtext[:120], must=False)

    what_strong = []
    if "competition" in topics or "industry_structure" in topics:
        what_strong.append("Competition / structure semantic present from filings")
    if reg_hits:
        what_strong.append("Regulatory/antitrust language captured with evidence labels")
    if 3 <= len(breakers) <= 7:
        what_strong.append(f"ER8 falsifier set sized honestly ({len(breakers)})")

    what_break = [b.mechanism for b in breakers[:5]]
    if not what_break:
        what_break.append("External envelope under-analyzed (semantic thin)")

    if not (semantic and semantic.filled):
        monitors.append("Deepen Stage 9 semantic — 10-K Business/Competition/Risk Factors")
    if gate2.get("present") is False:
        monitors.append("Stage 1 Gate2 hypothesis pack absent — ER2/ER8 limited")
    for g in gaps:
        monitors.append(g)

    thesis_coh = "unknown"
    if moat_stressed:
        thesis_coh = "strains"
    elif gate2.get("present") and process_outcome == "PROCEED":
        thesis_coh = "supports"

    refuse = None
    if gate0_class != "operating":
        refuse = f"Gate0={gate0_class} — Stage 9 v1 operating OpCo only"

    if business_notes and not gate2.get("present"):
        monitors.append(
            "business_notes present without Gate2 pack — do not invent Stage 9 thesis"
        )

    return Stage9Report(
        ticker=ticker,
        date=utc_now(),
        periods_used=periods_used,
        sources=sources,
        process_outcome=process_outcome,
        why_bullets=why,
        carry_forward_concerns=list(dict.fromkeys(carry)),
        industry_structure_bullets=industry_bullets,
        moat_durability_bullets=moat_bullets,
        disruption_bullets=disruption_bullets,
        concentration_bullets=concentration_bullets,
        regulatory_geo_bullets=reg_geo_bullets,
        macro_cycle_bullets=macro_bullets,
        breaker_fp_bullets=breaker_fp_bullets,
        false_positive_tags=fp_tags,
        er_lenses=er_lenses,
        thesis_breakers=breakers,
        archetype=archetype,
        concentration_labels=concentration,
        cycle_position_class=cycle_class,
        regulatory_posture=regulatory_posture,
        s1_8_conflicts=conflicts,
        s8_h9_carries_forwarded=s8_h9,
        s9_hfa_carries=s9_carries,
        gate2_hypothesis_consumed={
            "present": bool(gate2.get("present")),
            "advantage_type": gate2.get("advantage_type"),
            "kill_shot_primary": gate2.get("kill_shot_primary"),
            "kill_shot_secondary": gate2.get("kill_shot_secondary"),
            "monitoring_variables": gate2.get("monitoring_variables") or [],
            "no_thesis_restatement": True,
        },
        what_is_strong=what_strong,
        what_can_break=what_break,
        monitors=list(dict.fromkeys(monitors)),
        missing_ambiguous=list(
            dict.fromkeys(
                gaps + [f"{k}: {v}" for k, v in (calc.null_reasons or {}).items()]
            )
        ),
        question_answers=answers,
        calc=calc,
        semantic=semantic,
        terminates_later_stages=False,
        refuse_reason=refuse,
        thesis_coherence=thesis_coh,
        no_final_fa_synthesis=True,
    )
