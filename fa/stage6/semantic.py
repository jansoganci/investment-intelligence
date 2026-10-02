"""Stage 6 Notes/MD&A/IR semantic — capital / CapEx / acquisition / runway cues.

Every material finding tagged FACT | COMPANY_EXPLANATION | MODEL_INFERENCE.
No invented ROIC thresholds. Maint CapEx UNKNOWN if not disclosed.
Fixture-loadable like Stage 5.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .. import config, storage
from ..models import Stage6SemanticFinding, Stage6SemanticReview
from ..sec_client import get_filing_document

CHECKLIST_TOPICS = [
    "maint_growth_capex",
    "acquisition_context",
    "reinvestment_runway",
    "accounting_distortion",
    "fp_explanation",
    "lease_asc842",
    "investment_phase",
    "impairment",
    "capital_destination",
    "capex_productivity",
    "wc_mechanism",
    "ppa_acquisition",
]

_KEYWORD_MAP: list[tuple[str, list[str], str, str, bool, str | None]] = [
    (
        "maint_growth_capex",
        [
            r"\bmaintenance\s+(?:capex|capital\s+expenditures?)\b",
            r"\bgrowth\s+(?:capex|capital\s+expenditures?)\b",
            r"\bsustaining\s+(?:capex|capital)\b",
            r"\bmaintenance\s+versus\s+growth\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "maint_capex",
    ),
    (
        "acquisition_context",
        [
            r"\bacquisitions?\b.{0,60}\b(?:integration|synerg|earn[- ]?out)",
            r"\bbolt[- ]on\s+acquisitions?\b",
            r"\bbusiness\s+combinations?\b",
            r"\bgoodwill\b.{0,40}\bimpairment",
            # Wave 3 / B1: require purchase-accounting neighborhood; bare PPA excluded
            r"\bpurchase\s+price\s+allocation\b(?:\s*\(\s*PPA\s*\))?",
            r"\bPPA\b.{0,60}(?:purchase\s+(?:price\s+)?allocation|amortization|intangibles|acquisition|purchase\s+accounting)",
            r"(?:purchase\s+(?:price\s+)?allocation|purchase\s+accounting|amortization\s+of\s+(?:intangibles|acquired)).{0,60}\bPPA\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "acquisition",
    ),
    (
        "reinvestment_runway",
        [
            r"\breinvest(?:ment|ing)?\s+(?:opportunit|runway|capacity)",
            r"\bcapital\s+allocation\b",
            r"\bdeploy(?:ment|ing)?\s+capital\b",
            r"\breturn(?:s)?\s+of\s+capital\b|\bshare\s+repurchases?\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "runway",
    ),
    (
        "accounting_distortion",
        [
            r"\blease\s+accounting\b|\bASC\s*842\b|\bIFRS\s*16\b",
            r"\brestatement\b|\brevision\s+of\s+prior",
            r"\bchange\s+in\s+accounting\s+(?:principle|estimate)\b",
        ],
        "note",
        "FACT",
        True,
        "distortion",
    ),
    (
        "lease_asc842",
        [
            r"\bright[- ]of[- ]use\b|\bROU\s+assets?\b",
            r"\bASC\s*842\b",
            r"\boperating\s+lease\s+liabilit",
        ],
        "note",
        "FACT",
        False,
        "distortion",
    ),
    (
        "investment_phase",
        [
            r"\binvestment\s+phase\b",
            r"\belevated\s+(?:capex|investment|spending)\b",
            r"\bbuild(?:ing)?\s+capacity\b",
            r"\bramp[- ]up\b.{0,40}\b(?:facility|plant|fab|capacity)",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "fp",
    ),
    (
        "impairment",
        [
            r"\bgoodwill\s+impairment\b",
            r"\bimpairment\s+(?:of|charge|loss)\b",
            r"\bwrite[- ]downs?\b.{0,40}\b(?:goodwill|intangible)",
        ],
        "mdna",
        "FACT",
        True,
        "distortion",
    ),
    (
        "capital_destination",
        [
            r"\bdividends?\b.{0,40}\b(?:increased|returned|shareholders)",
            r"\bshare\s+repurchase\s+program\b",
            r"\bexcess\s+cash\b.{0,40}\b(?:return|distribute)",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "runway",
    ),
    (
        "capex_productivity",
        [
            r"\bcapex\b.{0,60}\b(?:productivity|returns?|payback|ROI)",
            r"\bproject\s+returns?\b",
            r"\bcapital\s+efficiency\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "growth_capex",
    ),
    (
        "wc_mechanism",
        [
            r"\bworking\s+capital\b",
            r"\bdeferred\s+revenue\b",
            r"\bcustomer\s+(?:float|prepayments?|deposits?)\b",
            r"\bsupply\s+chain\s+financ",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "other",
    ),
    (
        "ppa_acquisition",
        [
            r"\bamortization\s+of\s+(?:acquired\s+)?intangibles\b",
            r"\bpurchase\s+accounting\b",
            r"\bfair\s+value\s+adjustments?\b.{0,40}\bacquisition",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "acquisition",
    ),
]


def html_to_text(raw: str) -> str:
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"(?is)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t)
    return t


def _ppa_token_is_purchase_accounting(excerpt: str, full_text: str, match_start: int) -> bool:
    """Wave 3 / B1: bare PPA must have acquisition/accounting context; reject segment acronyms."""
    window = full_text[max(0, match_start - 100) : match_start + 120]
    if re.search(
        r"Precision\s+Agriculture\s*\(\s*PPA\s*\)"
        r"|Production\s*&\s*Precision\s+Agriculture\s*\(\s*PPA\s*\)"
        r"|operating\s+segments?\s*:.{0,160}\bPPA\b"
        r"|business\s+segments?\s*:.{0,160}\bPPA\b",
        window,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        return False
    ex = excerpt or window
    if re.search(
        r"purchase\s+(?:price\s+)?allocation"
        r"|purchase\s+accounting"
        r"|amortization\s+of\s+(?:intangibles|acquired)"
        r"|acquisition[\s-]related"
        r"|acquired\s+intangible",
        ex,
        flags=re.IGNORECASE,
    ):
        return True
    # Matched bare/near PPA without purchase-accounting neighborhood → reject
    return False


def _findings_from_text(
    text: str,
    *,
    source_label: str,
    accession: str | None = None,
) -> list[Stage6SemanticFinding]:
    findings: list[Stage6SemanticFinding] = []
    lower = text.lower()
    for topic, patterns, classification, kind, escalate, dim in _KEYWORD_MAP:
        for pat in patterns:
            m = re.search(pat, lower, flags=re.IGNORECASE)
            if not m:
                continue
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 120)
            excerpt = text[start:end].strip()
            matched_span = text[m.start() : m.end()]
            if topic == "acquisition_context" and re.search(r"\bPPA\b", matched_span, re.I):
                if not _ppa_token_is_purchase_accounting(excerpt, text, m.start()):
                    continue
            findings.append(
                Stage6SemanticFinding(
                    topic=topic,
                    citation=f"{source_label}~/{pat}/",
                    classification=classification,
                    evidence_kind=kind,
                    materiality_judgment="watchable",
                    materiality_reason=f"Keyword hit for {topic}",
                    escalate_to_human=escalate,
                    excerpt=excerpt[:400],
                    accession=accession,
                    dimension=dim,
                )
            )
            break
    return findings


def placeholder_stage6_semantic() -> Stage6SemanticReview:
    return Stage6SemanticReview(
        filled=False,
        review_source="placeholder",
        maint_capex_status="UNKNOWN",
    )


def load_stage6_semantic_from_fixture(path: Path) -> Stage6SemanticReview:
    """Load Stage 6 semantic from JSON fixture (mirror Stage 5)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    findings_raw = data.get("findings") or []
    findings = [
        Stage6SemanticFinding(**f) if isinstance(f, dict) else f for f in findings_raw
    ]
    return Stage6SemanticReview(
        findings=findings,
        maint_growth_capex_notes=data.get("maint_growth_capex_notes"),
        maint_capex_status=data.get("maint_capex_status") or "UNKNOWN",
        acquisition_context_notes=data.get("acquisition_context_notes"),
        runway_notes=data.get("runway_notes"),
        distortion_notes=data.get("distortion_notes"),
        fp_explanation_notes=data.get("fp_explanation_notes"),
        lease_accounting_notes=data.get("lease_accounting_notes"),
        investment_phase_notes=data.get("investment_phase_notes"),
        impairment_notes=data.get("impairment_notes"),
        capital_destination_notes=data.get("capital_destination_notes"),
        checklist_coverage=list(data.get("checklist_coverage") or []),
        review_source=data.get("review_source") or "fixture",
        filled=bool(data.get("filled", True)),
    )


