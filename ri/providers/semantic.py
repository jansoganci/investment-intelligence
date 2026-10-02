"""
Semantic modes of Research Intelligence (NOT separate agents).
Uses a rubric-constrained heuristic engine for offline/mock runs.
Swap call_llm() later for real API without changing pipeline shape.
"""
from __future__ import annotations
import re
from .. import config
from ..ids import new_id, utc_now

TICKER_RE = re.compile(r"\b([A-Z]{1,5}(?:\.DEMO)?)\b")

HIGH_PAT = re.compile(
    r"guidance|CAPEX|capacity|offtake|acquisition|acquire|divest|regulatory|regulation|"
    r"financing|balance[- ]sheet|raised its|revenue guidance|major CAPEX|material|"
    r"rehberlik|kapasite|satın al",
    re.I,
)
MED_PAT = re.compile(
    r"demand|pricing|sector|trend|policy discussion|industry|commodity|bakır talebi|"
    r"early-stage|monitor",
    re.I,
)
LOW_PAT = re.compile(
    r"opinion|routine|minor|generic|no new evidence|I love|promotional|rumor|unconfirmed",
    re.I,
)

def _tokens_estimate(text: str) -> int:
    return max(1, len(text) // 4)

def classify_materiality(text: str) -> tuple[str, str]:
    """Apply LOCKED rubric; return (enum, reason)."""
    t = text or ""
    if len(t.strip()) < 40:
        return "review_required", "Yetersiz metin; maddilik değerlendirilemiyor (REVIEW_REQUIRED)."
    if re.search(r"unclear whether|not specified|insufficient", t, re.I):
        return "review_required", "Fiili sonuç / rehberlik / tahmin ayrımı belirsiz; REVIEW_REQUIRED."
    # Unconfirmed rumor / pure opinion → LOW even if M&A keywords appear
    if re.search(r"\bunconfirmed rumor\b|\brumor\b|opinion column|no new evidence", t, re.I):
        return "low", "Doğrulanmamış söylenti/yorum veya yeni kanıt yok; tez etkisi net değil (LOW)."
    if LOW_PAT.search(t) and not HIGH_PAT.search(t):
        return "low", "Rutin/tekrar/yorum veya zayıf kanıt; tez etkisi net değil (LOW)."
    if HIGH_PAT.search(t):
        return "high", "Rehberlik/CAPEX/kapasite/müşteri/M&A/finansman gibi tez veya temel metrikleri etkileyebilecek gelişme (HIGH)."
    if MED_PAT.search(t):
        return "medium", "Sektör/talep/fiyat veya izlenmesi gereken ara gelişme; henüz net tez kırıcı değil (MEDIUM)."
    return "review_required", "Sınıflandırma için kanıt yetersiz (REVIEW_REQUIRED)."

def claim_types(text: str) -> list[dict]:
    claims = []
    if re.search(r"company guidance|raised its|management guided|rehberlik", text, re.I):
        claims.append({"text": "company guidance signal", "classification": "COMPANY_GUIDANCE"})
    if re.search(r"analyst estimated|price target|sell-side", text, re.I):
        claims.append({"text": "analyst estimate/opinion", "classification": "ANALYST_ESTIMATE"})
    if re.search(r"opinion column|I love|rumor|unconfirmed", text, re.I):
        claims.append({"text": "opinion/rumor", "classification": "SOURCE_OPINION"})
    if re.search(r"said it completed|reports|signed|rose after", text, re.I):
        claims.append({"text": "reported development", "classification": "FACT"})
    if not claims:
        claims.append({"text": "general statement", "classification": "BOT_INFERENCE"})
    return claims

def extract_entities(text: str, title: str = "") -> list[dict]:
    blob = f"{title}\n{text}"
    ents = []
    # demo tickers
    for m in TICKER_RE.findall(blob):
        if m in {"USD", "TRY", "EV", "US", "IPO", "CAPEX", "FCF", "A", "I"}:
            continue
        if ".DEMO" in m or m.endswith("DEMO") or m in {"FCX", "NVDA", "ALB"}:
            ticker = m if ".DEMO" in m else f"{m}.DEMO"
            ents.append({
                "id": f"ent_{ticker.lower().replace('.', '_')}",
                "kind": "company",
                "name": ticker,
                "ticker": ticker,
                "aliases": [],
                "geography": "US",
                "sector": None,
                "status": "active",
                "notes": "synthetic_demo",
                "synthetic_demo": True,
            })
    if re.search(r"copper|bakır", blob, re.I):
        ents.append({"id": "ent_copper", "kind": "commodity", "name": "Copper", "ticker": None,
                     "aliases": ["bakır"], "geography": None, "sector": None, "status": "active",
                     "notes": None, "synthetic_demo": True})
    if re.search(r"USD/TRY|USDTRY", blob, re.I):
        ents.append({"id": "ent_usdtry", "kind": "fx_pair", "name": "USD/TRY", "ticker": None,
                     "aliases": [], "geography": None, "sector": None, "status": "active",
                     "notes": None, "synthetic_demo": True})
    if re.search(r"semiconductor|yarı iletken|semis", blob, re.I):
        ents.append({"id": "ent_semis", "kind": "sector", "name": "Semiconductors", "ticker": None,
                     "aliases": [], "geography": None, "sector": "semiconductors", "status": "active",
                     "notes": None, "synthetic_demo": True})
    if re.search(r"China|Çin", blob, re.I):
        ents.append({"id": "ent_cn", "kind": "geography", "name": "China", "ticker": None,
                     "aliases": ["Çin"], "geography": "CN", "sector": None, "status": "active",
                     "notes": None, "synthetic_demo": True})
    # dedupe by id
    seen, out = set(), []
    for e in ents:
        if e["id"] not in seen:
            seen.add(e["id"])
            out.append(e)
    return out

def themes_and_types(text: str) -> tuple[list[str], list[str], list[str]]:
    themes, etypes, domains = [], [], []
    if re.search(r"CAPEX|capacity|kapasite", text, re.I):
        themes.append("CAPEX"); etypes.append("capacity")
    if re.search(r"guidance|rehberlik", text, re.I):
        themes.append("guidance"); etypes.append("guidance")
    if re.search(r"demand|talep", text, re.I):
        themes.append("demand")
    if re.search(r"offtake|customer", text, re.I):
        themes.append("customer"); etypes.append("commercial")
    if re.search(r"M&A|acquir|rumor", text, re.I):
        themes.append("M&A"); etypes.append("M&A")
    if re.search(r"copper|bakır|commodity", text, re.I):
        domains.append("commodities")
    if re.search(r"USD/TRY|FX", text, re.I):
        domains.append("fx")
    if re.search(r"equity|miner|NVDA|FCX|company|listing", text, re.I):
        domains.append("equities")
    if not domains:
        domains.append("macro")
    return themes, etypes, domains

def summarize_tr(title: str, text: str, materiality: str) -> str:
    return f"[{materiality.upper()}] {title}. Özet: {(text or '')[:180].strip()}…"

def extract_item(item: dict) -> dict:
    """RI semantic mode: extract structure for one SourceItem."""
    text = item.get("cleaned_content") or item.get("raw_content") or ""
    title = item.get("title") or ""
    mat, reason = classify_materiality(text)
    ents = extract_entities(text, title)
    themes, etypes, domains = themes_and_types(text)
    geos = []
    if re.search(r"China|Çin", text, re.I):
        geos.append("CN")
    if re.search(r"US|U\.S\.|Amerika", text, re.I) or any(e.get("ticker") for e in ents if e["kind"]=="company"):
        geos.append("US")
    if not geos:
        geos.append("unknown")
    in_tok = _tokens_estimate(text)
    out_tok = 120
    return {
        "source_item_id": item["id"],
        "entities": ents,
        "geography": geos,
        "domains": domains,
        "themes": themes,
        "event_types": etypes,
        "materiality": mat,
        "materiality_reason": reason,
        "claim_bundle": claim_types(text),
        "summary": summarize_tr(title, text, mat),
        "summary_language": "tr",
        "confidence": 0.55 if mat != "review_required" else 0.3,
        "_usage": {"input_tokens": in_tok, "output_tokens": out_tok, "model": "ri-heuristic-semantic-v1"},
    }

def extract_batch(items: list[dict]) -> tuple[list[dict], dict]:
    results = [extract_item(it) for it in items]
    usage = {"LLM_calls": len(results), "input_tokens": 0, "output_tokens": 0, "model": "ri-heuristic-semantic-v1"}
    for r in results:
        u = r.pop("_usage")
        usage["input_tokens"] += u["input_tokens"]
        usage["output_tokens"] += u["output_tokens"]
    return results, usage
