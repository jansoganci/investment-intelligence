# FA Backend + Stage 2 — Implementation Status v1

**Date:** 2026-09-14  
**Scope:** Fundamental Analysis financial backend + Stage 2 Balance Sheet (Operating only)  
**Out of scope (deferred / forbidden in this pass):** FI contract, Stage 3+, RED/ORANGE/GREEN, numeric investment thresholds, live prices, paid feeds

---

## Naming note — Research Coverage ≠ FA List

| List | Role | Location |
|------|------|----------|
| **Fundamental Analysis List** | Gate for `analyze_company` — refuse if not listed | `FA_ROOT/data/fundamental_analysis_list.json` (production starts empty); fixture: `fa_fixtures/demo_fa_list.json` |
| **Research Coverage / tracked_companies** | RI concept — event/research coverage | Lives under **RI / 01_Research** (`tracked_companies.json`). **Do not merge** with FA List. |
| Stub | `FA_ROOT/data/research_coverage_list.json` | Empty stub pointing to RI — does not break RI |

---

## CURRENT.json semantics (chosen)

**Pointer (simplest):**

```json
{"version_id": "v001", "path": "v001.json"}
```

Full accepted document lives in `vNNN.json`. Reconstruct by reading the pointed file. Index tracks history / superseded links.

---

## Data roots

| Path | Role |
|------|------|
| `FA_ROOT` env (default `/workspace/investment_intelligence/fa_data/`) | Local cache / workspace store |
| Conceptual Drive `03_Fundamental/companies/` | Canonical storage intent (Drive sync later — not required for dry-run) |

---

## Implemented

- [x] Package layout under `fa/` + `stage2/`
- [x] FA List load/check; refuse analyze if not listed
- [x] Company folder layout (Source / Normalized / Generated / Thesis)
- [x] Immutable versioning (`vNNN`, CURRENT pointer, index history, supersedes)
- [x] Idempotent Source ingest (SEC accession / IR sha256+name+date) — cases A–F
- [x] Operating contract + Stage 2 nullable extensions
- [x] Field lineage helpers
- [x] Lightweight SEC client (User-Agent, ticker→CIK, submissions, companyfacts, cache) — offline/fixture mode
- [x] Best-effort companyfacts→contract mapping; ambiguity → REVIEW / uncertain (no silent guess)
- [x] Stage 2 deterministic calc (null+reason)
- [x] Stage 2 semantic structured placeholder (fixture-fillable; no LLM required in dry-run)
- [x] Stage 2 evaluate (question spine M1–M10 / S1–S5) → process outcomes
- [x] ADHD markdown report renderer
- [x] `analyze_company` pipeline with blocking (no Stage 3 call exists)
- [x] Synthetic fixtures (`SYNTH_OPCO`) + pytest suite

### Process outcomes

`PROCEED` | `CONDITIONAL` | `REVIEW_REQUIRED` | `TOO_HARD` | `BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY`

**Blocking (process-level only):** missing critical evidence; wrong Gate 0; unresolved major conflict; explicit going-concern / severe solvency language; credible near-term liquidity failure from semantic+evidence.  
**Not blocking:** high debt ratio alone; any numeric investment threshold.

---

## SEC — what’s real vs stub

| Capability | Status |
|------------|--------|
| User-Agent header | Real string set |
| `resolve_cik` / `get_submissions` / `get_companyfacts` | Implemented; network optional |
| Cache under `FA_ROOT/cache/sec/` | Implemented |
| Offline / `FA_OFFLINE=1` | Uses fixture stubs for `SYNTH_OPCO` CIK `0009999991` |
| Live SEC pulls | Possible when `FA_OFFLINE=0` and network available — not required for dry-run |
| companyfacts mapping | Heuristic; uncertain fields marked |

---

## Human review escalation

| Trigger | Behavior |
|---------|----------|
| Ticker not on FA List | Refuse — no ingest |
| Gate 0 ≠ operating | `TOO_HARD` / block Stage 3+ |
| Ambiguous XBRL tags | Field `uncertain` + REVIEW note; do not treat as final |
| Amendment / restatement / mapping correction | New `vNNN`; prior immutable |
| Going-concern / severe solvency / credible liquidity failure (semantic) | `BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY` |
| Incomplete MUST spine | `REVIEW_REQUIRED` or `CONDITIONAL` with monitors |
| Accepted Normalized | Human `accept=True` path; drafts stay pending |