def semantic_text_blob(semantic: Stage6SemanticReview | None) -> str:
    if not semantic:
        return ""
    parts = [
        semantic.maint_growth_capex_notes,
        semantic.acquisition_context_notes,
        semantic.runway_notes,
        semantic.distortion_notes,
        semantic.fp_explanation_notes,
        semantic.lease_accounting_notes,
        semantic.investment_phase_notes,
        semantic.impairment_notes,
        semantic.capital_destination_notes,
    ]
    for f in semantic.findings:
        parts.append(f.topic)
        parts.append(f.excerpt)
    return " ".join(p for p in parts if p)


def _filing_metas(ticker: str, root: Path | None) -> list[dict[str, Any]]:
    cdir = storage.company_dir(ticker, root)
    man = storage.load_source_manifest(ticker, root)
    out = []
    for s in man.get("sources", []):
        if s.get("kind") in {"sec_filing", "sec_filing_manual"} or str(
            s.get("form") or ""
        ) in {"10-K", "10-Q", "20-F"}:
            out.append(s)
    # Also scan Source/filings metadata if present
    filings_dir = cdir / "Source" / "filings"
    if filings_dir.exists():
        for meta_path in filings_dir.glob("**/meta.json"):
            try:
                out.append(json.loads(meta_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    return out


def _enrich_notes(review: Stage6SemanticReview) -> Stage6SemanticReview:
    topics = {f.topic for f in review.findings}
    if "maint_growth_capex" in topics and review.maint_capex_status == "UNKNOWN":
        review.maint_capex_status = "DISCLOSED_WITH_EVIDENCE"
        if not review.maint_growth_capex_notes:
            hits = [f for f in review.findings if f.topic == "maint_growth_capex"]
            review.maint_growth_capex_notes = (
                hits[0].excerpt if hits else "Maint/growth CapEx language present"
            )
    elif review.maint_capex_status == "UNKNOWN":
        review.maint_capex_status = "NOT_DISCLOSED"

    def _first(topic: str) -> str | None:
        for f in review.findings:
            if f.topic == topic and f.excerpt:
                return f.excerpt[:240]
        return None

    review.acquisition_context_notes = review.acquisition_context_notes or _first(
        "acquisition_context"
    ) or _first("ppa_acquisition")
    review.runway_notes = review.runway_notes or _first("reinvestment_runway") or _first(
        "capital_destination"
    )
    review.distortion_notes = review.distortion_notes or _first("accounting_distortion")
    review.lease_accounting_notes = review.lease_accounting_notes or _first("lease_asc842")
    review.investment_phase_notes = review.investment_phase_notes or _first(
        "investment_phase"
    )
    review.impairment_notes = review.impairment_notes or _first("impairment")
    review.capital_destination_notes = review.capital_destination_notes or _first(
        "capital_destination"
    )
    review.checklist_coverage = sorted(topics)
    review.filled = bool(topics) or bool(
        review.maint_growth_capex_notes
        or review.acquisition_context_notes
        or review.runway_notes
    )
    return review


def persist_stage6_semantic(
    ticker: str,
    review: Stage6SemanticReview,
    *,
    root: Path | None = None,
) -> Path:
    cdir = storage.company_dir(ticker, root)
    notes = cdir / "Source" / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    path = notes / "stage6_semantic_review.json"
    storage.write_json(path, review.to_dict())
    return path


def run_stage6_semantic_from_filings(
    ticker: str,
    *,
    root: Path | None = None,
    persist: bool = True,
) -> Stage6SemanticReview:
    """Production-like Stage 6 semantic: scan 10-K/10-Q for capital topics."""
    ticker = ticker.upper()
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)
    meta = storage.load_meta(ticker, root)
    cik = str(meta.get("cik") or "").zfill(10) if meta.get("cik") else None

    findings: list[Stage6SemanticFinding] = []
    for fmeta in _filing_metas(ticker, root):
        form = str(fmeta.get("form") or "")
        if form not in {"10-K", "10-Q", "20-F"}:
            continue
        accession = fmeta.get("accession")
        primary = fmeta.get("primary_document")
        if not accession or not primary:
            continue
        cik_use = str(fmeta.get("cik") or cik or "").zfill(10)
        path = get_filing_document(cik_use, accession, primary, offline=None)
        if path is None or not path.exists():
            findings.append(
                Stage6SemanticFinding(
                    topic="filing_retrieval",
                    citation=f"accession={accession}; primary={primary}",
                    classification="other",
                    evidence_kind="MODEL_INFERENCE",
                    materiality_judgment="unclear",
                    materiality_reason="Official filing primary unavailable — semantic incomplete",
                    escalate_to_human=True,
                    accession=accession,
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
            )
        )

    seen: set[str] = set()
    deduped: list[Stage6SemanticFinding] = []
    for f in findings:
        if f.topic in seen and f.topic != "filing_retrieval":
            continue
        if f.topic != "filing_retrieval":
            seen.add(f.topic)
        deduped.append(f)

    review = Stage6SemanticReview(
        findings=deduped,
        review_source="filings_heuristic",
        filled=False,
        maint_capex_status="UNKNOWN",
    )
    review = _enrich_notes(review)
    if persist:
        persist_stage6_semantic(ticker, review, root=root)
    return review
