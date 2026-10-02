"""Structured views — Turkish default summaries; no daily essays."""
from __future__ import annotations
from pathlib import Path
from . import config

def _write(name: str, lines: list[str]) -> Path:
    config.DRIVE_VIEWS.mkdir(parents=True, exist_ok=True)
    p = config.DRIVE_VIEWS / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p

def render_all(clusters, ideas, entities, skipped_n: int) -> list[str]:
    paths = []
    mat = [c for c in clusters if c.get("materiality") in ("high", "medium")]
    lines = ["# Son maddi olaylar", ""]
    for c in sorted(mat, key=lambda x: x.get("last_seen_at") or "", reverse=True):
        lines.append(f"- **{c['materiality'].upper()}** `{c['id']}`: {c.get('summary')}")
        lines.append(f"  - Neden: {c.get('materiality_reason')}")
    paths.append(str(_write("latest_material_events.md", lines)))

    co = [e for e in entities if e.get("kind") == "company"]
    lines = ["# Bahsedilen şirketler (dikkat ≠ alfa)", ""]
    for e in co:
        lines.append(f"- {e.get('ticker') or e.get('name')} (`{e['id']}`) synthetic_demo={e.get('synthetic_demo')}")
    paths.append(str(_write("companies_mentioned.md", lines)))

    lines = ["# Sektör / tema dikkat haritası", ""]
    themes = {}
    for c in clusters:
        for t in c.get("themes") or []:
            themes[t] = themes.get(t, 0) + 1
    for t, n in sorted(themes.items(), key=lambda x: -x[1]):
        lines.append(f"- {t}: {n}")
    paths.append(str(_write("sectors_themes.md", lines)))

    lines = ["# Emtia", ""]
    for c in clusters:
        if "commodities" in (c.get("domains") or []):
            lines.append(f"- {c.get('summary')}")
    paths.append(str(_write("commodities.md", lines)))

    lines = ["# FX", ""]
    for c in clusters:
        if "fx" in (c.get("domains") or []):
            lines.append(f"- {c.get('summary')}")
    paths.append(str(_write("fx.md", lines)))

    lines = ["# Takipteki şirket güncellemeleri", ""]
    hits = [c for c in clusters if c.get("tracked_company_hits")]
    if not hits:
        lines.append("_Üretim tracked listesi boş veya bu koşuda eşleşme yok / fixture demo tracked ayrı._")
    for c in hits:
        lines.append(f"- {c.get('tracked_company_hits')}: {c.get('summary')}")
    paths.append(str(_write("tracked_updates.md", lines)))

    lines = ["# ResearchIdea bayrakları (otomatik yükseltme YOK)", ""]
    for i in ideas:
        lines.append(f"- `{i['id']}` event={i['event_id']} next={i['suggested_next']} auto_promoted={i['auto_promoted']}")
        lines.append(f"  - {i['why_interesting']}")
    paths.append(str(_write("research_ideas.md", lines)))

    lines = ["# Çözülmemiş / düşük güven", ""]
    for c in clusters:
        if c.get("materiality") == "review_required" or (c.get("confidence") or 1) < 0.4:
            lines.append(f"- `{c['id']}`: {c.get('summary')}")
    lines.append(f"\n_Atlanan mükerrer makale sayısı: {skipped_n}_")
    paths.append(str(_write("unresolved.md", lines)))
    return paths
