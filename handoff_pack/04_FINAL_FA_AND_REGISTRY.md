# 04 — Final FA Synthesis & Company FA History Registry

**Evidence-only** | As of: 2026-10-01 (Europe/Istanbul)  
Both components: **DONE / UAT_ACCEPTED**. Plan §0 remains design-freeze authority (**Plan wins**). No BUY/SELL.

---

## A. Final FA Synthesis

### Status

| Item | Value |
|------|-------|
| Lifecycle | **DONE / UAT_ACCEPTED** (2026-10-01; auth Can Soganci) |
| Canonical | `03_Fundamental/FINAL_FA_SYNTHESIS_PLAN_v1.md` §0 |
| Companions | Decision Pass; Pre-Spec Verify; Research (Plan wins on conflict) |
| Code | `fa/final_fa/` — `run_final_fa` on production `fa_data` |
| Stages 1–9 | Analytical logic **untouched** |
| Pytest at closure | `tests/fa/test_final_fa.py` **20 passed**; full `tests/fa` **343 passed / 3 known Stage 8 freshness fails** (non-blocking) |

### Why Final FA exists (documented)

Given Stages 1–9 evidence packs, produce a **single synthesis** that answers:

1. Final fundamental eligibility (outside-color vs RED/ORANGE/GREEN)  
2. Supports (provenance-tagged)  
3. Challenges (severity-classed, not scored)  
4. Unresolved gaps  
5. Human review queue **0–5** (investment judgment only)

**Synthesis core = evidence reconciliation** — not stage voting / averaging / scorecards.

### Locked principles (Plan §0.F excerpt)

| Principle | Rule |
|-----------|------|
| GREEN ≠ BUY | Eligibility for technical-universe consideration only |
| Missing ≠ RED | Absence → INCOMPLETE / REVIEW / soft challenge |
| TOO_HARD ≠ RED | Unevaluable ≠ hard-elimination |
| REVIEW ≠ ORANGE | REVIEW outside color / blocked; ORANGE inside color / soft residual |
| FACT breaker → REVIEW | Active FACT thesis-breaker → `REVIEW_REQUIRED` until cleared; RED only if human confirms falsify — **not** auto-RED |
| Prefer REVIEW over casual RED | When missing / thin / judgment-open |
| `technical_eligible` | true **iff** `final_state == GREEN` **and** no open `blocks_color=true` |
| ORANGE never TA/watchlist | Always `technical_eligible=false` |

### Completeness matrix (§0.E — WHY soft-missing ≠ GREEN)

| Class | Stages | Rule |
|-------|--------|------|
| Spine REQUIRED | **S1** present and `PROCEED` for any color path | Else map Stage 1 outside-color — **do not paint RED** |
| Core REQUIRED for color | **S2, S3, S6, S8, S9** CURRENT | Missing any → **`INCOMPLETE`** |
| Soft-if-missing | **S4, S5, S7** | Color OK; `S{n}_MISSING` chip; **GREEN forbidden**; **ORANGE max** |

**Why:** User-approved U2 tighten (Pre-Spec Verify Option D) — soft gaps must not sneak into GREEN eligibility.

### Final eligibility states

**Outside Color Universe:** `INCOMPLETE` \| `TOO_HARD` \| `STOP_NO_THESIS` \| `REVIEW_REQUIRED`  
**Inside:** `RED` \| `ORANGE` \| `GREEN`  

Anti-sprawl: no WEAK_GREEN / AMBER / DEEP_RED / PARK. Do not collapse STOP_NO_THESIS into TOO_HARD.

**ORANGE lock:** Complete enough to avoid INCOMPLETE/REVIEW, but material soft conditions / non-blocking gaps prevent GREEN. Not a dump for unevaluable / open FACT breakers.

### Production workflow (LOCKED)

```
ingest S1–9 CURRENT + carries
  → completeness gate
  → map Stage1 outside-color states
  → contradiction engine (≤5)
  → hard-constraint check
  → soft challenge assembly (ORANGE vs GREEN lean; GREEN-cap)
  → human queue proposal (0–5)
  → emit FinalFaSynthesis json+md
  → STOP before watchlist / TA / portfolio / Audit
```

### UAT (accepted)