---

## Deferred

- Stage 3+ income / earnings quality / moat / etc.
- FI / Commodity data contracts
- Live market price / mkt cap / EV (Stage 8)
- Paid data feeds
- LLM semantic call (placeholder + fixture only in v1 dry-run)
- Drive sync automation
- DERA / institutional PIT warehouse
- Rulebook numeric thresholds / color scoring
- DEF 14A Stage 7 deep dive (not required for Stage 2)

---

## Tests

```bash
cd /workspace/investment_intelligence && python -m pytest tests/fa -q
```

Dry-run report: `analyze_company("SYNTH_OPCO", ...)` or `fa.pipeline.dry_run_synth_opco()`.

## D — Stage 2 UAT — ACCEPTED (2026-09-14)

- **Ticker:** KO — FY2025/FY2024 Normalized **v002** (accepted)
- **Process outcome:** PROCEED · block_next=False · enough=Yes
- **Artifacts:** `fa_data/companies/KO/Generated/stage2_report.md`, `fa_data/uat/KO_stage2_uat_report_v1.md`, semantic `Source/notes/semantic_review.json`
- **User:** Stage 2 UAT accepted for KO
- **Stage 3:** not started

## D — Stage 2 UAT — ACCEPTED (near-term fix v2) — 2026-09-14

- **Ticker:** KO — Normalized FY2025/FY2024 **v003** (accepted; `short_term_debt_includes_current_ltd=false`)
- **Near-term:** $3,694M (ST $1,551M + CPLTD $1,822M + current leases $321M)
- **Process outcome:** PROCEED · block_next=False
- **Tests:** 43 passed (`tests/fa`)
- **Pack:** `fa_data/uat/KO_stage2_uat_report_v2.md`
- **User:** Stage 2 UAT accepted for KO (near-term fix v2)
- **Stage 3:** not started


## Stage 4 (2026-09-20)

**TESTED** — `fa/stage4/` + `fa/history_coverage.py` + `fa/quarter_derivation.py` (contiguous ~8Q; derived fiscal Q4 flows) + share mapping. KO UAT **v2** pending human (`KO_stage4_uat_report_v2.md`; v1 SUPERSEDED). Dry KO → **KO_RERUN_REQUIRED** (not run). pytest **158**. Not UAT_ACCEPTED/DONE. No Stage 5.


## Stage 8 (2026-09-29, Europe/Istanbul)

**DONE / UAT_ACCEPTED** — `fa/stage8/` (VA1–VA8; FCFF + dual-terminal CROSS-CHECKS; reverse DCF; session-aware freshness; A7 dual exhibits; MoS no universal %; NON-TERMINATING). pytest **269**. ROP Stage 8 UAT v1 **ACCEPTED** (`ROP_stage8_uat_accepted_v1.md`). NVDA Stage 8 UAT v1 **ACCEPTED** (`NVDA_stage8_uat_accepted_v1.md`). Component accept: `STAGE8_component_uat_accepted.md`. Blocking generics closed: CapEx-proxy≠FCFF; opacity≠incoherent; reverse-DCF ceiling provenance; EXIT_FCFF_MULTIPLE; VA3/VA7 regime-mismatch MIXED (no price-tuning). Remaining = non-blocking limitations. Stage 9 = **PLANNED**, not started. Stages 1–7 production modules preserved. No BUY/SELL/scores/colors/universal valuation gates. Independent `run_stage8` — not wired into `analyze_company`.

---

## Stage 9 (additive — 2026-09-29)

- Package: `fa/stage9/` — `run_stage9` independent (not in `analyze_company`).
- Lifecycle: **TESTED / UAT_IN_PROGRESS** (Visa UAT pending human accept; RIO not run; not DONE).
- Outcomes: `PROCEED` | `CONDITIONAL` | `REVIEW_REQUIRED` | `TOO_HARD` — NON-TERMINATING.
- Forbidden in Stage 9: BUY/SELL, scores/colors, numeric risk gates, averaged external-risk score, industry warehouse, final FA synthesis, S5 pricing-power redo, S1 thesis restatement, giant ER8 register.
