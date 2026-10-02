"""RI v1 end-to-end — single component orchestration (no sub-agents)."""
from __future__ import annotations
import json
from pathlib import Path
from . import config, storage
from .adapters import json_fixture, emtia_defteri
from .normalize import normalize_source_item
from .dedup import dedup_articles
from .providers.semantic import extract_batch
from .cluster import cluster_extracts
from .ideas import flag_ideas
from .views import render_all
from .ops_log import tracked_run
from .ids import utc_now

HARVEST_DIR = config.ROOT / "ri_data" / "harvests"
HARVEST_GLOB = "emtia_defteri_live_*.json"


def latest_emtia_harvest(harvest_dir: Path | None = None) -> Path:
    """Return newest emtia_defteri_live_*.json by mtime; raise if none."""
    d = harvest_dir or HARVEST_DIR
    files = sorted(d.glob(HARVEST_GLOB), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(
            f"No harvest files matching {HARVEST_GLOB} under {d}"
        )
    return files[0]


def run_fixture_pipeline(
    fixture_path: Path | None = None,
    demo_tracked_path: Path | None = None,
    use_production_tracked: bool = True,
) -> dict:
    fixture_path = fixture_path or (config.DRIVE_FIXTURES / "mock_source_items_v1.json")
    demo_tracked_path = demo_tracked_path or (config.DRIVE_FIXTURES / "demo_tracked_companies.json")

    with tracked_run("ri_ingest_batch", model="none", notes="json fixture ingest") as log:
        items = json_fixture.ingest(fixture_path)
        log.source_items = len(items)
        log.tool_calls = 1

    with tracked_run("ri_normalize_dedup", model="none") as log:
        existing = storage.read_jsonl(storage.source_items_path())
        normalized = [normalize_source_item(it) for it in items]
        unique, skipped = dedup_articles(normalized, existing)
        for s in skipped:
            s["updated_at"] = utc_now()
        for u in unique:
            u["updated_at"] = utc_now()
        storage.append_jsonl(storage.source_items_path(), unique + skipped)
        log.source_items = len(normalized)
        log.notes = f"unique={len(unique)} skipped_dup={len(skipped)}"
        log.tool_calls = 1

    with tracked_run("ri_extract_batch", model="ri-heuristic-semantic-v1") as log:
        extracts, usage = extract_batch(unique)
        log.LLM_calls = usage["LLM_calls"]
        log.input_tokens = usage["input_tokens"]
        log.output_tokens = usage["output_tokens"]
        log.model = usage["model"]
        log.source_items = len(unique)

    with tracked_run("ri_cluster", model="ri-heuristic-semantic-v1") as log:
        clusters = cluster_extracts(unique, extracts)
        # entity upsert
        ent_map = {}
        for c in clusters:
            for e in c.get("_entities") or []:
                ent_map[e["id"]] = e
        # tracked join: production empty by default; optional demo for fixture validation only
        prod = storage.load_tracked_companies()
        tracked_tickers = {c.get("ticker") for c in prod.get("companies", []) if c.get("ticker")}
        demo_tickers = set()
        if demo_tracked_path.exists():
            demo = json.loads(demo_tracked_path.read_text(encoding="utf-8"))
            demo_tickers = {c.get("ticker") for c in demo.get("companies", []) if c.get("ticker")}
        # For dry-run visibility: compute hits against demo list but DO NOT write demo into production
        join_tickers = tracked_tickers | demo_tickers
        for c in clusters:
            hits = []
            for e in c.get("_entities") or []:
                if e.get("ticker") and e["ticker"] in join_tickers:
                    hits.append(e["ticker"])
            c["tracked_company_hits"] = sorted(set(hits))
            if hits and demo_tickers.intersection(hits) and not tracked_tickers.intersection(hits):
                c.setdefault("adapter_meta_note", "tracked hit via FIXTURE demo list only")
        # strip private _entities before persist but keep for ideas
        storage.append_jsonl(storage.entities_path(), list(ent_map.values()))
        persist_clusters = []
        for c in clusters:
            pc = {k: v for k, v in c.items() if k != "_entities"}
            persist_clusters.append(pc)
        storage.append_jsonl(storage.events_path(), persist_clusters)
        log.source_items = len(unique)
        log.notes = f"clusters={len(clusters)}"
        log.LLM_calls = 0

    with tracked_run("ri_idea_flag", model="ri-heuristic-semantic-v1") as log:
        ideas = flag_ideas(clusters, join_tickers)
        for idea in ideas:
            idea["auto_promoted"] = False
        storage.append_jsonl(storage.ideas_path(), ideas)
        # ensure production tracked unchanged
        prod2 = storage.load_tracked_companies()
        assert prod2.get("companies") == [], "production tracked must remain empty"
        log.notes = f"ideas={len(ideas)}; production_tracked_empty=True"
        log.LLM_calls = len(ideas)

    with tracked_run("ri_views_refresh", model="none") as log:
        paths = render_all(clusters, ideas, list(ent_map.values()), skipped_n=len(skipped))
        log.notes = f"views={len(paths)}"
        log.tool_calls = 1

    return {
        "received": len(items),
        "unique": len(unique),
        "skipped_dup": len(skipped),
        "skipped_ids": [s["id"] for s in skipped],
        "clusters": len(clusters),
        "ideas": len(ideas),
        "entities": len(ent_map),
        "production_tracked_count": 0,
        "view_paths": paths,
    }


def run_emtia_harvest_pipeline(harvest_path: Path | None = None) -> dict:
    """Ingest an Emtia Defteri harvest JSON through the RI pipeline.

    Uses production tracked_companies only (empty OK). Never auto-promotes.
    Does not merge demo/fixture tracked lists. Writes via existing Drive storage.
    """
    path = Path(harvest_path) if harvest_path else latest_emtia_harvest()

    with tracked_run("ri_ingest_batch", model="none", notes=f"emtia harvest {path.name}") as log:
        items = emtia_defteri.ingest(path)
        log.source_items = len(items)
        log.tool_calls = 1

    with tracked_run("ri_normalize_dedup", model="none") as log:
        existing = storage.read_jsonl(storage.source_items_path())
        normalized = [normalize_source_item(it) for it in items]
        unique, skipped = dedup_articles(normalized, existing)
        for s in skipped:
            s["updated_at"] = utc_now()
        for u in unique:
            u["updated_at"] = utc_now()
        storage.append_jsonl(storage.source_items_path(), unique + skipped)
        log.source_items = len(normalized)
        log.notes = f"unique={len(unique)} skipped_dup={len(skipped)}"
        log.tool_calls = 1

    with tracked_run("ri_extract_batch", model="ri-heuristic-semantic-v1") as log:
        extracts, usage = extract_batch(unique)
        log.LLM_calls = usage["LLM_calls"]
        log.input_tokens = usage["input_tokens"]
        log.output_tokens = usage["output_tokens"]
        log.model = usage["model"]
        log.source_items = len(unique)

    with tracked_run("ri_cluster", model="ri-heuristic-semantic-v1") as log:
        clusters = cluster_extracts(unique, extracts)
        ent_map = {}
        for c in clusters:
            for e in c.get("_entities") or []:
                ent_map[e["id"]] = e
        # production tracked only — empty OK; never merge demo list
        prod_before = storage.load_tracked_companies()
        tracked_tickers = {
            c.get("ticker") for c in prod_before.get("companies", []) if c.get("ticker")
        }
        for c in clusters:
            hits = []
            for e in c.get("_entities") or []:
                if e.get("ticker") and e["ticker"] in tracked_tickers:
                    hits.append(e["ticker"])
            c["tracked_company_hits"] = sorted(set(hits))
        storage.append_jsonl(storage.entities_path(), list(ent_map.values()))
        persist_clusters = []
        for c in clusters:
            pc = {k: v for k, v in c.items() if k != "_entities"}
            persist_clusters.append(pc)
        storage.append_jsonl(storage.events_path(), persist_clusters)
        log.source_items = len(unique)
        log.notes = f"clusters={len(clusters)}; tracked_tickers={len(tracked_tickers)}"
        log.LLM_calls = 0

    with tracked_run("ri_idea_flag", model="ri-heuristic-semantic-v1") as log:
        ideas = flag_ideas(clusters, tracked_tickers)
        for idea in ideas:
            idea["auto_promoted"] = False
        storage.append_jsonl(storage.ideas_path(), ideas)
        prod_after = storage.load_tracked_companies()
        assert prod_after.get("companies") == prod_before.get("companies"), (
            "production tracked must not change during harvest pipeline"
        )
        assert all(not idea.get("auto_promoted") for idea in ideas)
        log.notes = (
            f"ideas={len(ideas)}; production_tracked_count={len(tracked_tickers)}; "
            "auto_promoted=False"
        )
        log.LLM_calls = len(ideas)

    with tracked_run("ri_views_refresh", model="none") as log:
        paths = render_all(clusters, ideas, list(ent_map.values()), skipped_n=len(skipped))
        log.notes = f"views={len(paths)}"
        log.tool_calls = 1

    return {
        "harvest_path": str(path),
        "received": len(items),
        "unique": len(unique),
        "skipped_dup": len(skipped),
        "skipped_ids": [s["id"] for s in skipped],
        "clusters": len(clusters),
        "ideas": len(ideas),
        "entities": len(ent_map),
        "production_tracked_count": len(tracked_tickers),
        "auto_promoted": False,
        "view_paths": paths,
    }
