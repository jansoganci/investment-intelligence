"""Deterministic normalize — preserve language; never translate for storage."""
from __future__ import annotations
import hashlib
import re
import unicodedata

def detect_language(text: str) -> str:
    if not text or not text.strip():
        return "unknown"
    # Turkish-specific chars
    if re.search(r"[ğüşıöçĞÜŞİÖÇ]", text):
        return "tr"
    # Heuristic: high ASCII letter ratio → en; else other
    letters = re.findall(r"[A-Za-zÀ-ÿ]", text)
    if len(letters) < 20:
        return "unknown"
    return "en"

def clean_text(text: str) -> str:
    if text is None:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def content_hash(cleaned: str) -> str:
    norm = re.sub(r"\s+", " ", cleaned.lower()).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:32]

def normalize_source_item(item: dict) -> dict:
    raw = item.get("raw_content") or item.get("cleaned_content") or ""
    cleaned = clean_text(raw)
    lang = item.get("language") or detect_language(cleaned)
    out = dict(item)
    out["cleaned_content"] = cleaned
    if raw and not out.get("raw_content"):
        out["raw_content"] = raw
    out["language"] = lang
    out["content_hash"] = content_hash(cleaned)
    out["processing_status"] = "normalized"
    return out
