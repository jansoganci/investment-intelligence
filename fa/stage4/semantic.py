"""Stage 4 Notes/MD&A/IR semantic pipeline — filing-backed growth extraction.

Every material finding tagged FACT | COMPANY_EXPLANATION | MODEL_INFERENCE.
No invented organic %, TAM, or scores. Mirrors Stage 3 automation depth.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .. import config, storage
from ..models import Stage4SemanticFinding, Stage4SemanticReview
from ..sec_client import get_filing_document

CHECKLIST_TOPICS = [
    "organic_vs_acquired",
    "fx_constant_currency",
    "volume_price_mix",
    "geography_product",
    "capacity_backlog",
    "customer_unit",
    "ma_inorganic",
    "category_share",
    "backlog_rpo",
    "recurring_revenue",
    "cycle_base_effect",
    "runway_claim",
    "dilution_sbc",
    "fp_channel_stuffing",
    "fp_inflation_price",
    "same_store_comps",
    "segment_disclosure",
    # Wave 4 C1 harvest: perimeter / comparability-break cues (spin, disc. ops, etc.)
    "comparability_perimeter",
]

# topic, patterns, classification, evidence_kind, escalate_if_hit, dimension
_KEYWORD_MAP: list[tuple[str, list[str], str, str, bool, str | None]] = [
    (
        "organic_vs_acquired",
        [
            r"\borganic\s+(?:revenue\s+)?growth\b",
            r"\bcomparable\s+(?:currency\s+)?(?:neutral\s+)?(?:sales|revenue)\b",
            r"\bexcluding\s+(?:the\s+)?(?:impact\s+of\s+)?acquisitions?\b",
            r"\binorganic\s+growth\b",
            r"\bacquisition(?:s)?\s+contributed\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "organic",
    ),
    (
        "fx_constant_currency",
        [
            r"\bconstant\s+currency\b",
            r"\bcurrency\s+neutral\b",
            r"\bforeign\s+currency\s+(?:translation|headwind|tailwind|impact)\b",
            r"\bFX\s+(?:impact|headwind|tailwind)\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "FX",
    ),
    (
        "volume_price_mix",
        [
            r"\bvolume\s+(?:increased|decreased|growth|decline)\b",
            r"\bprice(?:\/mix|/mix|\s+mix|\s+and\s+mix)?\b.{0,40}\b(?:contribut|benefit|impact)",
            r"\bconcentrate\s+sales\b",
            r"\bunit\s+case\s+volume\b",
            r"\bASP\b.{0,30}\b(?:increas|decreas)",
            r"\bprice\/mix\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "volume",
    ),
    (
        "geography_product",
        [
            r"\bemerging\s+markets?\b",
            r"\bgeographic\s+(?:expansion|segment|revenue)\b",
            r"\bnet operating revenues by.+segment\b",
            r"\bproduct\s+category\b",
            r"\bEurasia\b|\bLatin America\b|\bAsia Pacific\b",
        ],
        "segment",
        "COMPANY_EXPLANATION",
        False,
        "geo",
    ),
    (
        "capacity_backlog",
        [
            r"\bmanufacturing\s+capacity\b",
            r"\bcapacity\s+(?:expansion|constraint|utilization)\b",
            r"\bbook-to-bill\b",
            r"\border\s+backlog\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "capacity",
    ),
    (
        "customer_unit",
        [
            r"\bunit\s+case\b",
            r"\bactive\s+users?\b",
            r"\bmonthly\s+active\b",
            r"\btransaction\s+volume\b",
            r"\bgross\s+merchandise\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "volume",
    ),
    (
        "ma_inorganic",
        [
            r"\bbusiness\s+combination\b",
            r"\bacquisitions?\s+of\s+businesses\b",
            r"\bpurchase\s+of\s+.+business",
            r"\bbolt-?on\b",
            r"\binorganic\b",
        ],
        "note",
        "COMPANY_EXPLANATION",
        False,
        "acquisition",
    ),
    (
        "category_share",
        [
            r"\bmarket\s+share\b",
            r"\bcategory\s+growth\b",
            r"\bindustry\s+growth\b",
            r"\bshare\s+gains?\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "share",
    ),
    (
        "backlog_rpo",
        [
            r"\bremaining\s+performance\s+obligation",
            r"\bRPO\b",
            r"\bdeferred\s+revenue\b",
            r"\bbookings\b",
            r"\bbacklog\b",
        ],
        "note",
        "FACT",
        False,
        "other",
    ),
    (
        "recurring_revenue",
        [
            r"\bannual\s+recurring\s+revenue\b",
            r"\bARR\b",
            r"\bnet\s+(?:revenue\s+)?retention\b",
            r"\bsubscription\s+revenue\b",
            r"\brevenue\s+run[- ]rate\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "other",
    ),
    (
        "cycle_base_effect",
        [
            r"\bcompar(?:ison|able)\s+(?:to|against)\s+(?:a\s+)?(?:weak|strong|easy|difficult)\s+prior",
            r"\bbase\s+effect\b",
            r"\bcyclical\s+(?:recovery|rebound|peak|trough)\b",
            r"\brebound\s+(?:in|from)\b",
            r"\bpost-?pandemic\s+recovery\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        True,
        "other",
    ),
    (
        "runway_claim",
        [
            r"\blong-?term\s+growth\s+(?:algorithm|outlook|opportunity)\b",
            r"\bwhite\s+space\b",
            r"\btotal\s+addressable\s+market\b",
            r"\bunder-?penetrated\b",
            r"\brunway\s+for\s+growth\b",
            r"\bmulti-?year\s+growth\s+opportunit",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        None,
    ),
    (
        "dilution_sbc",
        [
            r"\bshare[- ]based\s+compensation\b",
            r"\bstock[- ]based\s+compensation\b",
            r"\bdiluted\s+weighted[- ]average\s+shares\b",
            r"\bshare\s+repurchase",
            r"\btreasury\s+stock\b",
        ],
        "note",
        "FACT",
        False,
        None,
    ),
    (
        "fp_channel_stuffing",
        [
            r"\bchannel\s+stuff",
            r"\btrade\s+loading\b",
            r"\bpull[- ]forward\s+(?:of\s+)?(?:demand|sales|orders)",
            r"\binventory\s+build\s+at\s+(?:retail|distributor)",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        True,
        "accounting",
    ),
    (
        "fp_inflation_price",
        [
            r"\bpricing\s+actions?\b",
            r"\bprice\s+increases?\b.{0,40}\binflation",
            r"\binflationary\s+(?:pricing|environment)\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "price",
    ),
    (
        "same_store_comps",
        [
            r"\bsame[- ]store\s+sales\b",
            r"\bcomparable\s+store\s+sales\b",
            r"\bcomp\s+sales\b",
        ],
        "mdna",
        "COMPANY_EXPLANATION",
        False,
        "volume",
    ),
    (
        "segment_disclosure",
        [
            r"\breportable\s+segments?\b",
            r"\bsegment\s+(?:net\s+)?(?:operating\s+)?revenues?\b",
            r"\bresults\s+of\s+operations\s+by\s+segment\b",
        ],
        "segment",
        "FACT",
        False,
        "geo",
    ),
    # General perimeter / spin / disc-ops harvest for SD-W4-C1 (no ticker hardcodes).
    # Surfaces cue text into semantic_text_blob so detect_comparability_breaks can fire.
    (
        "comparability_perimeter",
        [
            r"\bdiscontinued\s+operations?\b",
            r"\bcontinuing\s+operations?\b",
            r"\bspin[- ]?offs?\b",
            r"\bspin[- ]?separation\b",
            r"\bcompleted\s+the\s+separation\b",
            r"\bseparation\s+of\s+(?:its\s+|our\s+)?(?:former\s+)?\w+",
            r"\bbusiness\s+as\s+a\s+discontinued\s+operation\b",
            r"\bdivestiture\s+of\s+the\s+\w+\s+business\b",
            r"\bportfolio\s+change\b",
            r"\bsplit[- ]?offs?\b",
        ],
        "note",
        "FACT",
        True,
        "other",
    ),
]


def html_to_text(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _section_for_pos(plain: str, pos: int) -> str:
    window = plain[max(0, pos - 8000) : pos + 200]
    if re.search(r"ITEM\s+7", window, re.I) and not re.search(r"ITEM\s+8", window[-2000:], re.I):
        return "Item 7 MD&A"
    if re.search(r"Notes? to Consolidated Financial Statements|ITEM\s+8", window, re.I):
        return "Notes / Item 8"
    if re.search(r"ITEM\s+1\b", window, re.I):
        return "Item 1 Business"
    return "filing_text"


def _findings_from_text(
    text: str,
    source_label: str,
    *,
    accession: str | None = None,
) -> list[Stage4SemanticFinding]:
    findings: list[Stage4SemanticFinding] = []
    if not text:
        return findings
    lower = text.lower()
    for topic, patterns, classification, evidence_kind, escalate_default, dimension in _KEYWORD_MAP:
        for pat in patterns:
            m = re.search(pat, lower, flags=re.IGNORECASE)
            if not m:
                continue
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 220)
            excerpt = text[start:end].strip()
            section = _section_for_pos(text, m.start())
            materiality = "watchable" if escalate_default else "not_assessed"
            reason = (
                f"Filing text hit for '{topic}' in {source_label} ({section}); "
                "human judges materiality (no numeric bar)."
            )
            escalate = escalate_default
            # Quantified organic / FX / volume language → keep COMPANY_EXPLANATION
            # (do not silently promote to FACT unless clearly a table/number FACT context)
            if topic in {"organic_vs_acquired", "fx_constant_currency", "volume_price_mix"}:
                if re.search(r"\d+\s*%|\$\s*[0-9]|percent", excerpt, re.I):
                    evidence_kind = "COMPANY_EXPLANATION"
                    materiality = "watchable"
                    reason = (
                        f"Quantified {topic} language in MD&A — COMPANY_EXPLANATION "
                        "(not auto-promoted to FACT; no invented Normalized %)"
                    )
            if topic == "fp_channel_stuffing":
                materiality = "material"
                escalate = True
                reason = (
                    "Channel stuffing / pull-forward language — escalate FP6 watch "
                    "(evidence tag, not auto-fail)"
                )
            if topic == "comparability_perimeter":
                materiality = "watchable"
                escalate = True
                reason = (
                    "Perimeter / spin / discontinued-ops language — harvest for "
                    "COMPARABILITY_BREAK honesty (as-reported preserved; no recast)"
                )
            findings.append(
                Stage4SemanticFinding(
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
                    dimension=dimension,
                )
            )
            break
    return findings


def load_stage4_semantic_from_fixture(
    notes_path: Path | None = None,
    notes_payload: dict | None = None,
) -> Stage4SemanticReview:
    data: dict[str, Any] = {}
    if notes_payload:
        data = dict(notes_payload)
    elif notes_path and notes_path.exists():
        raw_text = notes_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return heuristic_stage4_semantic(raw_text, source_label=str(notes_path.name))

    if data.get("filled") is False and str(data.get("review_source", "")).startswith(
        "uat_placeholder"
    ):
        return placeholder_stage4_semantic()

    findings: list[Stage4SemanticFinding] = []
    for item in data.get("findings") or []:
        if not isinstance(item, dict):
            continue
        findings.append(
            Stage4SemanticFinding(
                topic=str(item.get("topic") or "other"),
                citation=item.get("citation"),
                classification=str(item.get("classification") or "mdna"),
                evidence_kind=str(item.get("evidence_kind") or "COMPANY_EXPLANATION"),
                materiality_judgment=str(item.get("materiality_judgment") or "not_assessed"),
                materiality_reason=str(item.get("materiality_reason") or ""),
                escalate_to_human=bool(item.get("escalate_to_human", False)),
                excerpt=item.get("excerpt"),
                accession=item.get("accession"),
                section=item.get("section"),
                dimension=item.get("dimension"),
            )
        )

    for key in ("notes_text", "mdna_text", "ir_text", "earnings_text", "segment_text"):
        blob = data.get(key)
        if isinstance(blob, str) and blob.strip():
            findings.extend(_findings_from_text(blob, key))

    return Stage4SemanticReview(
        findings=findings,
        organic_acquired_notes=data.get("organic_acquired_notes"),
        fx_notes=data.get("fx_notes"),
        volume_price_mix_notes=data.get("volume_price_mix_notes"),
        geography_product_notes=data.get("geography_product_notes"),
        runway_claim_notes=data.get("runway_claim_notes"),
        dilution_notes=data.get("dilution_notes"),
        ma_notes=data.get("ma_notes"),
        backlog_rpo_notes=data.get("backlog_rpo_notes"),
        recurring_notes=data.get("recurring_notes"),
        cycle_notes=data.get("cycle_notes"),
        checklist_coverage=list(data.get("checklist_coverage") or CHECKLIST_TOPICS),
        review_source=data.get("review_source") or "fixture",
        filled=True,
    )


def heuristic_stage4_semantic(
    text: str,
    *,
    source_label: str = "heuristic_text",
    accession: str | None = None,
) -> Stage4SemanticReview:
    findings = _findings_from_text(text or "", source_label, accession=accession)
    return Stage4SemanticReview(
        findings=findings,
        checklist_coverage=list(CHECKLIST_TOPICS),
        review_source="heuristic",
        filled=bool(text),
        organic_acquired_notes=_note_from_findings(findings, "organic_vs_acquired"),
        fx_notes=_note_from_findings(findings, "fx_constant_currency"),
        volume_price_mix_notes=_note_from_findings(findings, "volume_price_mix"),
        geography_product_notes=_note_from_findings(findings, "geography_product"),
        runway_claim_notes=_note_from_findings(findings, "runway_claim"),
        dilution_notes=_note_from_findings(findings, "dilution_sbc"),
        ma_notes=_note_from_findings(findings, "ma_inorganic"),
        backlog_rpo_notes=_note_from_findings(findings, "backlog_rpo"),
        recurring_notes=_note_from_findings(findings, "recurring_revenue"),
        cycle_notes=_note_from_findings(findings, "cycle_base_effect"),
    )


def _note_from_findings(findings: list[Stage4SemanticFinding], topic: str) -> str | None:
    for f in findings:
        if f.topic == topic and f.excerpt:
            return f"{f.section or ''}: {f.excerpt[:240]}"
    return None


def placeholder_stage4_semantic() -> Stage4SemanticReview:
    return Stage4SemanticReview(
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


def run_stage4_semantic_from_filings(
    ticker: str,
    *,
    root: Path | None = None,
    persist: bool = True,
) -> Stage4SemanticReview:
    """Production-like Stage 4 semantic: scan 10-K/10-Q for growth topics."""
    ticker = ticker.upper()
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)
    meta = storage.load_meta(ticker, root)
    cik = str(meta.get("cik") or "").zfill(10) if meta.get("cik") else None

    findings: list[Stage4SemanticFinding] = []
    sources_used: list[str] = []
    plain_blobs: list[tuple[str, str, str | None]] = []

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
        if path is None:
            cand = config.SEC_CACHE_DIR / "filings" / Path(primary).name
            path = cand if cand.exists() else None
        if path is None or not path.exists():
            findings.append(
                Stage4SemanticFinding(
                    topic="filing_retrieval",
                    citation=f"accession={accession}; primary={primary}",
                    classification="other",
                    evidence_kind="MODEL_INFERENCE",
                    materiality_judgment="unclear",
                    materiality_reason=(
                        "Official filing primary unavailable — semantic incomplete for accession"
                    ),
                    escalate_to_human=True,
                    accession=accession,
                )
            )
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        plain = html_to_text(raw)
        label = f"{form}:{accession}:{path.name}"
        sources_used.append(label)
        plain_blobs.append((label, plain, accession))
        findings.extend(_findings_from_text(plain, label, accession=accession))

    if not plain_blobs:
        # Do NOT scan the shared SEC_CACHE_DIR/filings tree — that mixes tickers
        # (e.g. KO HTML reused for ROP). Require ticker-scoped Source/filings metas.
        findings.append(
            Stage4SemanticFinding(
                topic="filing_retrieval",
                citation=f"ticker={ticker}; Source/filings empty or primary unavailable",
                classification="other",
                evidence_kind="MODEL_INFERENCE",
                materiality_judgment="unclear",
                materiality_reason=(
                    "No ticker-scoped periodic filing text available for Stage 4 semantic — "
                    "refusing shared-cache fallback to avoid cross-ticker contamination"
                ),
                escalate_to_human=True,
            )
        )

    # Also scan IR / notes text if present
    notes_dir = storage.company_dir(ticker, root) / "Source" / "notes"
    if notes_dir.exists():
        for np in notes_dir.glob("*.md"):
            plain = np.read_text(encoding="utf-8", errors="ignore")
            findings.extend(_findings_from_text(plain, f"notes:{np.name}"))
            plain_blobs.append((f"notes:{np.name}", plain, None))

    seen: set[str] = set()
    deduped: list[Stage4SemanticFinding] = []
    for f in findings:
        if f.topic in seen and f.topic != "filing_retrieval":
            continue
        seen.add(f.topic)
        deduped.append(f)

    review = Stage4SemanticReview(
        findings=deduped,
        organic_acquired_notes=_note_from_findings(deduped, "organic_vs_acquired"),
        fx_notes=_note_from_findings(deduped, "fx_constant_currency"),
        volume_price_mix_notes=_note_from_findings(deduped, "volume_price_mix"),
        geography_product_notes=_note_from_findings(deduped, "geography_product"),
        runway_claim_notes=_note_from_findings(deduped, "runway_claim"),
        dilution_notes=_note_from_findings(deduped, "dilution_sbc"),
        ma_notes=_note_from_findings(deduped, "ma_inorganic"),
        backlog_rpo_notes=_note_from_findings(deduped, "backlog_rpo"),
        recurring_notes=_note_from_findings(deduped, "recurring_revenue"),
        cycle_notes=_note_from_findings(deduped, "cycle_base_effect"),
        checklist_coverage=list(CHECKLIST_TOPICS),
        review_source="filing_heuristic",
        filled=bool(plain_blobs),
    )
    if persist:
        persist_stage4_semantic(ticker, review, root=root, sources_used=sources_used)
    return review


def persist_stage4_semantic(
    ticker: str,
    review: Stage4SemanticReview,
    *,
    root: Path | None = None,
    sources_used: list[str] | None = None,
) -> Path:
    cdir = storage.company_dir(ticker, root)
    notes_dir = cdir / "Source" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = notes_dir / "stage4_semantic_review.json"
    payload = review.to_dict()
    payload["sources_used"] = sources_used or []
    payload["note"] = (
        "Stage 4 growth Notes/MD&A/IR pass from official filing text (heuristic). "
        "No invented organic %, TAM, or scores. Evidence kinds: "
        "FACT | COMPANY_EXPLANATION | MODEL_INFERENCE."
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def semantic_text_blob(review: Stage4SemanticReview | None) -> str:
    if not review:
        return ""
    parts = []
    for attr in (
        "organic_acquired_notes",
        "fx_notes",
        "volume_price_mix_notes",
        "geography_product_notes",
        "runway_claim_notes",
        "dilution_notes",
        "ma_notes",
        "backlog_rpo_notes",
        "recurring_notes",
        "cycle_notes",
    ):
        v = getattr(review, attr, None)
        if v:
            parts.append(str(v))
    for f in review.findings:
        if f.excerpt:
            parts.append(f.excerpt)
        if f.topic:
            parts.append(f.topic.replace("_", " "))
    return " ".join(parts)
