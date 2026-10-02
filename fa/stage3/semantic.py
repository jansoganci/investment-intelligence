"""Stage 3 Notes/MD&A semantic pipeline — filing-backed; no invented maintenance CapEx."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .. import config, storage
from ..models import Stage3SemanticFinding, Stage3SemanticReview
from ..sec_client import get_filing_document

# Systematic checklist topics (SPEC §0 / §8 / §9)
CHECKLIST_TOPICS = [
    "maintenance_vs_growth_capex",
    "ocf_vs_ni_explanation",
    "factoring",
    "supplier_finance",
    "wc_distortions",
    "wc_material_movements",
    "contingent_consideration",
    "acquisitions",
    "asset_sales",
    "restructuring",
    "capitalized_costs",
    "unusual_cash",
    "sbc_optics",
    "equity_method_cash",
]

# topic, patterns, section_hint, evidence_kind, escalate_if_hit
_KEYWORD_MAP: list[tuple[str, list[str], str, str, bool]] = [
    (
        "factoring",
        [r"\bfactoring\b", r"\bsold receivables\b", r"\breceivables.?sold\b", r"\btrade accounts receivable factoring\b"],
        "note",
        "COMPANY_EXPLANATION",
        True,
    ),
    (
        "supplier_finance",
        [
            r"\bsupplier finance\b",
            r"\breverse factoring\b",
            r"\bsupply chain finance\b",
            r"\bSCF\b.?program",
        ],
        "note",
        "COMPANY_EXPLANATION",
        True,
    ),
    (
        "maintenance_vs_growth_capex",
        [r"\bmaintenance capital\b", r"\bmaintenance capex\b", r"\bgrowth capital expenditure"],
        "mdna",
        "COMPANY_EXPLANATION",
        True,
    ),
    (
        "ocf_vs_ni_explanation",
        [
            r"\bnet cash provided by operating activities\b",
            r"\bcash flows from operating activities\b",
            r"\breconcili(?:e|ation).{0,40}net income\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
    ),
    (
        "equity_method_cash",
        [
            r"\bequity method invest",
            r"\bequity income\b",
            r"\bshare of.+earnings\b",
            r"\bdividends.{0,40}equity method\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
    ),
    (
        "acquisitions",
        [r"\bacquisition[s]?\b", r"\bbusiness combination\b", r"\bpurchase of .*business"],
        "cf_footnote",
        "COMPANY_EXPLANATION",
        False,
    ),
    (
        "asset_sales",
        [r"\bproceeds from sale\b", r"\basset sale[s]?\b", r"\bdivestiture\b", r"\brefranchising\b"],
        "cf_footnote",
        "COMPANY_EXPLANATION",
        False,
    ),
    (
        "restructuring",
        [r"\brestructuring\b", r"\bseverance\b", r"\bexit cost"],
        "note",
        "COMPANY_EXPLANATION",
        False,
    ),
    (
        "capitalized_costs",
        [r"\bcapitalized software\b", r"\bcapitalized commission\b", r"\binternally developed software"],
        "note",
        "COMPANY_EXPLANATION",
        False,
    ),
    (
        "unusual_cash",
        [r"\bone.?time\b", r"\bnon.?recurring\b", r"\bunusual.{0,20}cash", r"\btax litigation deposit\b"],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
    ),
    (
        "wc_distortions",
        [r"\bchannel stuff", r"\btrade loading\b", r"\bworking capital.{0,40}benefit"],
        "mdna",
        "COMPANY_EXPLANATION",
        True,
    ),
    (
        "sbc_optics",
        [r"\bshare.?based compensation\b", r"\bstock.?based compensation\b", r"\bstock-based compensation expense\b"],
        "note",
        "FACT",
        False,
    ),
    (
        "contingent_consideration",
        [
            r"\bcontingent consideration\b",
            r"\bmilestone payment\b",
            r"\bearnout\b",
            r"\bcontingent.{0,40}liability.{0,40}paid\b",
            r"\bfinal milestone\b",
        ],
        "note",
        "COMPANY_EXPLANATION",
        True,
    ),
    (
        "wc_material_movements",
        [
            r"\bdecrease in accounts payable\b",
            r"\bworking capital.{0,60}(decrease|increase|use|source)",
            r"\baccounts payable and accrued.{0,80}(decrease|increase)",
            r"\bnet change in operating assets and liabilities\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
    ),
]


def html_to_text(raw: str) -> str:
    """Strip HTML/XBRL chrome to searchable plain text."""
    if not raw:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _section_for_pos(plain: str, pos: int) -> str:
    """Best-effort Item 7 / Item 8 / notes label near hit."""
    window = plain[max(0, pos - 8000) : pos + 200]
    if re.search(r"ITEM\s+7", window, re.I) and not re.search(r"ITEM\s+8", window[-2000:], re.I):
        return "Item 7 MD&A"
    if re.search(r"Notes? to Consolidated Financial Statements|ITEM\s+8", window, re.I):
        return "Notes / Item 8"
    if re.search(r"Cash Flows from Operating Activities", window, re.I):
        return "MD&A — Cash Flows from Operating Activities"
    return "filing_text"


def _findings_from_text(
    text: str,
    source_label: str,
    *,
    accession: str | None = None,
) -> list[Stage3SemanticFinding]:
    findings: list[Stage3SemanticFinding] = []
    if not text:
        return findings
    lower = text.lower()
    for topic, patterns, classification, evidence_kind, escalate_default in _KEYWORD_MAP:
        for pat in patterns:
            m = re.search(pat, lower, flags=re.IGNORECASE)
            if not m:
                continue
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 220)
            excerpt = text[start:end].strip()
            section = _section_for_pos(text, m.start())
            # Escalate only when topic is a known distortion class OR disclosure is ambiguous
            materiality = "watchable" if escalate_default else "not_assessed"
            reason = (
                f"Filing text hit for '{topic}' in {source_label} ({section}); "
                "human judges materiality (no numeric bar). Escalate only if distortion class "
                "or ambiguity remains after reading excerpt."
            )
            escalate = escalate_default
            # If company quantifies factoring/SCF volumes in excerpt → material disclosure present
            if topic in {"factoring", "supplier_finance"} and re.search(
                r"\$\s*[0-9]|billion|million", excerpt, re.I
            ):
                materiality = "material"
                reason = (
                    f"Company discloses {topic} program with quantified activity in filing; "
                    "escalate for cash-quality review (disclosure presence — not a numeric threshold rule)"
                )
                escalate = True
            if topic == "contingent_consideration" and re.search(
                r"\$\s*[0-9]|billion|million|paid", excerpt, re.I
            ):
                materiality = "material"
                reason = (
                    "Company discloses contingent consideration / milestone payment affecting "
                    "operating liabilities / WC cash; escalate for one-time vs recurring cash judgment "
                    "(disclosure presence — not a numeric threshold rule)"
                )
                escalate = True
            findings.append(
                Stage3SemanticFinding(
                    topic=topic,
                    citation=f"{source_label}:{section}:{m.group(0)!r}",
                    classification=classification,
                    evidence_kind=evidence_kind,
                    materiality_judgment=materiality,
                    materiality_reason=reason,
                    escalate_to_human=escalate,
                    excerpt=excerpt[:500],
                    accession=accession,
                    section=section,
                )
            )
            break  # one hit per topic from this text
    return findings


def _maintenance_from_payload(data: dict[str, Any]) -> tuple[str, str | None, float | None]:
    """UNKNOWN unless defensible disclosed evidence — never invent amount."""
    status = data.get("maintenance_capex_status") or "UNKNOWN"
    evidence = data.get("maintenance_capex_evidence")
    amount = data.get("maintenance_capex_amount")
    if status == "DISCLOSED_WITH_EVIDENCE":
        if not evidence:
            return "UNKNOWN", None, None
        try:
            amt = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            amt = None
        return "DISCLOSED_WITH_EVIDENCE", str(evidence), amt
    return "UNKNOWN", None, None


def load_stage3_semantic_from_fixture(
    notes_path: Path | None = None,
    notes_payload: dict | None = None,
) -> Stage3SemanticReview:
    """Fill Stage3SemanticReview from fixture JSON (no paid LLM)."""
    data: dict[str, Any] = {}
    if notes_payload:
        data = dict(notes_payload)
    elif notes_path and notes_path.exists():
        raw_text = notes_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return heuristic_stage3_semantic(raw_text, source_label=str(notes_path.name))

    # Placeholder / unfilled stubs → treat as not filled
    if data.get("filled") is False and data.get("review_source", "").startswith("uat_placeholder"):
        return placeholder_stage3_semantic()

    status, evidence, amount = _maintenance_from_payload(data)

    findings: list[Stage3SemanticFinding] = []
    for item in data.get("findings") or []:
        if not isinstance(item, dict):
            continue
        findings.append(
            Stage3SemanticFinding(
                topic=str(item.get("topic") or "other"),
                citation=item.get("citation"),
                classification=str(item.get("classification") or "note"),
                evidence_kind=str(item.get("evidence_kind") or "COMPANY_EXPLANATION"),
                materiality_judgment=str(item.get("materiality_judgment") or "not_assessed"),
                materiality_reason=str(item.get("materiality_reason") or ""),
                escalate_to_human=bool(item.get("escalate_to_human", False)),
                excerpt=item.get("excerpt"),
                accession=item.get("accession"),
                section=item.get("section"),
            )
        )

    for key in (
        "notes_text",
        "mdna_text",
        "cash_footnotes_text",
        "covenants_notes",
    ):
        blob = data.get(key)
        if isinstance(blob, str) and blob.strip():
            findings.extend(_findings_from_text(blob, key))

    return Stage3SemanticReview(
        findings=findings,
        maintenance_capex_status=status,  # type: ignore[arg-type]
        maintenance_capex_evidence=evidence,
        maintenance_capex_amount=amount,
        factoring_or_supplier_finance_notes=data.get("factoring_or_supplier_finance_notes"),
        acquisitions_notes=data.get("acquisitions_notes"),
        asset_sales_notes=data.get("asset_sales_notes"),
        restructuring_notes=data.get("restructuring_notes"),
        capitalized_costs_notes=data.get("capitalized_costs_notes"),
        unusual_cash_notes=data.get("unusual_cash_notes"),
        wc_distortion_notes=data.get("wc_distortion_notes"),
        checklist_coverage=list(data.get("checklist_coverage") or CHECKLIST_TOPICS),
        review_source=data.get("review_source") or "fixture",
        filled=True,
    )


def heuristic_stage3_semantic(
    text: str,
    *,
    source_label: str = "heuristic_text",
    accession: str | None = None,
) -> Stage3SemanticReview:
    """Keyword/heuristic Notes pass. Maintenance stays UNKNOWN unless structured evidence."""
    findings = _findings_from_text(text or "", source_label, accession=accession)
    status = "UNKNOWN"
    evidence = None
    amount = None
    if text and re.search(r"\bmaintenance capex\b.{0,40}\b(disclosed|was|of)\b", text, re.I):
        m_amt = re.search(
            r"maintenance capex[^\n$.]{0,40}\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(million|billion|m|bn)?",
            text,
            re.I,
        )
        if m_amt:
            status = "UNKNOWN"
            evidence = None
            amount = None
            findings.append(
                Stage3SemanticFinding(
                    topic="maintenance_vs_growth_capex",
                    citation=f"{source_label}:maintenance-capex-phrase",
                    classification="mdna",
                    evidence_kind="MODEL_INFERENCE",
                    materiality_judgment="unclear",
                    materiality_reason=(
                        "Heuristic saw maintenance CapEx language but will not invent/accept "
                        "amount without structured DISCLOSED_WITH_EVIDENCE evidence — escalate"
                    ),
                    escalate_to_human=True,
                    excerpt=m_amt.group(0)[:300],
                    accession=accession,
                    section="MD&A",
                )
            )

    return Stage3SemanticReview(
        findings=findings,
        maintenance_capex_status=status,  # type: ignore[arg-type]
        maintenance_capex_evidence=evidence,
        maintenance_capex_amount=amount,
        checklist_coverage=list(CHECKLIST_TOPICS),
        review_source="heuristic",
        filled=bool(text),
    )


def placeholder_stage3_semantic() -> Stage3SemanticReview:
    """Empty placeholder — LLM not required in dry-run; maintenance UNKNOWN."""
    return Stage3SemanticReview(
        maintenance_capex_status="UNKNOWN",
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


def run_stage3_semantic_from_filings(
    ticker: str,
    *,
    root: Path | None = None,
    persist: bool = True,
) -> Stage3SemanticReview:
    """
    Production-like Stage 3 semantic path:
    load official 10-K primary documents (cache or fetch), scan MD&A/notes for cash topics,
    persist stage3_semantic_review.json. No arithmetic; maintenance CapEx UNKNOWN unless
    structured disclosed evidence.
    """
    ticker = ticker.upper()
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)
    meta = storage.load_meta(ticker, root)
    cik = str(meta.get("cik") or "").zfill(10) if meta.get("cik") else None

    findings: list[Stage3SemanticFinding] = []
    sources_used: list[str] = []
    plain_blobs: list[tuple[str, str, str | None]] = []  # label, text, accession

    for fmeta in _filing_metas(ticker, root):
        form = str(fmeta.get("form") or "")
        if form not in {"10-K", "10-Q", "20-F"}:
            continue
        accession = fmeta.get("accession")
        primary = fmeta.get("primary_document")
        if not accession or not primary:
            # Try cache by common KO-style name from description — skip if no primary
            # Look for any cached html matching accession fragment
            cache_dir = config.SEC_CACHE_DIR / "filings"
            if cache_dir.exists() and accession:
                hits = list(cache_dir.glob(f"*{accession}*")) + list(cache_dir.glob("*.htm"))
                # Prefer latest 10-K html if primary missing
                if hits and form == "10-K":
                    # only use if single obvious file already known
                    pass
            continue
        cik_use = str(fmeta.get("cik") or cik or "").zfill(10)
        path = get_filing_document(cik_use, accession, primary, offline=None)
        if path is None:
            # Offline fallback: any cache file matching primary basename
            cand = config.SEC_CACHE_DIR / "filings" / Path(primary).name
            path = cand if cand.exists() else None
        if path is None or not path.exists():
            findings.append(
                Stage3SemanticFinding(
                    topic="filing_retrieval",
                    citation=f"accession={accession}; primary={primary}",
                    classification="other",
                    evidence_kind="MODEL_INFERENCE",
                    materiality_judgment="unclear",
                    materiality_reason=(
                        "Official filing primary document unavailable in cache/network — "
                        "semantic incomplete for this accession"
                    ),
                    escalate_to_human=True,
                    accession=accession,
                    section=None,
                )
            )
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        plain = html_to_text(raw)
        label = f"{form}:{accession}:{path.name}"
        sources_used.append(label)
        plain_blobs.append((label, plain, accession))
        findings.extend(_findings_from_text(plain, label, accession=accession))

    # If no primary_document on older filings, still scan any cached html under filings/
    if not plain_blobs:
        cache_dir = config.SEC_CACHE_DIR / "filings"
        if cache_dir.exists():
            for path in sorted(cache_dir.glob("*.htm")) + sorted(cache_dir.glob("*.html")):
                raw = path.read_text(encoding="utf-8", errors="ignore")
                plain = html_to_text(raw)
                label = f"cache:{path.name}"
                sources_used.append(label)
                plain_blobs.append((label, plain, None))
                findings.extend(_findings_from_text(plain, label))

    # Deduplicate by topic (keep first / most specific)
    seen: set[str] = set()
    deduped: list[Stage3SemanticFinding] = []
    for f in findings:
        key = f.topic
        if key in seen and key != "filing_retrieval":
            continue
        seen.add(key)
        deduped.append(f)

    # Topic summary notes for evaluator
    def _note_for(topic: str) -> str | None:
        for f in deduped:
            if f.topic == topic and f.excerpt:
                return f"{f.section or ''}: {f.excerpt[:240]}"
        return None

    factoring_note = None
    fac = _note_for("factoring")
    scf = _note_for("supplier_finance")
    if fac or scf:
        factoring_note = " | ".join(x for x in (fac, scf) if x)

    review = Stage3SemanticReview(
        findings=deduped,
        maintenance_capex_status="UNKNOWN",
        maintenance_capex_evidence=None,
        maintenance_capex_amount=None,
        factoring_or_supplier_finance_notes=factoring_note,
        acquisitions_notes=_note_for("acquisitions"),
        asset_sales_notes=_note_for("asset_sales"),
        restructuring_notes=_note_for("restructuring"),
        capitalized_costs_notes=_note_for("capitalized_costs"),
        unusual_cash_notes=_note_for("unusual_cash"),
        wc_distortion_notes=_note_for("wc_distortions"),
        checklist_coverage=list(CHECKLIST_TOPICS),
        review_source="filing_heuristic",
        filled=bool(plain_blobs),
    )

    if persist:
        persist_stage3_semantic(ticker, review, root=root, sources_used=sources_used)
    return review


def persist_stage3_semantic(
    ticker: str,
    review: Stage3SemanticReview,
    *,
    root: Path | None = None,
    sources_used: list[str] | None = None,
) -> Path:
    """Write Source/notes/stage3_semantic_review.json (real pack, not stub)."""
    cdir = storage.company_dir(ticker, root)
    notes_dir = cdir / "Source" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = notes_dir / "stage3_semantic_review.json"
    payload = review.to_dict()
    payload["sources_used"] = sources_used or []
    payload["note"] = (
        "Stage 3 cash Notes/MD&A pass from official filing text (heuristic). "
        "Maintenance CapEx UNKNOWN unless DISCLOSED_WITH_EVIDENCE. No invented amounts. "
        "No arithmetic in semantic layer."
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def attach_bridge_semantic_explanations(
    bridge: dict[str, Any],
    semantic: Stage3SemanticReview | None,
) -> dict[str, Any]:
    """Attach filing explanations that match the OCF–NI gap (no arithmetic)."""
    out = dict(bridge or {})
    attached: list[dict[str, Any]] = []
    if semantic and semantic.findings:
        for f in semantic.findings:
            if f.topic in {
                "ocf_vs_ni_explanation",
                "equity_method_cash",
                "wc_distortions",
                "unusual_cash",
                "factoring",
                "supplier_finance",
            }:
                attached.append(
                    {
                        "topic": f.topic,
                        "evidence_kind": f.evidence_kind,
                        "citation": f.citation,
                        "section": f.section,
                        "accession": f.accession,
                        "excerpt": f.excerpt,
                    }
                )
    out["semantic_explanations"] = attached
    return out
