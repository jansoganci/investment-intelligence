"""Stage 5 Notes/MD&A/IR semantic pipeline — filing-backed economics extraction.

Every material finding tagged FACT | COMPANY_EXPLANATION | MODEL_INFERENCE.
No invented GM/OP bands, scores, or ROIIC. Automate research first.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .. import config, storage
from ..models import Stage5SemanticFinding, Stage5SemanticReview
from ..sec_client import get_filing_document

CHECKLIST_TOPICS = [
    "pricing_power",
    "cost_advantage_scale",
    "margin_bridge",
    "input_commodity_labor",
    "sbc_nongaap",
    "ses_intentional_thin",
    "segment_margins",
    "unit_economics",
    "cycle_peak_margins",
    "investment_phase_om",
    "mix_theatre",
    "ppa_acquisition_optics",
    "promo_discounting",
    "capex_holiday_margin",
    "business_model",
]

# topic, patterns, classification, evidence_kind, escalate_if_hit, dimension
_KEYWORD_MAP: list[tuple[str, list[str], str, str, bool, str | None]] = [
    (
        "pricing_power",
        [
            r"\bpricing\s+power\b",
            r"\bprice\s+increases?\b.{0,40}\b(?:volume|demand|elastic)",
            r"\bpass(?:ed|ing|-through)\s+(?:through\s+)?(?:higher\s+)?(?:costs|inflation|input)",
            r"\bvalue(?:-|\s)based\s+pricing\b",
            r"\bbrand\s+(?:strength|equity|premium)\b",
            r"\bconcentrate\s+price\b",
            r"\bnet\s+price\s+(?:realization|increase)\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "price",
    ),
    (
        "cost_advantage_scale",
        [
            r"\boperating\s+leverage\b",
            r"\bscale\s+(?:econom(?:y|ies)|advantage|benefit)\b",
            r"\bcost\s+advantage\b",
            r"\bfixed[\s-]cost\s+(?:leverage|absorption)\b",
            r"\befficienc(?:y|ies)\s+(?:initiative|program|gain)",
            r"\bcost\s+(?:productivity|discipline)\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "scale",
    ),
    (
        "margin_bridge",
        [
            r"\bgross\s+margin\b.{0,60}\b(?:increased|decreased|expanded|compressed|improved|declined)",
            r"\boperating\s+margin\b.{0,60}\b(?:increased|decreased|expanded|compressed|improved|declined)",
            r"\bmargin\s+(?:expansion|compression|bridge|drivers?)\b",
            r"\bprice\/mix\b",
            r"\bvolume\s+leverage\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "mix",
    ),
    (
        "input_commodity_labor",
        [
            r"\bcommodity\s+(?:costs?|prices?|inflation)\b",
            r"\binput\s+costs?\b",
            r"\braw\s+material\b",
            r"\blabor\s+(?:costs?|inflation|shortage)\b",
            r"\bfreight\s+(?:costs?|rates?)\b",
            r"\bsweetener\b|\baluminum\b|\bresin\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "input",
    ),
    (
        "sbc_nongaap",
        [
            r"\bshare[\s-]based\s+compensation\b",
            r"\bstock[\s-]based\s+compensation\b",
            r"\bnon[\s-]GAAP\b.{0,40}\b(?:operating|margin|adjusted)",
            r"\badjusted\s+operating\s+(?:income|margin)\b",
            r"\bexcluding\s+stock[\s-]based\b",
        ],
        "note",
        "COMPANY_EXPLANATION",
        False,
        "accounting",
    ),
    (
        "ses_intentional_thin",
        [
            r"\bscale\s+economies\s+shared\b",
            r"\bpass(?:ed|ing)\s+(?:savings|efficienc).{0,40}\b(?:customer|consumer)",
            r"\bcustomer\s+surplus\b",
            r"\blow[\s-]price[\s-]high[\s-]volume\b",
            r"\beveryday\s+low\s+price\b",
            r"\bshared\s+(?:with|to)\s+(?:customers|consumers)\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "SES",
    ),
    (
        "segment_margins",
        [
            r"\bsegment\s+(?:operating\s+)?(?:income|margin|profit)\b",
            r"\boperating\s+income\s+by\s+segment\b",
            r"\breportable\s+segment\b",
        ],
        "segment",
        "FACT",
        False,
        "segment",
    ),
    (
        "unit_economics",
        [
            r"\bunit\s+economics\b",
            r"\bcontribution\s+margin\b",
            r"\btake[\s-]rate\b",
            r"\bcost\s+per\s+(?:unit|case|transaction|user)\b",
            r"\bgross\s+profit\s+per\s+unit\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "unit",
    ),
    (
        "cycle_peak_margins",
        [
            r"\bcyclical\s+(?:peak|high|trough)\b",
            r"\bpeak\s+(?:margins?|pricing|cycle)\b",
            r"\bthrough[\s-]the[\s-]cycle\b",
            r"\bcommodity\s+price\s+(?:spike|windfall|boom)\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "cycle",
    ),
    (
        "investment_phase_om",
        [
            r"\binvestment\s+phase\b",
            r"\breinvest(?:ing|ment)\s+in\s+(?:growth|brand|capacity)",
            r"\bincremental\s+(?:operating\s+)?margin\b",
            r"\boperating\s+leverage\b.{0,40}\b(?:negative|dilut|invest)",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "leverage",
    ),
    (
        "mix_theatre",
        [
            r"\bmix\s+(?:shift|benefit|tailwind|improvement)\b",
            r"\bhigher[\s-]margin\s+(?:products?|mix|portfolio)\b",
            r"\bportfolio\s+mix\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "mix",
    ),
    (
        "ppa_acquisition_optics",
        [
            r"\bpurchase\s+accounting\b",
            # Wave 3 / B1: bare PPA alone is NOT enough (DE Precision Agriculture false positive).
            # Require purchase-accounting / acquisition neighborhood around PPA.
            r"\bpurchase\s+price\s+allocation\b(?:\s*\(\s*PPA\s*\))?",
            r"\bPPA\b.{0,60}(?:purchase\s+(?:price\s+)?allocation|amortization|intangibles|acquisition|purchase\s+accounting)",
            r"(?:purchase\s+(?:price\s+)?allocation|amortization\s+of\s+(?:intangibles|acquired)|purchase\s+accounting).{0,60}\bPPA\b",
            r"\bamortization\s+of\s+(?:intangibles|acquired)",
            r"\bintegration\s+(?:costs?|charges?)\b",
            r"\bacquisition[\s-]related\s+(?:costs?|charges?|amort)",
        ],
        "note",
        "COMPANY_EXPLANATION",
        False,
        "accounting",
    ),
    (
        "promo_discounting",
        [
            r"\bpromotional\s+(?:activity|intensity|spend)\b",
            r"\bdiscount(?:ing|s)\b.{0,40}\b(?:increased|elevated|heavy)",
            r"\btrade\s+(?:spend|promotion)\b",
            r"\bprice\s+promotion\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "price",
    ),
    (
        "capex_holiday_margin",
        [
            r"\bdeferred\s+(?:maintenance|capex|investment)\b",
            r"\bunderinvest(?:ment|ing)\b",
            r"\bcapex\s+(?:holiday|pause|deferral)\b",
            r"\breduced\s+capital\s+expenditures?\b.{0,40}\bmargin",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        True,
        "accounting",
    ),
    (
        "business_model",
        [
            r"\bpayment\s+network\b",
            r"\bcard\s+network\b",
            r"\bpayments?\s+platform\b",
            r"\belectronic\s+payments?\b",
            r"\bpayment\s+services\b",
            r"\bmerchant\s+acquiring\b",
            r"\btake[\s-]?rate\b",
            r"\btransaction\s+volume\b",
            r"\bpayments?\s+volume\b",
            r"\bconsumer\s+payments\b",
            r"\bmoney\s+movement\b",
            r"\bsoftware\s+as\s+a\s+service\b|\bsaas\b",
            r"\bsubscription\s+software\b",
            r"\bacquisitive\s+compounder\b|\bbolt[\s-]on\s+acquisition",
        ],
        "business",
        "COMPANY_EXPLANATION",
        False,
        None,
    ),
]


def html_to_text(raw: str) -> str:
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t)
    return t


def _section_for_pos(text: str, pos: int) -> str:
    head = text[max(0, pos - 80) : pos + 80].lower()
    if "item 7" in head or "management" in head:
        return "MD&A"
    if "item 8" in head or "notes to" in head:
        return "Notes"
    if "item 1" in head:
        return "Business"
    return "filing"


def _ppa_token_is_purchase_accounting(excerpt: str, full_text: str, match_start: int) -> bool:
    """Wave 3 / B1: bare PPA must have acquisition/accounting context; reject segment acronyms."""
    window = full_text[max(0, match_start - 100) : match_start + 120]
    # Explicit segment / product acronym exclusions (no ticker hardcodes)
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
    return bool(
        re.search(
            r"purchase\s+(?:price\s+)?allocation"
            r"|purchase\s+accounting"
            r"|amortization\s+of\s+(?:intangibles|acquired)"
            r"|acquisition[\s-]related"
            r"|acquired\s+intangible",
            ex,
            flags=re.IGNORECASE,
        )
    )


def _findings_from_text(
    text: str,
    source_label: str,
    *,
    accession: str | None = None,
) -> list[Stage5SemanticFinding]:
    findings: list[Stage5SemanticFinding] = []
    seen: set[str] = set()
    low = text.lower()
    for topic, patterns, classification, kind, escalate, dim in _KEYWORD_MAP:
        for pat in patterns:
            m = re.search(pat, low, flags=re.IGNORECASE)
            if not m:
                continue
            key = f"{topic}:{m.start()}"
            if key in seen:
                continue
            seen.add(key)
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 120)
            excerpt = text[start:end].strip()
            # Wave 3 / B1: reject segment-acronym PPA false positives (only when match is PPA token)
            matched_span = text[m.start() : m.end()]
            if topic == "ppa_acquisition_optics" and re.search(r"\bPPA\b", matched_span, re.I):
                if not _ppa_token_is_purchase_accounting(excerpt, text, m.start()):
                    continue
            findings.append(
                Stage5SemanticFinding(
                    topic=topic,
                    citation=f"{source_label}@{m.start()}",
                    classification=classification,
                    evidence_kind=kind,
                    materiality_judgment="watchable" if not escalate else "material",
                    materiality_reason=(
                        "Heuristic keyword hit — human if material MODEL_INFERENCE"
                        if escalate
                        else "Automated MD&A/Notes economics cue"
                    ),
                    escalate_to_human=escalate,
                    excerpt=excerpt[:400],
                    accession=accession,
                    section=_section_for_pos(text, m.start()),
                    dimension=dim,
                )
            )
            break  # one hit per topic per document blob
    return findings


def load_stage5_semantic_from_fixture(path: Path) -> Stage5SemanticReview:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    findings = []
    for f in data.get("findings") or []:
        findings.append(Stage5SemanticFinding(**{k: v for k, v in f.items() if k in Stage5SemanticFinding.__dataclass_fields__}))
    return Stage5SemanticReview(
        findings=findings,
        pricing_power_notes=data.get("pricing_power_notes"),
        cost_advantage_notes=data.get("cost_advantage_notes"),
        margin_bridge_notes=data.get("margin_bridge_notes"),
        input_cost_notes=data.get("input_cost_notes"),
        sbc_nongaap_notes=data.get("sbc_nongaap_notes"),
        ses_notes=data.get("ses_notes"),
        segment_margin_notes=data.get("segment_margin_notes"),
        unit_econ_notes=data.get("unit_econ_notes"),
        cycle_peak_notes=data.get("cycle_peak_notes"),
        investment_phase_notes=data.get("investment_phase_notes"),
        checklist_coverage=list(data.get("checklist_coverage") or CHECKLIST_TOPICS),
        review_source=data.get("review_source") or "fixture",
        filled=True,
    )


def _note_from_findings(findings: list[Stage5SemanticFinding], topic: str) -> str | None:
    for f in findings:
        if f.topic == topic and f.excerpt:
            return f"{f.section or ''}: {f.excerpt[:240]}"
    return None


def heuristic_stage5_semantic(
    text: str,
    *,
    source_label: str = "heuristic_text",
    accession: str | None = None,
) -> Stage5SemanticReview:
    findings = _findings_from_text(text or "", source_label, accession=accession)
    return Stage5SemanticReview(
        findings=findings,
        checklist_coverage=list(CHECKLIST_TOPICS),
        review_source="heuristic",
        filled=bool(text),
        pricing_power_notes=_note_from_findings(findings, "pricing_power"),
        cost_advantage_notes=_note_from_findings(findings, "cost_advantage_scale"),
        margin_bridge_notes=_note_from_findings(findings, "margin_bridge"),
        input_cost_notes=_note_from_findings(findings, "input_commodity_labor"),
        sbc_nongaap_notes=_note_from_findings(findings, "sbc_nongaap"),
        ses_notes=_note_from_findings(findings, "ses_intentional_thin"),
        segment_margin_notes=_note_from_findings(findings, "segment_margins"),
        unit_econ_notes=_note_from_findings(findings, "unit_economics"),
        cycle_peak_notes=_note_from_findings(findings, "cycle_peak_margins"),
        investment_phase_notes=_note_from_findings(findings, "investment_phase_om"),
    )


def placeholder_stage5_semantic() -> Stage5SemanticReview:
    return Stage5SemanticReview(
        checklist_coverage=list(CHECKLIST_TOPICS),
        review_source="placeholder",
        filled=False,
    )


def _filing_metas(ticker: str, root: Path | None = None) -> list[dict[str, Any]]:
    cdir = storage.company_dir(ticker, root)
    filings_dir = cdir / "Source" / "filings"
    out: list[dict[str, Any]] = []
    if not filings_dir.exists():
        return out
    for path in sorted(filings_dir.glob("*.json")):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(meta, dict):
            meta["_meta_path"] = str(path)
            out.append(meta)
    return out


def persist_stage5_semantic(
    ticker: str,
    review: Stage5SemanticReview,
    *,
    root: Path | None = None,
) -> Path:
    cdir = storage.company_dir(ticker, root)
    notes = cdir / "Source" / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    path = notes / "stage5_semantic_review.json"
    storage.write_json(path, review.to_dict())
    return path


def run_stage5_semantic_from_filings(
    ticker: str,
    *,
    root: Path | None = None,
    persist: bool = True,
) -> Stage5SemanticReview:
    """Production-like Stage 5 semantic: scan 10-K/10-Q for economics topics."""
    ticker = ticker.upper()
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)
    meta = storage.load_meta(ticker, root)
    cik = str(meta.get("cik") or "").zfill(10) if meta.get("cik") else None

    findings: list[Stage5SemanticFinding] = []
    plain_blobs: list[str] = []

    for fmeta in _filing_metas(ticker, root):
        form = str(fmeta.get("form") or "")
        if form not in {"10-K", "10-Q", "20-F"}:
            continue
        accession = fmeta.get("accession")
        primary = fmeta.get("primary_document")
        if not accession or not primary:
            continue
        cik_use = str(fmeta.get("cik") or cik or "").zfill(10)
        # Refuse shared-cache cross-ticker: prefer company-scoped path via get_filing_document
        path = get_filing_document(cik_use, accession, primary, offline=None)
        if path is None or not path.exists():
            findings.append(
                Stage5SemanticFinding(
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
        plain_blobs.append(text)
        findings.extend(
            _findings_from_text(
                text,
                source_label=f"{form}:{accession}",
                accession=accession,
            )
        )

    # Deduplicate by topic keeping first
    seen_topics: set[str] = set()
    deduped: list[Stage5SemanticFinding] = []
    for f in findings:
        if f.topic in seen_topics and f.topic != "filing_retrieval":
            continue
        if f.topic != "filing_retrieval":
            seen_topics.add(f.topic)
        deduped.append(f)

    review = Stage5SemanticReview(
        findings=deduped,
        checklist_coverage=list(CHECKLIST_TOPICS),
        review_source="heuristic_filings" if plain_blobs else "placeholder",
        filled=bool(plain_blobs) or bool(deduped),
        pricing_power_notes=_note_from_findings(deduped, "pricing_power"),
        cost_advantage_notes=_note_from_findings(deduped, "cost_advantage_scale"),
        margin_bridge_notes=_note_from_findings(deduped, "margin_bridge"),
        input_cost_notes=_note_from_findings(deduped, "input_commodity_labor"),
        sbc_nongaap_notes=_note_from_findings(deduped, "sbc_nongaap"),
        ses_notes=_note_from_findings(deduped, "ses_intentional_thin"),
        segment_margin_notes=_note_from_findings(deduped, "segment_margins"),
        unit_econ_notes=(
            _note_from_findings(deduped, "unit_economics")
            or _note_from_findings(deduped, "business_model")
        ),
        cycle_peak_notes=_note_from_findings(deduped, "cycle_peak_margins"),
        investment_phase_notes=_note_from_findings(deduped, "investment_phase_om"),
    )
    if persist and review.filled:
        persist_stage5_semantic(ticker, review, root=root)
    return review


def semantic_text_blob(semantic: Stage5SemanticReview | None) -> str:
    if semantic is None:
        return ""
    parts = [
        semantic.pricing_power_notes or "",
        semantic.cost_advantage_notes or "",
        semantic.margin_bridge_notes or "",
        semantic.input_cost_notes or "",
        semantic.sbc_nongaap_notes or "",
        semantic.ses_notes or "",
        semantic.segment_margin_notes or "",
        semantic.unit_econ_notes or "",
        semantic.cycle_peak_notes or "",
        semantic.investment_phase_notes or "",
    ]
    for f in semantic.findings:
        parts.append(f.excerpt or "")
        parts.append(f.topic)
    return " ".join(p for p in parts if p)