| Company | Packs | Outcome (v002 CURRENT noted in STATUS) |
|---------|-------|----------------------------------------|
| **ROP** | `ROP_final_fa_uat_report_v2.md` + `ROP_final_fa_uat_accepted_v2.md` | **`ORANGE`** / `technical_eligible=False` (soft-chain; soft-missing S5) |
| **V (Visa)** | `V_final_fa_uat_report_v2.md` + `V_final_fa_uat_accepted_v2.md` | **`REVIEW_REQUIRED`** / `technical_eligible=False` (FACT breaker → REVIEW, not auto-RED) |
| Component | `FINAL_FA_component_uat_accepted.md` | **ACCEPTED → DONE** |

v1 packs preserved. Registry CURRENT Final FA rows `uat_status=accepted` (history preserved).

### Non-blocking limitations (Final FA)

- Soft-missing chips (ROP S5; V S4/S7) → orange ceiling by design  
- ORANGE/REVIEW block GREEN eligibility by design  
- 3 known S8 freshness pytest fails remain (unrelated fix scope)  
- Consume-only — does not rewrite Stage CURRENT  
- No BUY/SELL / weights / watchlist ranking  

### Explicit non-claims

No Stages 1–9 redesign; no TA/watchlist/portfolio; Final System Audit **not** started under Final FA closure.

---

## B. Company FA History / Run Registry

### Status

| Item | Value |
|------|-------|
| Lifecycle | **DONE / UAT_ACCEPTED** (2026-10-01; FINAL UAT + CLOSURE) |
| Canonical | `00_System/COMPANY_FA_HISTORY_REGISTRY_PLAN_v1.md` §0 (Plan wins) |
| Companions | Decision Pass (U1–U14); Architecture research |
| Code | `fa/registry/` + hooks |
| DB | `fa_data/registry/fa_run_registry.sqlite` |
| Stages 1–9 analytical logic | **Unchanged** |

### Why Registry exists (documented)

One-user local-first **ops index**: historical metadata + CURRENT pointers so runs/stages/Final FA are browsable and auditable **without** duplicating analytical JSON. Soft budget → **$0 incremental** storage.

### Standing principles (§0.A)

1. Artifacts on disk = analytical **truth**  
2. Registry = indexed metadata pointing back (paths, scalars, hashes)  
3. Never duplicate full stage / Final FA JSON  
4. Immutable history — append rows; CURRENT = flag/pointer  
5. If registry vs file disagree → **artifact wins**; repair from disk scan  
6. Local-first; Sheets never primary SoR (Sheets C = none in v1)  

### Owns / does not own

| Owns | Does not own |
|------|--------------|
| Indexed history of runs / stage results / Final FA results | Stage lens redesign / recompute |
| CURRENT pointer map (ticker × stage / Final FA) | Silent rewrite of Thesis CURRENT content |
| Regenerable company × stage VIEW matrix | Final FA color engine |
| Thin post-write hooks + backfill scanner | BUY/SELL / scores / watchlist / TA / Audit |
| Backup / export of registry + VIEW | Replacing artifact backup |

### Schema intent (high level)

Tables (LOCKED): `companies`, `analysis_runs`, stage-result rows, Final FA rows, optional `events`.  
Scalars include `process_outcome` / `final_state`, `version_id`, paths, hashes, `uat_status` (`none`\|`pending`\|`accepted`\|`rejected`), `uat_pack_path`.  
Logical uniqueness `(ticker, stage, version_id)`; at most one CURRENT per `(ticker, stage)`.

### Hooks & ops

- Emit registry actions **after** successful artifact write (`fa/registry/hooks.py` wired from Stages 1–9 storage + Final FA path).  
- Backfill = idempotent disk scan.  
- Drift detection vs artifacts.  
- Write-once SQLite backups under `fa_data/registry/backups/`.  
- VIEW: `views/company_stage_matrix.csv` (+ optional `.md`); SQL client browse.  
- Optional JSONL mirror — not competing SoR in primary path.

### Non-blocking limitations (Registry)

- 3 known Stage 8 date/freshness pytest failures (clock) unrelated to Registry  
- Sheets C (none); optional JSONL unused in primary path  

### Explicit non-claims

Registry does not implement Final FA logic (Final FA separate, now also DONE). Does not change Stages 1–9 analytics.
