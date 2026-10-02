"""Article-level dedup: URL + content_hash (deterministic)."""
from __future__ import annotations
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}

def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlparse(url.strip())
        q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
        path = p.path.rstrip("/") or "/"
        return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(q), ""))
    except Exception:
        return url.strip().lower()

def dedup_articles(items: list[dict], existing: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """Return (unique_new, skipped_dups)."""
    seen_url = set()
    seen_hash = set()
    for e in existing or []:
        nu = normalize_url(e.get("source_url"))
        if nu:
            seen_url.add(nu)
        h = e.get("content_hash")
        if h:
            seen_hash.add(h)
    unique, skipped = [], []
    for it in items:
        nu = normalize_url(it.get("source_url"))
        h = it.get("content_hash")
        reason = None
        if nu and nu in seen_url:
            reason = "duplicate_url"
        elif h and h in seen_hash:
            reason = "duplicate_content_hash"
        if reason:
            dup = dict(it)
            dup["processing_status"] = "skipped_dup"
            dup["error"] = reason
            skipped.append(dup)
        else:
            if nu:
                seen_url.add(nu)
            if h:
                seen_hash.add(h)
            unique.append(it)
    return unique, skipped
