# Fixture dry-run notes

Date: 2026-09-13
Semantic engine: ri-heuristic-semantic-v1 (RI mode, not a sub-agent; real LLM API swappable later)

## Counts
{
  "received": 19,
  "unique": 16,
  "skipped_dup": 3,
  "skipped_ids": [
    "src_fix02",
    "src_fix03",
    "src_fix17"
  ],
  "clusters": 13,
  "ideas": 7,
  "entities": 8,
  "production_tracked_count": 0,
  "view_paths": [
    "/workspace/butterbear/drive/transition/01_Research/views/latest_material_events.md",
    "/workspace/butterbear/drive/transition/01_Research/views/companies_mentioned.md",
    "/workspace/butterbear/drive/transition/01_Research/views/sectors_themes.md",
    "/workspace/butterbear/drive/transition/01_Research/views/commodities.md",
    "/workspace/butterbear/drive/transition/01_Research/views/fx.md",
    "/workspace/butterbear/drive/transition/01_Research/views/tracked_updates.md",
    "/workspace/butterbear/drive/transition/01_Research/views/research_ideas.md",
    "/workspace/butterbear/drive/transition/01_Research/views/unresolved.md"
  ]
}

## Checks
- production tracked empty: OK
- auto_promoted all false: OK
- TR src_fix16 untranslated: OK
- expected dups skipped subset: True

## Architecture
Single Python package `ri/` with modules: adapters, normalize, dedup, providers.semantic, cluster, ideas, views, storage, ops_log, ops_weekly, pipeline.
No Dedup/Verification/Messenger/Entity/Materiality/Ops agents.

## Subscriptions
Dragonomi / Emtia Defteri adapters: NOT implemented (blocked).
