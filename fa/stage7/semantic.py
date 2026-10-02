"""Stage 7 semantic — DEF 14A / CD&A / hierarchy / gov / FACT-GUIDANCE-CLAIM-INFERENCE.

Semantic-first CD&A MVP. No compensation DB. No invented thresholds/scores/colors.
Fixture-loadable like Stage 6.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .. import config, storage
from ..models import Stage7SemanticFinding, Stage7SemanticReview
from ..sec_client import get_filing_document

CHECKLIST_TOPICS = [
    "stated_hierarchy",
    "incentive_metrics",
    "ownership_guidelines",
    "governance_structure",
    "related_party",
    "deal_criteria",
    "guidance_delivery",
    "succession",
    "buyback_policy",
    "dividend_policy",
    "debt_motive",
    "clawback",
    "dual_class",
]

# topic, patterns, classification, evidence_kind, escalate, dimension
_KEYWORD_MAP: list[tuple[str, list[str], str, str, bool, str | None]] = [
    (
        "stated_hierarchy",
        [
            # Prefer concrete hierarchy/deployment language before generic "strategy" mentions
            r"\bsubstantial\s+majority\s+of\s+(?:our\s+)?(?:available\s+)?capital\s+toward\b",
            r"\bdisciplined\s+capital\s+deployment\b",
            r"\bapproach\s+to\s+capital\s+allocation\b",
            r"\bcapital\s+allocation\s+(?:priorit|framework|hierarch|polic)",
            r"\bfirst\s+(?:priority|allocate|reinvest)",
            r"\breinvest(?:ment)?\s+(?:in\s+)?(?:the\s+)?(?:business|organic)",
            r"\breturn(?:ing)?\s+(?:excess\s+)?capital\s+to\s+shareholders",
            # CapEx / capital-return hierarchy language (e.g. infra+AI + return of capital)
            r"\breturn of capital to stockholders\b",
            r"\bcapital return program\b",
            r"\binvestments? in infrastructure(?:\s+and\s+AI(?:\s+initiatives)?)?\b",
            r"\bfund our cash commitments for investing\b",
            r"\bincreased investments in infrastructure\b",
            r"\buses?\s+of\s+cash\b",
            r"\bcapital\s+allocation\s+strateg",  # weaker; last among allocation phrases
        ],
        "mdna",
        "MANAGEMENT_CLAIM",
        False,
        "hierarchy",
    ),
    (
        "incentive_metrics",
        [
            r"\bcompensation\s+discussion\s+and\s+analysis\b|\bCD&A\b",
            r"\bperformance\s+(?:share|stock)\s+units?\b|\bPSUs?\b",
            r"\bannual\s+(?:incentive|bonus).{0,40}\b(?:metric|measure|target)",
            r"\bROIC\b.{0,40}\b(?:compensat|incentive|metric)",
            r"\btotal\s+shareholder\s+return\b|\bTSR\b.{0,30}\b(?:compensat|metric)",
            r"\badjusted\s+(?:EBITDA|EPS|operating\s+income).{0,40}\bincentive",
        ],
        "def14a",
        "FACT",
        False,
        "incentives",
    ),
    (
        "ownership_guidelines",
        [
            r"\bstock\s+ownership\s+guidelines?\b",
            r"\bexecutive\s+stock\s+ownership\b",
            r"\bhold(?:ing)?\s+requirements?\b.{0,40}\b(?:CEO|NEO|executive)",
        ],
        "def14a",
        "FACT",
        False,
        "incentives",
    ),
    (
        "clawback",
        [
            r"\bclawback\b",
            r"\bcompensation\s+recovery\s+polic",
            r"\brecoupment\s+polic",
        ],
        "def14a",
        "FACT",
        False,
        "incentives",
    ),
    (
        "governance_structure",
        [
            r"\bdual[- ]class\b",
            r"\bcontrolled\s+company\b",
            r"\bfounder[- ]led\b|\bfamily[- ]controlled\b",
            r"\bsupervoting\b|\bClass\s+[AB]\s+common\s+stock\b",
            r"\bindependent\s+directors?\b",
            r"\bboard\s+(?:composition|structure|independence)\b",
        ],
        "proxy",
        "FACT",
        False,
        "gov",
    ),
    (
        "dual_class",
        [
            r"\bdual[- ]class\s+(?:capital|common|structure)\b",
            r"\bhigh[- ]vote\s+(?:shares?|stock)\b",
        ],
        "proxy",
        "FACT",
        False,
        "gov",
    ),
    (
        "related_party",
        [
            r"\brelated[- ]party\s+transactions?\b",
            r"\btransactions?\s+with\s+related\s+persons?\b",
            r"\bItem\s*404\b",
        ],
        "proxy",
        "FACT",
        True,
        "gov",
    ),
    (
        "deal_criteria",
        [
            r"\bacquisition\s+(?:criteria|strateg|disciplin|framework)",
            r"\bbolt[- ]on\s+acquisitions?\b",
            r"\bstrategic\s+fit\b.{0,40}\bacquisit",
            r"\bintegration\b.{0,40}\bacquisit",
            r"\bearn[- ]?outs?\b",
        ],
        "mdna",
        "MANAGEMENT_CLAIM",
        False,
        "ma",
    ),
    (
        "guidance_delivery",
        [
            # Avoid bare "guidance" (matches accounting Topic / ASC "guidance" noise)
            r"\b(?:revenue|earnings|EPS|margin|outlook)\s+guidance\b",
            r"\b(?:full[- ]year|fiscal(?:\s+year)?)\s+guidance\b",
            r"\bguidance\b.{0,40}\b(?:revenue|earnings|EPS|full[- ]year|fiscal|outlook)\b",
            r"\boutlook\s+for\s+(?:fiscal|the\s+year|full[- ]year)",
            r"\bexpects?\s+(?:revenue|earnings|EPS|margin)\s+to\b",
            r"\breaffirm(?:s|ed)?\s+(?:full[- ]year\s+)?guidance\b",
            r"\bupdated?\s+guidance\b|\bwithdr[ae]w\s+guidance\b",
        ],
        "mdna",
        "GUIDANCE",
        False,
        "comm",
    ),
    (
        "succession",
        [
            r"\bsuccession\s+plann",
            r"\bCEO\s+succession\b",
            r"\bkey[- ]person\b|\bkey\s+man\b",
            r"\bmanagement\s+development\b.{0,40}\bsuccession",
            r"\bleadership\s+transition\b",
        ],
        "proxy",
        "FACT",
        False,
        "succession",
    ),
    (
        "buyback_policy",
        [
            r"\bshare\s+repurchase\s+(?:program|authorization|polic)",
            r"\bstock\s+buyback\b",
            r"\boffset\s+(?:the\s+)?(?:dilutive\s+)?(?:effect\s+of\s+)?(?:share[- ]based|SBC|equity\s+awards)",
            r"\brepurchase.{0,40}\b(?:undervalued|intrinsic|opportunistic)",
        ],
        "mdna",
        "MANAGEMENT_CLAIM",
        False,
        "hierarchy",
    ),
    (
        "dividend_policy",
        [
            r"\bdividend\s+polic",
            r"\bquarterly\s+dividend\b",
            r"\bincrease(?:d)?\s+(?:the\s+)?(?:quarterly\s+)?dividend\b",
            r"\bspecial\s+dividend\b",
        ],
        "mdna",
        "FACT",
        False,
        "hierarchy",
    ),
    (
        "debt_motive",
        [
            r"\bfinanced?\s+(?:the\s+)?acquisition\s+with\s+debt\b",
            r"\brevolver\b|\bcredit\s+facilit",
            r"\brefinanc(?:e|ing)\b",
            r"\bnet\s+leverage\b|\bleverage\s+target\b",
            r"\binvestment[- ]grade\b",
        ],
        "mdna",
        "MANAGEMENT_CLAIM",
        False,
        "debt",
    ),
]


def html_to_text(raw: str) -> str:
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t)
    return t


def placeholder_stage7_semantic() -> Stage7SemanticReview:
    return Stage7SemanticReview(review_source="placeholder", filled=False)


def load_stage7_semantic_from_fixture(path: Path) -> Stage7SemanticReview:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    findings = [
        Stage7SemanticFinding(**f) if isinstance(f, dict) else f
        for f in data.get("findings") or []
    ]
    return Stage7SemanticReview(
        findings=findings,
        stated_hierarchy_notes=data.get("stated_hierarchy_notes"),
        incentive_metrics_notes=data.get("incentive_metrics_notes"),
        ownership_guidelines_notes=data.get("ownership_guidelines_notes"),
        governance_structure_notes=data.get("governance_structure_notes"),
        related_party_notes=data.get("related_party_notes"),
        deal_criteria_notes=data.get("deal_criteria_notes"),
        guidance_delivery_notes=data.get("guidance_delivery_notes"),
        succession_notes=data.get("succession_notes"),
        buyback_policy_notes=data.get("buyback_policy_notes"),
        dividend_policy_notes=data.get("dividend_policy_notes"),
        debt_motive_notes=data.get("debt_motive_notes"),
        checklist_coverage=list(data.get("checklist_coverage") or []),
        review_source=data.get("review_source") or "fixture",
        filled=bool(data.get("filled", True)),
    )


def semantic_text_blob(semantic: Stage7SemanticReview | None) -> str:
    if not semantic:
        return ""
    parts = [
        semantic.stated_hierarchy_notes,
        semantic.incentive_metrics_notes,
        semantic.ownership_guidelines_notes,
        semantic.governance_structure_notes,
        semantic.related_party_notes,
        semantic.deal_criteria_notes,
        semantic.guidance_delivery_notes,
        semantic.succession_notes,
        semantic.buyback_policy_notes,
        semantic.dividend_policy_notes,
        semantic.debt_motive_notes,
    ]
    for f in semantic.findings:
        parts.append(f.topic)
        parts.append(f.excerpt)
        parts.append(f.evidence_kind)
    return " ".join(p for p in parts if p)


def _findings_from_text(
    text: str,
    *,
    source_label: str,
    accession: str | None = None,
    form: str | None = None,
) -> list[Stage7SemanticFinding]:
    findings: list[Stage7SemanticFinding] = []
    lower = text.lower()
    for topic, patterns, classification, kind, escalate, dimension in _KEYWORD_MAP:
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if not m:
                continue
            # Wider window for hierarchy/dividend so labels see consecutive/discretion context
            pre, post = 80, 120
            if topic in {"stated_hierarchy", "dividend_policy", "buyback_policy"}:
                # Dividend Policy sections often put discretion after amounts — need long post
                pre, post = (80, 680) if topic == "dividend_policy" else (100, 420)
            start = max(0, m.start() - pre)
            end = min(len(text), m.end() + post)
            excerpt = text[start:end].strip()
            # Skip risk-factor boilerplate buyback hits; keep searching for authorization body
            if topic == "buyback_policy":
                low_ex = excerpt.lower()
                if (
                    "trading activity in our share repurchase" in low_ex
                    or "fluctuations in the market values of our investments" in low_ex
                ):
                    continue
            # Promote DEF 14A incentive hits to FACT; keep GUIDANCE for outlook
            ek = kind
            if form and form.upper() in {"DEF 14A", "DEFA14A", "DEF14A"} and topic in {
                "incentive_metrics",
                "ownership_guidelines",
                "clawback",
                "governance_structure",
                "related_party",
                "succession",
                "dual_class",
            }:
                ek = "FACT"
            excerpt_cap = 800 if topic == "dividend_policy" else 520
            findings.append(
                Stage7SemanticFinding(
                    topic=topic,
                    citation=f"{source_label}~/{pat}/",
                    classification=classification,
                    evidence_kind=ek,
                    materiality_judgment="watchable" if escalate else "not_assessed",
                    materiality_reason=(
                        "Related-party language — human materiality judgment"
                        if escalate
                        else ""
                    ),
                    escalate_to_human=escalate,
                    excerpt=excerpt[:excerpt_cap],
                    accession=accession,
                    section=form,
                    dimension=dimension,
                )
            )
            break  # one hit per topic per filing
    # Never silently promote CLAIM→FACT: enforce taxonomy on non-proxy forms
    if form and form.upper() in {"8-K", "EX-99", "IR"}:
        for f in findings:
            if f.evidence_kind == "FACT" and f.topic not in {
                "dividend_policy",
                "related_party",
            }:
                # IR/8-K defaults toward CLAIM/GUIDANCE unless already GUIDANCE
                if f.topic == "guidance_delivery":
                    f.evidence_kind = "GUIDANCE"
                elif f.evidence_kind == "FACT":
                    f.evidence_kind = "MANAGEMENT_CLAIM"
    _ = lower  # reserved for future density heuristics
    return findings


def _filing_metas(ticker: str, root: Path | None) -> list[dict[str, Any]]:
    cdir = storage.company_dir(ticker, root)
    man = storage.load_source_manifest(ticker, root)
    out = []
    for s in man.get("sources", []):
        form = str(s.get("form") or "")
        if (
            s.get("kind") in {"sec_filing", "sec_filing_manual"}
            or form in {"10-K", "10-Q", "20-F", "DEF 14A", "DEFA14A", "8-K"}
        ):
            out.append(s)
    filings_dir = cdir / "Source" / "filings"
    if filings_dir.exists():
        for meta_path in filings_dir.glob("**/meta.json"):
            try:
                out.append(json.loads(meta_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    return out



_DIVIDEND_DISCRETION_TOKENS = (
    "sole discretion",
    "at the discretion",
    "board discretion",
    "no obligation",
    "depend upon",
    "depends upon",
    "subject to",
    "not obligated",
    "future declaration",
)


# --- Incentive / CD&A evidence-depth (generic; no ticker hardcodes) ---
# Weak/TOC-level proxy hits must NOT alone justify MG6 PASS (Plan §8 / §0.C CD&A MVP).

_TOC_LIKE_PATTERNS = [
    re.compile(
        r"(?:compensation discussion and analysis|executive compensation|"
        r"related[- ]party transactions?|director compensation|"
        r"security ownership|beneficial ownership)"
        r"\s+\d{1,3}\b",
        re.I,
    ),
    re.compile(r"\btable of contents\b", re.I),
    re.compile(
        r"\b(?:proposal\s+(?:one|two|three|four|five|six|seven|1|2|3|4|5|6|7)"
        r".{0,40}\d{1,3})\b",
        re.I,
    ),
]


def looks_like_toc_excerpt(excerpt: str | None) -> bool:
    """True when excerpt is TOC / page-index noise rather than body disclosure."""
    if not excerpt:
        return False
    text = excerpt.strip()
    if len(text) < 40:
        return True
    for pat in _TOC_LIKE_PATTERNS:
        if pat.search(text):
            return True
    # Dense page-number index: many bare integers + compensation/proposal headings
    nums = re.findall(r"\b\d{1,3}\b", text)
    low = text.lower()
    if len(nums) >= 4 and (
        "compensation" in low or "proposal" in low or "ownership" in low
    ):
        return True
    return False


def _incentive_blobs(semantic: Stage7SemanticReview | None) -> list[str]:
    if not semantic:
        return []
    blobs: list[str] = []
    for attr in (
        "incentive_metrics_notes",
        "ownership_guidelines_notes",
    ):
        val = getattr(semantic, attr, None)
        if val:
            blobs.append(val)
    for f in semantic.findings:
        if f.topic in {"incentive_metrics", "ownership_guidelines", "clawback"} and f.excerpt:
            blobs.append(f.excerpt)
    return blobs


# Patterns that evidence primary pay / vesting / LTI spine (required for MG6 PASS)
_METRICISH_CDA_PATTERNS = [
    re.compile(r"\bperformance\s+(?:share|stock)\s+units?\b|\bPSUs?\b", re.I),
    re.compile(r"\brestricted\s+stock\s+units?\b|\bRSUs?\b", re.I),
    re.compile(r"\bvest(?:ing|ed|s)?\b", re.I),
    re.compile(r"\b(?:three|3)[- ]year(?:\s+performance)?\s+period\b", re.I),
    re.compile(r"\blong[- ]term\s+incentive", re.I),
    re.compile(
        r"\b(?:ROIC|ROIIC|return on (?:invested )?capital)\b.{0,60}"
        r"\b(?:compensat|incentive|metric|measure|PSU|bonus)",
        re.I,
    ),
    re.compile(
        r"(?:total\s+shareholder\s+return|\bTSR\b).{0,60}"
        r"(?:compensat|incentive|metric|measure|PSU|modifier|ranking)",
        re.I,
    ),
    re.compile(
        r"\badjusted\s+(?:EBITDA|EPS|operating\s+income).{0,40}"
        r"\b(?:incentive|compensat|metric)",
        re.I,
    ),
    re.compile(
        r"\bannual\s+(?:incentive|bonus).{0,60}"
        r"\b(?:metric|measure|target|organic|revenue|growth)",
        re.I,
    ),
    re.compile(
        r"\b(?:primary|performance)\s+metrics?\b.{0,80}"
        r"\b(?:bonus|incentive|PSU|NEO|named executive)",
        re.I,
    ),
    re.compile(r"\belements of (?:our )?executive compensation\b", re.I),
    re.compile(
        r"\b(?:dilut(?:ion|ive)|share[- ]based compensation|SBC)\b.{0,80}"
        r"\b(?:compensat|equity|award|repurchase|offset)",
        re.I,
    ),
]

# Support disclosures alone (ownership guidelines / clawback) ≠ CD&A PASS
_SUPPORT_CDA_PATTERNS = [
    re.compile(
        r"\bclawback\s+polic|\bcompensation\s+recovery\s+polic|"
        r"\brecoup(?:ment)?\s+(?:polic|certain|erroneously)",
        re.I,
    ),
    re.compile(
        r"\bstock\s+ownership\s+guidelines?.{0,120}"
        r"(?:\d+\s*[x×]|multiple|salary|retain|significant ownership|hold)",
        re.I,
    ),
]


def incentive_evidence_depth(semantic: Stage7SemanticReview | None) -> dict[str, Any]:
    """Classify CD&A / incentive semantic depth for MG6.

    PASS requires non-TOC *metricish* CD&A spine (pay metrics / vesting / LTI / dilution
    linkage). Ownership-guidelines or clawback presence alone, or TOC/heading CD&A hits,
    are shallow → MIXED — never PASS merely because a proxy exists (Plan §8 / §0.C).

    Returns keys:
      depth: substantive | shallow | absent
      substantive_hits: list[str]
      support_hits: list[str]
      presence: bool
      toc_only: bool
    """
    blobs = _incentive_blobs(semantic)
    if not blobs:
        return {
            "depth": "absent",
            "substantive_hits": [],
            "support_hits": [],
            "presence": False,
            "toc_only": False,
        }
    metric_hits: list[str] = []
    support_hits: list[str] = []
    non_toc = 0
    for blob in blobs:
        if not looks_like_toc_excerpt(blob):
            non_toc += 1
        if looks_like_toc_excerpt(blob):
            continue  # TOC never counts as metric/support substance
        for pat in _METRICISH_CDA_PATTERNS:
            if pat.search(blob):
                metric_hits.append(pat.pattern[:60])
                break
        for pat in _SUPPORT_CDA_PATTERNS:
            if pat.search(blob):
                support_hits.append(pat.pattern[:60])
                break

    def _uniq(seq: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for h in seq:
            if h not in seen:
                seen.add(h)
                out.append(h)
        return out

    metric_hits = _uniq(metric_hits)
    support_hits = _uniq(support_hits)
    if metric_hits:
        depth = "substantive"
    else:
        depth = "shallow"  # presence (TOC and/or support-only) without CD&A metric spine
    return {
        "depth": depth,
        "substantive_hits": metric_hits,
        "support_hits": support_hits,
        "presence": True,
        "toc_only": non_toc == 0,
    }


def _prefer_incentive_notes(review: Stage7SemanticReview, limit: int = 400) -> str | None:
    """Prefer substantive CD&A body over TOC / page-index hits."""
    cands = [f for f in review.findings if f.topic == "incentive_metrics" and f.excerpt]
    if not cands:
        return None

    def score(ex: str) -> tuple[int, int, int]:
        low = ex.lower()
        subst = sum(1 for pat in (_METRICISH_CDA_PATTERNS + _SUPPORT_CDA_PATTERNS) if pat.search(ex))
        toc_pen = 1 if looks_like_toc_excerpt(ex) else 0
        body = 1 if ("psu" in low or "vest" in low or "tsr" in low or "incentive" in low) else 0
        return (subst, -toc_pen, body)

    best = max(cands, key=lambda f: score(f.excerpt or ""))
    return (best.excerpt or "")[:limit]


def _prefer_related_party_notes(review: Stage7SemanticReview, limit: int = 400) -> str | None:
    """Prefer related-party body disclosure over TOC page refs."""
    cands = [f for f in review.findings if f.topic == "related_party" and f.excerpt]
    if not cands:
        return None

    def score(ex: str) -> tuple[int, int]:
        toc_pen = 1 if looks_like_toc_excerpt(ex) else 0
        return (-toc_pen, len(ex))

    best = max(cands, key=lambda f: score(f.excerpt or ""))
    return (best.excerpt or "")[:limit]



_BUYBACK_PREFERRED_TOKENS = (
    "capital return program",
    "share repurchase program",
    "stock repurchase program",
    "authorized a share repurchase",
    "does not obligate us to repurchase",
    "repurchase authorization",
)


def _prefer_dividend_notes(review: Stage7SemanticReview, limit: int = 780) -> str | None:
    """Prefer Dividend Policy excerpts that include discretion / residual language."""
    cands = [f for f in review.findings if f.topic == "dividend_policy" and f.excerpt]
    if not cands:
        return None

    def score(ex: str) -> tuple[int, int, int]:
        low = ex.lower()
        disc = sum(1 for t in _DIVIDEND_DISCRETION_TOKENS if t in low)
        # Prefer section body over heading-only; penalize heading-only short blobs
        has_body = 1 if ("beginning in" in low or "declared" in low or "dividend" in low) else 0
        return (disc, has_body, len(ex))

    best = max(cands, key=lambda f: score(f.excerpt or ""))
    return (best.excerpt or "")[:limit]


def _prefer_buyback_notes(review: Stage7SemanticReview, limit: int = 400) -> str | None:
    """Prefer authorization/Capital Return Program language over risk-factor boilerplate."""
    cands = [f for f in review.findings if f.topic == "buyback_policy" and f.excerpt]
    if not cands:
        return None

    def score(ex: str) -> tuple[int, int, int]:
        low = ex.lower()
        pref = sum(1 for t in _BUYBACK_PREFERRED_TOKENS if t in low)
        # Risk-factor boilerplate often says "trading activity in our share repurchase"
        penalty = 1 if "trading activity" in low or "fluctuations in the market" in low else 0
        return (pref, -penalty, len(ex))

    best = max(cands, key=lambda f: score(f.excerpt or ""))
    return (best.excerpt or "")[:limit]


def _enrich_notes(review: Stage7SemanticReview) -> Stage7SemanticReview:
    topics = {f.topic for f in review.findings}

    def _first(topic: str, limit: int = 240) -> str | None:
        for f in review.findings:
            if f.topic == topic and f.excerpt:
                return f.excerpt[:limit]
        return None

    if not review.stated_hierarchy_notes:
        # Prefer concrete deployment/hierarchy excerpts over generic "strategy" mentions
        preferred_tokens = (
            "substantial majority",
            "disciplined capital deployment",
            "approach to capital allocation",
            "toward acquiring",
            "capital allocation priorit",
            "return of capital",
            "capital return program",
            "investments in infrastructure",
            "cash commitments for investing",
        )
        best = None
        for f in review.findings:
            if f.topic != "stated_hierarchy" or not f.excerpt:
                continue
            low = f.excerpt.lower()
            if any(tok in low for tok in preferred_tokens):
                best = f.excerpt[:400]
                break
            if best is None:
                best = f.excerpt[:400]
        review.stated_hierarchy_notes = best
    review.incentive_metrics_notes = review.incentive_metrics_notes or _prefer_incentive_notes(
        review
    ) or _first("incentive_metrics")
    review.ownership_guidelines_notes = review.ownership_guidelines_notes or _first(
        "ownership_guidelines"
    ) or _first("clawback")
    review.governance_structure_notes = review.governance_structure_notes or _first(
        "governance_structure"
    ) or _first("dual_class")
    review.related_party_notes = review.related_party_notes or _prefer_related_party_notes(
        review
    ) or _first("related_party")
    review.deal_criteria_notes = review.deal_criteria_notes or _first("deal_criteria")
    review.guidance_delivery_notes = review.guidance_delivery_notes or _first(
        "guidance_delivery"
    )
    review.succession_notes = review.succession_notes or _first("succession")
    review.buyback_policy_notes = review.buyback_policy_notes or _prefer_buyback_notes(
        review
    ) or _first("buyback_policy", limit=400)
    review.dividend_policy_notes = review.dividend_policy_notes or _prefer_dividend_notes(
        review
    )
    review.debt_motive_notes = review.debt_motive_notes or _first("debt_motive")
    review.checklist_coverage = sorted(topics)
    review.filled = bool(topics) or bool(
        review.stated_hierarchy_notes
        or review.incentive_metrics_notes
        or review.deal_criteria_notes
        or review.governance_structure_notes
    )
    return review


def persist_stage7_semantic(
    ticker: str,
    review: Stage7SemanticReview,
    *,
    root: Path | None = None,
) -> Path:
    cdir = storage.company_dir(ticker, root)
    notes = cdir / "Source" / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    path = notes / "stage7_semantic_review.json"
    storage.write_json(path, review.to_dict())
    return path


def run_stage7_semantic_from_filings(
    ticker: str,
    *,
    root: Path | None = None,
    persist: bool = True,
) -> Stage7SemanticReview:
    """Production-like Stage 7 semantic: scan 10-K/10-Q/DEF 14A/8-K for MG topics."""
    ticker = ticker.upper()
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)
    meta = storage.load_meta(ticker, root)
    cik = str(meta.get("cik") or "").zfill(10) if meta.get("cik") else None

    findings: list[Stage7SemanticFinding] = []
    allowed = {"10-K", "10-Q", "20-F", "DEF 14A", "DEFA14A", "8-K"}
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
                Stage7SemanticFinding(
                    topic="filing_retrieval",
                    citation=f"accession={accession}; primary={primary}",
                    classification="other",
                    evidence_kind="SYSTEM_INFERENCE",
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
    deduped: list[Stage7SemanticFinding] = []
    for f in findings:
        key = f"{f.topic}|{f.accession}|{(f.excerpt or '')[:60]}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)

    review = Stage7SemanticReview(
        findings=deduped,
        review_source="filings_heuristic",
        filled=False,
    )
    review = _enrich_notes(review)
    if persist:
        persist_stage7_semantic(ticker, review, root=root)
    return review
