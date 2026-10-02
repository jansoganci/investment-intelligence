"""Hybrid event clustering — code keys + semantic similarity assist (same RI component)."""
from __future__ import annotations
import re
from .ids import new_id, utc_now

def _blocking_key(extract: dict, item: dict) -> str:
    tickers = sorted({e["ticker"] for e in extract.get("entities", []) if e.get("ticker")})
    day = (item.get("published_at") or item.get("received_at") or "")[:10]
    et = ",".join(sorted(extract.get("event_types") or ["na"]))[:40]
    if tickers:
        return f"{tickers[0]}|{day}|{et}"
    themes = ",".join(sorted(extract.get("themes") or ["na"]))[:40]
    return f"theme:{themes}|{day}"

def _title_tokens(title: str) -> set[str]:
    return set(re.findall(r"[a-zA-ZğüşıöçĞÜŞİÖÇ0-9]{3,}", (title or "").lower()))

def should_merge(a_item, a_ex, b_item, b_ex) -> bool:
    # same blocking key + overlapping title tokens or shared ticker
    if _blocking_key(a_ex, a_item) != _blocking_key(b_ex, b_item):
        # still merge if nearly identical CAPEX copper FCX stories on same day
        ta, tb = _title_tokens(a_item.get("title")), _title_tokens(b_item.get("title"))
        shared_t = {e["ticker"] for e in a_ex.get("entities", []) if e.get("ticker")} & {
            e["ticker"] for e in b_ex.get("entities", []) if e.get("ticker")}
        if shared_t and len(ta & tb) >= 2:
            return True
        return False
    ta, tb = _title_tokens(a_item.get("title")), _title_tokens(b_item.get("title"))
    if len(ta & tb) >= 2:
        return True
    # body overlap hint
    ca = (a_item.get("cleaned_content") or "")[:200].lower()
    cb = (b_item.get("cleaned_content") or "")[:200].lower()
    return ca[:80] == cb[:80]

def cluster_extracts(items: list[dict], extracts: list[dict]) -> list[dict]:
    by_id = {i["id"]: i for i in items}
    ex_by = {e["source_item_id"]: e for e in extracts}
    unassigned = [i["id"] for i in items]
    clusters = []
    while unassigned:
        seed = unassigned.pop(0)
        members = [seed]
        changed = True
        while changed:
            changed = False
            for oid in list(unassigned):
                if should_merge(by_id[seed], ex_by[seed], by_id[oid], ex_by[oid]) or any(
                    should_merge(by_id[m], ex_by[m], by_id[oid], ex_by[oid]) for m in members
                ):
                    members.append(oid)
                    unassigned.remove(oid)
                    changed = True
        # build cluster from first extract + merge
        exs = [ex_by[m] for m in members]
        base = exs[0]
        ent = {}
        for e in exs:
            for x in e.get("entities", []):
                ent[x["id"]] = x
        mat_rank = {"high": 3, "medium": 2, "low": 1, "review_required": 0}
        best = max(exs, key=lambda e: mat_rank.get(e["materiality"], 0))
        now = utc_now()
        pubs = [by_id[m].get("published_at") or by_id[m].get("received_at") for m in members]
        cluster = {
            "id": new_id("evt_"),
            "canonical_title": by_id[members[0]].get("title") or "event",
            "summary": best["summary"],
            "summary_language": "tr",
            "first_seen_at": min(p for p in pubs if p),
            "last_seen_at": max(p for p in pubs if p),
            "source_item_ids": members,
            "geography": sorted({g for e in exs for g in e.get("geography", [])}),
            "domains": sorted({d for e in exs for d in e.get("domains", [])}),
            "themes": sorted({t for e in exs for t in e.get("themes", [])}),
            "event_types": sorted({t for e in exs for t in e.get("event_types", [])}),
            "materiality": best["materiality"],
            "materiality_reason": best["materiality_reason"],
            "claim_bundle": best["claim_bundle"],
            "entity_ids": list(ent.keys()),
            "_entities": list(ent.values()),
            "tracked_company_hits": [],
            "confidence": best.get("confidence"),
            "status": "open",
            "created_at": now,
            "updated_at": now,
        }
        clusters.append(cluster)
    return clusters
