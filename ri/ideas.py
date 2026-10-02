"""ResearchIdea flags only — never auto-promote to FA/GREEN/watchlist."""
from __future__ import annotations
from .ids import new_id, utc_now

def flag_ideas(clusters: list[dict], tracked_tickers: set[str]) -> list[dict]:
    ideas = []
    for c in clusters:
        mat = c.get("materiality")
        if mat not in ("high", "medium"):
            continue
        ent_tickers = set()
        for e in c.get("_entities") or []:
            if e.get("ticker"):
                ent_tickers.add(e["ticker"])
        hits = ent_tickers & tracked_tickers
        c["tracked_company_hits"] = sorted(hits)
        is_new = bool(ent_tickers - tracked_tickers) or not ent_tickers
        if hits or (mat == "high" and is_new) or (mat == "medium" and is_new and "CAPEX" in (c.get("themes") or [])):
            ideas.append({
                "id": new_id("idea_"),
                "event_id": c["id"],
                "entity_ids": c.get("entity_ids") or [],
                "why_interesting": c.get("materiality_reason") or c.get("summary"),
                "suggested_next": "watch_intel" if not hits else "consider_fa_package",
                "auto_promoted": False,
                "created_at": utc_now(),
                "status": "open",
                "synthetic_demo": True,
            })
    return ideas
