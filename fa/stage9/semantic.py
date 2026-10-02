"""Stage 9 semantic — 10-K Business / Competition / Risk Factors heuristic MVP.

Source-first. No industry warehouse. No LLM required in dry-run.
Evidence labels: FACT | GUIDANCE | CLAIM | INFERENCE | UNKNOWN.
Risk triple: mechanism + exposure + evidence.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .. import config, storage
from ..models import Stage9SemanticFinding, Stage9SemanticReview
from ..sec_client import get_filing_document

CHECKLIST_TOPICS = [
    "industry_structure",
    "competition",
    "moat_attack_surface",
    "disruption",
    "concentration_customer",
    "concentration_supplier",
    "concentration_geo",
    "regulatory",
    "antitrust",
    "environmental_permitting",
    "geopolitical",
    "macro_cycle",
    "thesis_breaker_seed",
]

# topic, patterns, classification, evidence_kind, escalate, dimension, er_lens
_KEYWORD_MAP: list[tuple[str, list[str], str, str, bool, str | None, str | None]] = [
    (
        "industry_structure",
        [
            r"\bcompetition\b.{0,40}\b(?:industry|market|payments|network)",
            r"\bthe\s+(?:global\s+)?(?:payments|industry)\s+(?:is|continues|remains)",
            r"\bcompetitive\s+(?:landscape|environment|position)",
            r"\bmarket\s+(?:structure|participants|share)",
            r"\bbarriers?\s+to\s+entry\b",
            r"\bnetwork\s+effects?\b",
            r"\btwo[- ]sided\s+(?:market|network|platform)",
        ],
        "competition",
        "CLAIM",
        False,
        "structure",
        "ER1",
    ),
    (
        "competition",
        [
            r"\bcompete(?:s|d)?\s+with\b",
            r"\bcompetitors?\s+(?:include|such\s+as|may)",
            r"\bcompetitive\s+pressures?\b",
            r"\brival(?:ry|s)?\b",
            r"\bother\s+(?:payment|card)\s+networks?\b",
        ],
        "competition",
        "CLAIM",
        False,
        "structure",
        "ER1",
    ),
    (
        "moat_attack_surface",
        [
            r"\bmulti[- ]hom",
            r"\bswitching\s+costs?\b",
            r"\bdisintermediat",
            r"\balternative\s+(?:payment|networks?|rails?)",
            # Competitive new-entrants only — exclude pension "closed to new entrants"
            r"(?:competitive|industry|market|barrier).{0,60}\bnew\s+entrants?\b",
            r"\bnew\s+entrants?\b.{0,60}(?:competitive|industry|market|barrier)",
            # Avoid GAAP "should not be relied upon as substitutes for"
            r"\bproduct\s+substitut(?:e|es|ion)\b",
            r"\bsubstitut(?:e|es)\s+(?:product|service|payment|network)",
        ],
        "risk_factors",
        "CLAIM",
        False,
        "moat",
        "ER2",
    ),
    (
        "disruption",
        [
            r"\bfintechs?\b",
            r"\bdisrupt(?:ion|ive|ing)?\b",
            r"\btechnological\s+(?:change|advances?|innovation)",
            r"\bblockchain\b|\bcrypto(?:currency)?\b|\bdigital\s+currenc",
            r"\bartificial\s+intelligence\b|\b\bAI\b.{0,40}\b(?:disrupt|compet|substitut)",
            r"\bnew\s+technologies?\b.{0,40}\b(?:compet|threat|displac)",
        ],
        "risk_factors",
        "CLAIM",
        False,
        "disruption",
        "ER3",
    ),
    (
        "concentration_customer",
        [
            r"\bcustomer\s+concentration\b",
            r"\blargest\s+customer\b",
            r"\btop\s+(?:\d+|ten|five)\s+customers?\b",
            r"\bsignificant\s+portion\s+of\s+(?:our\s+)?(?:net\s+)?(?:revenues?|sales).{0,60}\bcustomer",
            r"\bdependence\s+on\s+(?:a\s+)?(?:few|small\s+number\s+of)\s+customers?\b",
        ],
        "risk_factors",
        "FACT",
        False,  # escalate only with quantitative revenue-share materiality (see _findings_from_text)
        "concentration",
        "ER4",
    ),
    (
        "concentration_supplier",
        [
            r"\bsupplier\s+concentration\b",
            r"\bsingle[- ]source\s+supplier\b",
            r"\bkey\s+suppliers?\b",
            r"\bdependence\s+on\s+(?:a\s+)?(?:few|limited)\s+suppliers?\b",
        ],
        "risk_factors",
        "FACT",
        False,
        "concentration",
        "ER4",
    ),
    (
        "concentration_geo",
        [
            r"\bgeographic\s+concentration\b",
            r"\brevenues?\s+from\s+(?:outside|international|foreign)",
            r"\boperations?\s+in\s+(?:emerging|international)\s+markets?\b",
            r"\bcross[- ]border\b",
            r"\bChina\b.{0,80}\b(?:revenue|operations?|risk|demand)",
        ],
        "risk_factors",
        "CLAIM",
        False,
        "concentration",
        "ER4",
    ),
    (
        "regulatory",
        [
            r"\bgovernment\s+regulation\b",
            r"\bregulatory\s+(?:environment|developments?|authorit|scrutiny)",
            r"\bcompliance\s+with\s+(?:laws?|regulations?)\b",
            r"\bprivacy\s+(?:law|regulation|rules?)\b",
            r"\binterchange\b.{0,40}\b(?:regulat|cap|fee)",
            r"\blicens(?:e|ing)\s+requirements?\b",
        ],
        "risk_factors",
        "CLAIM",  # FACT only for named primary-legal / specific mandate — not GOVERNMENT REGULATION boilerplate
        False,
        "regulatory",
        "ER5",
    ),
    (
        "antitrust",
        [
            # Prefer named agency / primary-legal patterns BEFORE generic "antitrust" boilerplate
            r"\bFTC\b",
            r"\bDOJ\b|\b(?:U\.S\.\s+)?Department\s+of\s+Justice\b",
            r"\bEuropean\s+Commission\b.{0,40}\b(?:antitrust|compet|settlement|decision)",
            r"\bright[- ]to[- ]repair\b",
            r"\bsettlement\s+with\s+the\s+(?:FTC|DOJ|Department\s+of\s+Justice|European\s+Commission)\b",
            r"\bconsent\s+(?:decree|order)\b",
            r"\bantitrust\b",
            r"\bcompetition\s+law\b",
            r"\banti[- ]competitive\b",
            r"\bmonopol(?:y|ization)\b",
        ],
        "legal",
        "CLAIM",  # FACT only when primary-legal markers (see _findings_from_text)
        False,  # escalate only when primary-legal open action
        "regulatory",
        "ER5",
    ),
    (
        "environmental_permitting",
        [
            r"\benvironmental\s+(?:regulation|regulations|law|laws|liabilit(?:y|ies)|permit|permits|approvals?)\b",
            r"\bpermitting\b",
            r"\bmine\s+(?:approval|approvals|permit|permits|licen[cs]e|licen[cs]es)\b",
            r"\blicen[cs](?:e|es|ing)\s+(?:of\s+)?(?:mines?|mining|operations?)\b",
            r"\b(?:closure|rehabilitation|reclamation)\s+(?:obligat|liabilit|plan|provision|requirements?)",
            r"\bremediation\b",
            r"\btailings\b",
            r"\benvironmental\s+(?:litigation|claims?|proceedings?|enforcement)\b",
            r"\bdelays?\s+in\s+approvals?\b",
        ],
        "risk_factors",
        "CLAIM",  # FACT only with primary-legal / named regulator action
        False,
        "regulatory",
        "ER5",
    ),
    (
        "geopolitical",
        [
            r"\bgeopolitical\b",
            r"\bsanctions?\b",
            r"\bexport\s+controls?\b",
            r"\btrade\s+(?:war|tensions?|restrictions?)\b",
            r"\bpolitical\s+(?:instability|unrest|risk)",
            r"\bheightened\s+geopolitical\s+tensions?\b",
        ],
        "risk_factors",
        "CLAIM",
        False,
        "geo",
        "ER6",
    ),
    (
        "macro_cycle",
        [
            r"\beconomic\s+(?:conditions?|downturn|recession|uncertainty)",
            r"\bmacroeconomic\b",
            r"\bcyclical\b",
            r"\bconsumer\s+spend(?:ing)?\b",
            r"\binflation(?:ary)?\s+(?:pressure|environment|risk)",
            r"\brising\s+interest\s+rates?\b",
            r"\bpandemic\b|\bCOVID",
        ],
        "risk_factors",
        "CLAIM",
        False,
        "macro",
        "ER7",
    ),
    (
        "thesis_breaker_seed",
        [
            r"\bif\s+we\s+(?:are\s+unable|fail)\s+to\b",
            r"\bcould\s+(?:materially\s+)?(?:adversely\s+)?affect\b",
            r"\bmay\s+not\s+be\s+successful\b",
            r"\bloss\s+of\s+(?:key\s+)?(?:customers?|partners?|clients?)\b",
        ],
        "risk_factors",
        "CLAIM",
        False,
        "breaker",
        "ER8",
    ),
]


def html_to_text(raw: str) -> str:
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t)
    return t


def placeholder_stage9_semantic() -> Stage9SemanticReview:
    return Stage9SemanticReview(review_source="placeholder", filled=False)


def load_stage9_semantic_from_fixture(path: Path) -> Stage9SemanticReview:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    findings = []
    for f in data.get("findings") or []:
        if isinstance(f, dict):
            findings.append(
                Stage9SemanticFinding(
                    **{k: v for k, v in f.items() if k in Stage9SemanticFinding.__dataclass_fields__}
                )
            )
    return Stage9SemanticReview(
        findings=findings,
        industry_structure_notes=data.get("industry_structure_notes"),
        competition_notes=data.get("competition_notes"),
        moat_stress_notes=data.get("moat_stress_notes"),
        disruption_notes=data.get("disruption_notes"),
        concentration_notes=data.get("concentration_notes"),
        regulatory_notes=data.get("regulatory_notes"),
        geopolitical_notes=data.get("geopolitical_notes"),
        macro_cycle_notes=data.get("macro_cycle_notes"),
        breaker_notes=data.get("breaker_notes"),
        conflict_notes=data.get("conflict_notes"),
        checklist_coverage=list(data.get("checklist_coverage") or []),
        review_source=data.get("review_source") or "fixture",
        filled=bool(data.get("filled", True)),
    )


def semantic_text_blob(semantic: Stage9SemanticReview | None) -> str:
    if not semantic:
        return ""
    parts = [
        semantic.industry_structure_notes,
        semantic.competition_notes,
        semantic.moat_stress_notes,
        semantic.disruption_notes,
        semantic.concentration_notes,
        semantic.regulatory_notes,
        semantic.geopolitical_notes,
        semantic.macro_cycle_notes,
        semantic.breaker_notes,
        semantic.conflict_notes,
    ]
    for f in semantic.findings:
        parts.append(f.topic)
        parts.append(f.excerpt)
        parts.append(f.mechanism)
        parts.append(f.exposure)
    return " ".join(p for p in parts if p)



# Primary-legal markers: named agency action / order / judgment / open litigation with identity.
# Generic Risk Factors "subject to antitrust law" boilerplate is NOT primary-legal.
_PRIMARY_LEGAL_RE = re.compile(
    r"""
    (?:
        \b(?:U\.S\.\s+)?Department\s+of\s+Justice\b
        |\bDOJ\b
        |\bFTC\b
        |\bEuropean\s+Commission\b
        |\bCompetition\s+Appeal\s+Tribunal\b|\b\bCAT\b.{0,40}(?:antitrust|interchange|compet)
        |\bconsent\s+(?:decree|order)\b
        |\b(?:final\s+)?judgment\b
        |\bhanded\s+down\b
        |\blawsuit\s+filed\b
        |\bcomplaint\s+(?:is\s+)?(?:brought|filed|served)\b
        |\bserved\s+with\s+a\s+(?:class\s+)?(?:action\s+)?claim\b
        |\bMDL\s*\d+
        |\bInterchange\s+Multidistrict\s+Litigation\b
        |\bNote\s+\d+[—\-]Legal\s+Matters\b
        |\bright[- ]to[- ]repair\b.{0,80}\b(?:FTC|DOJ|lawsuit|settlement|complaint)\b
        |\b(?:FTC|DOJ|lawsuit|settlement|complaint)\b.{0,80}\bright[- ]to[- ]repair\b
        |\bsettlement\s+with\s+the\s+(?:FTC|DOJ|Department\s+of\s+Justice|European\s+Commission|plaintiff\s+states)\b
        |\bentered\s+into\s+a\s+settlement\s+with\s+the\s+FTC\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_REG_BOILERPLATE_RE = re.compile(
    r"""
    (?:
        subject\s+to\s+complex\s+and\s+evolving
        |most\s+significant\s+government\s+regulations\s+that\s+impact
        |violations\s+of\s+competition\s+and\s+antitrust\s+law
        |government\s+regulation\s+as\s+a\s+global
        |these\s+are\s+referred\s+to\s+as\s+["“]actions["”]
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_DISRUPTION_SUBSTANCE_RE = re.compile(
    r"""
    (?:
        \bdisintermediat
        |\bmulti[- ]hom
        |\balternative\s+(?:payment|rails?|networks?)
        |\bshare\s+(?:loss|erosion|pressure|shift)
        |\bpricing\s+pressure
        |\bthreat(?:en(?:s|ed|ing)?)?\s+to\s+(?:our|the)\s+(?:business|model|network)
        |\bcould\s+(?:materially\s+)?(?:adversely\s+)?affect.{0,40}\b(?:compet|disrupt|fintech)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Geo MECHANISM cues (shock). High China revenue/demand/market/pathway/growth ≠ geo.
# Those are ER4 end-market / customer concentration — do not auto-fire GEO_MATERIAL.
_GEO_SUBSTANCE_RE = re.compile(
    r"""
    (?:
        \bsanctions?\b
        |\bexport\s+controls?\b
        |\bcross[- ]border\s+(?:volume|revenue|payment|ops|operations?)
        |\boperations?\s+in\s+[A-Z][a-z]+
        |\bfootprint\b
        # Country + geo shock only (war/conflict/sanction/export/ops) — NOT demand/market/pathway/growth/revenue
        |\b(?:Russia|China|Ukraine|Iran)\b.{0,80}\b(?:war|conflict|sanction|export\s+controls?|ops|operations?)
        |\b(?:war|conflict|sanction|export\s+controls?|ops|operations?).{0,80}\b(?:Russia|China|Ukraine|Iran)\b
        |\bRussia[- ]Ukraine\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Geo EXPOSURE / footprint cues — required (with substance) for S9_HFA_GEO_MATERIAL.
# Russia-Ukraine commodity-price volatility alone ≠ company geo footprint exposure.
_GEO_FOOTPRINT_RE = re.compile(
    r"""
    (?:
        \bfootprint\b
        |\boperations?\s+in\b
        |\bcross[- ]border\s+(?:volume|revenue|payment|ops|operations?)
        |\b(?:suspended|curtail(?:ed|ing)?|ceased)\s+operations?\b
        |\bsanctions?\b.{0,60}\b(?:operations?|revenue|volume|sales|exports?|business)
        |\b(?:operations?|revenue|volume|sales|exports?|business).{0,60}\bsanctions?\b
        |\bexport\s+controls?\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# Quantitative concentration materiality — largest-customer alone ≠ automatic material.
# Require disclosed revenue/sales share markers (%, significant portion of revenue, etc.).
_CONC_QUANT_RE = re.compile(
    r"""
    (?:
        (?:\d+(?:\.\d+)?\s*%|\bpercent(?:age)?\b).{0,50}
            (?:of\s+(?:our\s+)?(?:net\s+)?(?:revenues?|sales|turnover))
        |(?:significant|substantial|material)\s+portion\s+of\s+(?:our\s+)?(?:net\s+)?(?:revenues?|sales)
        |(?:revenues?|sales).{0,40}(?:from|attributable\s+to).{0,40}(?:\d+(?:\.\d+)?\s*%|\bpercent)
        |(?:top|largest)\s+(?:\d+|ten|five)\s+customers?.{0,80}
            (?:\d+(?:\.\d+)?\s*%|percent|significant\s+portion)
        |(?:accounts?\s+for|represented|contributed).{0,40}
            (?:\d+(?:\.\d+)?\s*%|percent).{0,40}(?:revenue|sales)
        |(?:no\s+single\s+customer|customer\s+concentration).{0,60}
            (?:\d+(?:\.\d+)?\s*%|percent|significant\s+portion)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def excerpt_has_concentration_quant(excerpt: str | None) -> bool:
    """True when excerpt discloses quantitative customer/revenue-share concentration.

    Largest-customer / named-partner identity alone is NOT automatic material concentration.
    """
    if not excerpt:
        return False
    return bool(_CONC_QUANT_RE.search(excerpt))


def excerpt_has_primary_legal(excerpt: str | None) -> bool:
    """True when excerpt cites named agency action / order / judgment / open case identity."""
    if not excerpt:
        return False
    return bool(_PRIMARY_LEGAL_RE.search(excerpt))


def excerpt_is_reg_boilerplate(excerpt: str | None) -> bool:
    """True for generic GOVERNMENT REGULATION / Risk Factors intro without named action."""
    if not excerpt:
        return True
    if excerpt_has_primary_legal(excerpt):
        return False
    return bool(_REG_BOILERPLATE_RE.search(excerpt)) or not (
        re.search(r"\b(?:filed|served|judgment|consent|MDL|DOJ|FTC)\b", excerpt, re.I)
    )


def excerpt_has_disruption_substance(excerpt: str | None) -> bool:
    """Mechanism-level disruption — not mere fintech/partner ecosystem naming."""
    if not excerpt:
        return False
    return bool(_DISRUPTION_SUBSTANCE_RE.search(excerpt))


def excerpt_has_geo_substance(excerpt: str | None) -> bool:
    """Geo mechanism cue — not bare 'geopolitical tensions'; not China demand/concentration."""
    if not excerpt:
        return False
    return bool(_GEO_SUBSTANCE_RE.search(excerpt))


def excerpt_has_geo_footprint(excerpt: str | None) -> bool:
    """Company geo exposure/footprint language — required with substance for GEO_MATERIAL HFA."""
    if not excerpt:
        return False
    return bool(_GEO_FOOTPRINT_RE.search(excerpt))


def _findings_from_text(
    text: str,
    *,
    source_label: str,
    accession: str | None = None,
    form: str | None = None,
) -> list[Stage9SemanticFinding]:
    findings: list[Stage9SemanticFinding] = []
    for topic, patterns, classification, kind, escalate, dimension, er_lens in _KEYWORD_MAP:
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if not m:
                continue
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 280)
            excerpt = text[start:end].strip()
            ek = kind
            esc = escalate
            # Concentration: 10-K/20-F named disclosure can be FACT identity, but
            # largest-customer alone ≠ automatic material escalate (need revenue-share quant).
            # Regulatory/antitrust require primary-legal markers — RF boilerplate stays CLAIM.
            if form and form.upper() in {"10-K", "20-F"} and topic in {
                "concentration_customer",
                "concentration_supplier",
            }:
                ek = "FACT"
            if topic == "concentration_customer":
                if excerpt_has_concentration_quant(excerpt):
                    esc = True
                else:
                    # Named largest-customer / partnership without disclosed % → monitor/uncertainty
                    esc = False
            if topic in {"antitrust", "regulatory", "environmental_permitting"}:
                if excerpt_has_primary_legal(excerpt):
                    ek = "FACT"
                    esc = True
                elif excerpt_is_reg_boilerplate(excerpt):
                    ek = "CLAIM"
                    esc = False
                else:
                    # Named mandate / specific development without full case caption → CLAIM, watchable
                    ek = "CLAIM"
                    esc = bool(
                        re.search(
                            r"\b(?:mandat(?:e|ing|ory)|consent|order|litigation|investigation)\b",
                            excerpt,
                            re.I,
                        )
                    )
            # Disruption: only attach mechanism/exposure when substance present (anti FP-E3)
            mech = None
            exp = None
            if topic == "antitrust":
                mech = "competition_law_enforcement_or_private_action"
                exp = "network_rules_fees_or_business_model_constraints"
            elif topic == "disruption":
                if excerpt_has_disruption_substance(excerpt):
                    mech = "technology_or_fintech_attack_on_customer_job"
                    exp = "share_or_pricing_pressure_if_mechanism_realizes"
                else:
                    ek = "CLAIM"
                    esc = False
            elif topic == "moat_attack_surface":
                # Anti FP: pension "closed to new entrants" ≠ moat attack (require substance)
                if excerpt_has_disruption_substance(excerpt) or (
                    re.search(
                        r"(?:competitive|industry|market|barrier|substitut|multi[- ]hom|disintermediat)",
                        excerpt,
                        re.I,
                    )
                    and not re.search(
                        r"\b(?:pension|defined\s+benefit|superannuation)\b",
                        excerpt,
                        re.I,
                    )
                ):
                    mech = "entry_multi_homing_or_substitute_erosion"
                    exp = "claimed_advantage_under_external_pressure"
                else:
                    ek = "CLAIM"
                    esc = False
            elif topic.startswith("concentration"):
                mech = f"{topic.replace('concentration_', '')}_dependency"
                exp = "earnings_or_ops_sensitivity_to_axis"
            elif topic == "environmental_permitting":
                mech = "environmental_permitting_closure_or_remediation_constraint"
                exp = "approvals_licence_ops_or_closure_liability"
            elif topic == "geopolitical":
                if excerpt_has_geo_substance(excerpt):
                    mech = "sanctions_export_controls_or_political_shock"
                    exp = "cross_border_volume_or_ops_footprint"
                else:
                    ek = "CLAIM"
                    esc = False
            elif topic == "macro_cycle":
                mech = "demand_or_spend_cycle_sensitivity"
                exp = "volume_or_mix_under_macro_stress"
            if topic == "concentration_customer" and not esc:
                mat_j = "unclear"
                mat_r = (
                    "Largest-customer / named customer alone without disclosed revenue "
                    "share — monitoring/uncertainty (not automatic material concentration)"
                )
            elif esc and topic in {"antitrust", "regulatory", "environmental_permitting"}:
                mat_j = "watchable"
                mat_r = "Primary-legal / named open regulatory action — human judgment"
            elif esc and topic == "concentration_customer":
                mat_j = "watchable"
                mat_r = (
                    "Quantitative concentration disclosure (revenue/sales share) — "
                    "human judgment"
                )
            elif esc:
                mat_j = "watchable"
                mat_r = "Material concentration language — human judgment"
            else:
                mat_j = "not_assessed"
                mat_r = ""
            findings.append(
                Stage9SemanticFinding(
                    topic=topic,
                    citation=f"{source_label}~/{pat}/",
                    classification=classification,
                    evidence_kind=ek,
                    materiality_judgment=mat_j,
                    materiality_reason=mat_r,
                    escalate_to_human=esc,
                    excerpt=excerpt[:520],
                    accession=accession,
                    section=form,
                    dimension=dimension,
                    er_lens=er_lens,
                    mechanism=mech,
                    exposure=exp,
                )
            )
            # Wave 3 / B2 / SD-W3-ER5: for legal/regulatory topics, keep scanning for
            # additional MATERIAL named facts (do not stop at first generic antitrust hit).
            # Other topics retain one-hit-per-topic behavior.
            if topic in {"antitrust", "regulatory", "environmental_permitting"}:
                continue
            break
    return findings


def _filing_metas(ticker: str, root: Path | None) -> list[dict[str, Any]]:
    cdir = storage.company_dir(ticker, root)
    man = storage.load_source_manifest(ticker, root)
    out = []
    for s in man.get("sources", []):
        form = str(s.get("form") or "")
        if (
            s.get("kind") in {"sec_filing", "sec_filing_manual"}
            or form in {"10-K", "10-Q", "20-F", "8-K"}
        ):
            out.append(s)
    filings_dir = cdir / "Source" / "filings"
    if filings_dir.exists():
        for meta_path in filings_dir.glob("*.json"):
            try:
                out.append(json.loads(meta_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    return out


def _enrich_notes(review: Stage9SemanticReview) -> Stage9SemanticReview:
    by_topic: dict[str, list[Stage9SemanticFinding]] = {}
    for f in review.findings:
        by_topic.setdefault(f.topic, []).append(f)

    def first_excerpt(topic: str, *, prefer_primary_legal: bool = False) -> str | None:
        hits = by_topic.get(topic) or []
        if prefer_primary_legal:
            ranked = sorted(
                hits,
                key=lambda h: (
                    0 if excerpt_has_primary_legal(h.excerpt) else 1,
                    0 if (h.evidence_kind == "FACT") else 1,
                ),
            )
            hits = ranked
        for h in hits:
            if h.excerpt:
                return h.excerpt[:240]
        return None

    review.industry_structure_notes = first_excerpt("industry_structure") or first_excerpt(
        "competition"
    )
    review.competition_notes = first_excerpt("competition")
    review.moat_stress_notes = first_excerpt("moat_attack_surface")
    review.disruption_notes = first_excerpt("disruption")
    conc_parts = [
        first_excerpt("concentration_customer"),
        first_excerpt("concentration_supplier"),
        first_excerpt("concentration_geo"),
    ]
    review.concentration_notes = "; ".join(p for p in conc_parts if p) or None
    reg_parts = [
        first_excerpt("regulatory", prefer_primary_legal=True),
        first_excerpt("antitrust", prefer_primary_legal=True),
        first_excerpt("environmental_permitting"),
    ]
    review.regulatory_notes = "; ".join(p for p in reg_parts if p) or None
    review.geopolitical_notes = first_excerpt("geopolitical")
    review.macro_cycle_notes = first_excerpt("macro_cycle")
    review.breaker_notes = first_excerpt("thesis_breaker_seed")

    covered = sorted({f.topic for f in review.findings if f.topic in CHECKLIST_TOPICS})
    review.checklist_coverage = covered
    # filled when we have multi-lens coverage from filings (not single TOC hit)
    substantive = [
        f
        for f in review.findings
        if f.topic in CHECKLIST_TOPICS and f.excerpt and len(f.excerpt) > 40
    ]
    review.filled = len(substantive) >= 3
    return review


def semantic_cues_from_review(semantic: Stage9SemanticReview | None) -> dict[str, Any]:
    """Map semantic hits → calc concentration / cycle soft cues (not gates)."""
    cues: dict[str, Any] = {
        "customer_opaque": True,
        "supplier_opaque": True,
        "geo_opaque": True,
        "product_opaque": True,
        "distribution_opaque": True,
    }
    if not semantic:
        return cues
    topics = {f.topic for f in semantic.findings}
    blob = semantic_text_blob(semantic).lower()

    if "concentration_customer" in topics:
        cues["customer_opaque"] = False
        # Largest-customer alone ≠ high/material — require quantitative revenue-share cues
        cust_findings = [f for f in semantic.findings if f.topic == "concentration_customer"]
        if any(excerpt_has_concentration_quant(f.excerpt) for f in cust_findings):
            cues["customer_high"] = True
        elif "significant portion" in blob and any(
            x in blob for x in ("revenue", "sales", "turnover")
        ):
            cues["customer_high"] = True
        # else: named customer without share → leave non-high (label → unknown/uncertainty)
    if "concentration_supplier" in topics:
        cues["supplier_opaque"] = False
        cues["supplier_moderate"] = True
        if "single-source" in blob or "single source" in blob:
            cues["supplier_high"] = True
    if "concentration_geo" in topics:
        cues["geo_opaque"] = False
        cues["geo_moderate"] = True
        if "china" in blob:
            cues["geo_high"] = True
    if "macro_cycle" in topics:
        if any(x in blob for x in ("recession", "downturn", "cyclical")):
            cues["mid_cycle_honesty"] = True
        if any(x in blob for x in ("peak", "record high", "historically high")):
            cues["peak_cycle_language"] = True
    return cues


def persist_stage9_semantic(
    ticker: str,
    review: Stage9SemanticReview,
    *,
    root: Path | None = None,
) -> Path:
    cdir = storage.company_dir(ticker, root)
    notes = cdir / "Source" / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    path = notes / "stage9_semantic_review.json"
    storage.write_json(path, review.to_dict())
    return path


def run_stage9_semantic_from_filings(
    ticker: str,
    *,
    root: Path | None = None,
    persist: bool = True,
) -> Stage9SemanticReview:
    """Production-like Stage 9 semantic: scan 10-K/10-Q/20-F for external-risk topics."""
    ticker = ticker.upper()
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)
    meta = storage.load_meta(ticker, root)
    cik = str(meta.get("cik") or "").zfill(10) if meta.get("cik") else None

    findings: list[Stage9SemanticFinding] = []
    allowed = {"10-K", "10-Q", "20-F", "8-K"}
    for fmeta in _filing_metas(ticker, root):
        form = str(fmeta.get("form") or "")
        if form not in allowed:
            continue
        accession = fmeta.get("accession")
        primary = fmeta.get("primary_document")
        if not accession or not primary:
            continue
        cik_use = str(fmeta.get("cik") or cik or "").zfill(10)
        path = get_filing_document(cik_use, accession, primary, offline=None)
        if path is None or not path.exists():
            findings.append(
                Stage9SemanticFinding(
                    topic="filing_retrieval",
                    citation=f"accession={accession}; primary={primary}",
                    classification="other",
                    evidence_kind="INFERENCE",
                    materiality_judgment="unclear",
                    materiality_reason="Official filing primary unavailable — semantic incomplete",
                    escalate_to_human=True,
                    accession=accession,
                    section=form,
                )
            )
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        text = html_to_text(raw)
        findings.extend(
            _findings_from_text(
                text,
                source_label=f"{form}:{accession}",
                accession=accession,
                form=form,
            )
        )

    seen: set[str] = set()
    deduped: list[Stage9SemanticFinding] = []
    for f in findings:
        key = f"{f.topic}|{f.accession}|{(f.excerpt or '')[:60]}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)

    review = Stage9SemanticReview(
        findings=deduped,
        review_source="filings_heuristic",
        filled=False,
    )
    review = _enrich_notes(review)
    if persist:
        persist_stage9_semantic(ticker, review, root=root)
    return review


__all__ = [
    "CHECKLIST_TOPICS",
    "placeholder_stage9_semantic",
    "load_stage9_semantic_from_fixture",
    "semantic_text_blob",
    "semantic_cues_from_review",
    "run_stage9_semantic_from_filings",
    "persist_stage9_semantic",
    "html_to_text",
    "excerpt_has_concentration_quant",
    "excerpt_has_primary_legal",
    "excerpt_has_geo_substance",
    "excerpt_has_geo_footprint",
    "excerpt_has_disruption_substance",
]
