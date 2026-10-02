# 02 — System Architecture

**Handoff pack doc** | Structure + locked boundaries | As of: 2026-10-01 (Europe/Istanbul)  
**Sources:** Architecture charter, Data Architecture, Rulebook, code layout (structure only — no code changes).

---

## 1. High-level components (LOCKED)

| Component | Includes | Does not |
|-----------|----------|----------|
| **Research Intelligence** | Broad ingest (Dragonomi + Emtia), normalize/dedupe, entities, summaries, Coverage List follow, flag NEW RESEARCH IDEA | Auto deep-web every item; auto BUY/GREEN; auto-add lists |
| **Fundamental Analysis** | FA List only; Gates 0–2 + Stages 2–9; Final FA synthesis → eligibility + supports/challenges/unresolved | Subjective free-form LLM as sole state; FA on non-listed names; cigar-butt mixed into v1 |
| **Registry** | Indexed run/stage/Final FA metadata + CURRENT pointers (SQLite) | Duplicating full JSON; rewriting analytical artifacts |
| **Technical (later)** | Daily deterministic Özekşi-derived on ACTIVE WATCHLIST | OPT loops; 1m params; all GREEN daily |
| **Operations** | Service log, cost/freshness monitors, PROJECT_STATUS + CHANGELOG | Second analyst |
| **Verification / Messenger** | Modes: materiality-triggered checks; material state-change notices | Fixed % re-research; daily essay spam |

---

## 2. Drive / doc folders

| Folder | Role |
|--------|------|
| `00_System` | Charter, status, changelog, Registry specs, this handoff_pack |
| `01_Research` | RI scope / plan / status / coverage contract |
| `02_Candidates` | Future investigation shortlist |
| `03_Fundamental` | Stage plans, Final FA plans, Rulebook, Ownership Philosophy, Data Architecture |
| `04_Technical` | Özekşi classic (later daily TA) |
| `05_Portfolio` | Later |
| `06_Verification` | Later |
| `07_Operations` | Service log + weekly notes |
| `90/91 Archives` | Historical |

---

## 3. Code layout (structure only)

**Root:** `/workspace/investment_intelligence/`

```
fa/                    # Fundamental Analysis package
  stage1/ … stage9/    # Per-stage modules (evaluate, pipeline, report, storage, …)
  final_fa/            # Final FA synthesis (consume Stages 1–9 CURRENT)
  registry/            # schema, writers, hooks, backfill, drift, backup, views_export
  pipeline.py          # analyze_company path (note: S8/S9 often independent runners)
  ingest.py, map_companyfacts.py, versioning.py, storage.py, …
  sec_client.py, filing_coverage.py, history_coverage.py, quarter_derivation.py
fa_data/               # Runtime data (companies, uat, registry, …)
ri/                    # Research Intelligence
tests/fa/              # Pytest suite
schemas/, fixtures/, fa_fixtures/
PROJECT_STATUS.md, CHANGELOG.md
```

**Independent runners (documented):** `run_stage8`, `run_stage9` — **not** wired into `analyze_company` (non-blocking limitation carried in UAT accepts). Final FA is consume-only of CURRENT artifacts.

---

## 4. FA data backend (Hybrid — LOCKED)

**Source:** `FUNDAMENTAL_DATA_ARCHITECTURE_v1.md`.

- **Official docs** = system of record (SEC filings + user-dropped IR).  
- **SEC spine:** submissions + companyfacts → mapped Normalized draft.  
- **Normalized** versioned per-period (`vNNN` + CURRENT pointer); immutable history.  
- **Code math / LLM semantic / human review** on mapping ambiguity.  
- **No paid financial data feed** (v1).  
- **No live market price until Stage 8.**  
- Default history depth ~5 FY + ~8Q (PROVISIONAL default).  
- FI / Commodity = separate contracts later.

---

## 5. Stage ownership map

| Stage | Owns | Typical outcomes |
|-------|------|------------------|
| 1 Gates 0–2 | Unit, competence, ownership thesis | `PROCEED` / `TOO_HARD` / `REVIEW_REQUIRED` / `STOP_NO_THESIS` — **no colors** |
| 2 Balance sheet | Survival / leverage / liquidity / WC stress | Process outcomes (incl. fragility language in plan); blocks later if Stage 1 ≠ PROCEED |
| 3 Cash generation | OCF/FCF reality, CFS recon, distortions | `PROCEED` \| `CONDITIONAL` \| `REVIEW_REQUIRED` \| `TOO_HARD` — evidence/review |
| 4 Growth quality | Real/valuable/continuable growth vs thesis | Same enum; **NON-TERMINATING** default; Benchmark ≠ gate |
| 5 Business economics | Margin cause + durability (not “high margin”) | Same; NON-TERMINATING; SES = context tag |
| 6 ROIC / reinvestment | Capital conversion + incremental returns | Same; dual ROIC; `S6_H7_*` handoff to S7 |
| 7 Management / allocation | Capital allocation coherence, incentives, etc. | Same; `S7_H8_*` deferred vocab to S8 |
| 8 Valuation | Expectations, IV range, MoS evidence, uncertainty | Same; NON-TERMINATING; never BUY/SELL; `S8_H9_*` |
| 9 External risk | Industry/moat stress/disruption/concentration/reg/geo/macro | Same; `S9_HFA_*` carries to Final FA |
| **Final FA** | Reconciliation → final_state + technical_eligible | Outside-color + RED/ORANGE/GREEN |

---

## 6. Registry architecture (DONE / UAT_ACCEPTED)

**Canonical:** `COMPANY_FA_HISTORY_REGISTRY_PLAN_v1.md` §0 (Plan wins).

| Lock | Detail |
|------|--------|
| Analytical truth | Stage / Final FA **artifact files** on disk |
| Registry | Indexed metadata + paths + scalars + hashes — **never** full JSON duplicate |
| Primary SoR | `fa_data/registry/fa_run_registry.sqlite` |
| History | Append-only rows; CURRENT = flag/pointer flip |
| Conflict | Artifact file wins; repair registry from disk scan |
| Hooks | Thin post-write hooks after successful artifact write |
| VIEW | Regenerable `company_stage_matrix.csv` (+ optional `.md`); SQL client browse |
| Sheets | C (none) in v1; never Sheets-as-SoR |
| Budget | $0 incremental storage |

Module: `fa/registry/` (`schema`, `writers`, `hooks`, `backfill`, `drift`, `backup`, `views_export`, `db`).

---

## 7. Final FA placement

Final FA **consumes** Stages 1–9 CURRENT + carries; does **not** rewrite stage CURRENT.  
Stage 8 ⊥ Stage 9 ⊥ Final FA preserved.  
Stops before watchlist / TA / portfolio / Audit.

Artifacts (Plan): `Thesis/final_fa_CURRENT.{json,md}` + `final_fa_versions/`.

---

## 8. Budget & attention (LOCKED)

- AI/API/system ~USD **25–30/mo**; Dragonomi + Emtia subscriptions **outside**.  
- ~10 h/week human attention target.  
- ACTIVE WATCHLIST cap **15**; GREEN uncapped.
