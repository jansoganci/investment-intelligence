# Changelog


---

## 2026-10-02 — POST-REMEDIATION FULL REVALIDATION (evidence freeze)

- **Component:** Final System Audit / Checkpoint C evidence
- **Event:** POST-REMEDIATION FULL REVALIDATION executed (NOT Wave 5; NOT Audit PASS/FAIL; NOT A1 close)
- **When (Europe/Istanbul):** 2026-10-02 15:42 +0300
- **Summary:** Isolated E2E DE/INTU/COST/DHR/AZO under \`investment_intelligence/audit/post_remediation_full_revalidation_2026-10-02/\`. Pytest \`tests/fa\` **417 passed / 1 skipped**. Stage 8 Yahoo E2E **YES×5** (Stooq SSL OPEN / SINGLE_SOURCE). Waves 1–4 resolved items largely VERIFIED_RESOLVED; A1 remains PARTIAL/OPEN. Proposed: **PARTIAL**; Checkpoint C: **READY_FOR_USER_DECISION**.
- **Evidence:** \`audit/post_remediation_full_revalidation_2026-10-02/MASTER_REPORT.md\`; Drive mirror \`00_System/handoff_pack/post_remediation_full_revalidation_2026-10-02/\`
- **Non-actions:** no FA code edits; no Wave 5; no Stooq fix; no production CURRENT mass rewrite; no frozen Phase 0–7 mutation; no overall audit PASS/FAIL.

## 2026-10-02 (Europe/Istanbul) — Wave 4 UAT ACCEPTED → DONE / UAT_ACCEPTED

- User **Can Soganci ACCEPTED** Wave 4. B4, C1, C2, and C3 are recorded as **RESOLVED** (formerly `RESOLVED_CANDIDATE`); A1 remains **PARTIAL/OPEN**.
- Wave 4 UAT is **UAT_ACCEPTED / DONE**. WAVE4 deliverable and UAT report status lines updated; all audit/retest evidence preserved.
- **Status/docs updates only** for this acceptance record; no code logic changes, no new wave, and no Wave 5.
- Overall audit **PASS/FAIL remains undeclared**; Checkpoint C remains open; Stooq SSL and other explicitly catalogued audit items remain open as documented.


## 2026-10-02 — Wave 4 C1 semantic harvest fix (targeted wave 4)

- **C1 only** — harvest/retrieval gap: Stage4 `_KEYWORD_MAP` lacked perimeter topics → empty `semantic_text_blob` on real 10-K spin/disc-ops text (Path A miss; Path B evaluate wiring already correct).
- Fix: add general `comparability_perimeter` topic + patterns (discontinued/continuing ops, spin-off/separation, etc.) in `fa/stage4/semantic.py`. No ticker hardcodes. No synthesize/recast. Dual-series SPEC preserved.
- Validate: real DHR FY2023 10-K → perimeter finding → blob cue → FY2022→FY2023 `COMPARABILITY_BREAK`; as-reported preserved; companion absent; provenance honesty_flag set.
- No B4/C2/C3 reopen. **STOP** after validation — not UAT_ACCEPTED.

## 2026-10-02 — Wave 4 IMPLEMENTED / TESTED (B4 / C3 / C2 / C1)

- Authorized **WAVE 4 SPEC LOCK + IMPLEMENTATION + REGRESSION + UAT**. Wave 3 ACCEPTED/CLOSED. No Wave 5. No W1–W3 reopen. No A1 fix. No Market Price/Stooq. No historical S8 freshness. No production CURRENT/Registry mass regen. No ticker hardcodes. No auto-close findings. No overall audit PASS/FAIL.
- **SPEC:** `WAVE4_SPEC_DECISIONS_B4_C1_C2_C3_v1.md` (SD-W4-B4 disruption wording; SD-W4-C1 dual-series; SD-W4-C2 duration; SD-W4-C3 growth basis). Thin cites Stage 9/4/2/6 Plan §0 + Data Architecture.
- Prefreeze → implement order **B4 → C3 → C2 → C1**.
- **B4** `fa/stage9/evaluate.py`: archetype/evidence-conditioned disruption wording (no universal fintech template).
- **C3** `fa/stage2/calc.py`+`evaluate.py`: `revenue_growth_qoq` + explicit basis; `revenue_growth_yoy` companion; no new S2 gate.
- **C2** `fa/stage4/calc.py`+`map_companyfacts.py`: persist/expose `duration_days`; unequal-duration YoY flag; no 53→52 normalize; no week-adjusted synthetics.
- **C1** `fa/comparability.py` + Stage 4/6: as-reported preserved; COMPARABILITY_BREAK; disclosed companion only; no model recast.
- Tests: `tests/fa/test_wave4_dual_series_duration.py` (12). Full `tests/fa`: **416 passed** / 1 skipped.
- Isolated held-out: `audit/retests/wave4_dual_series_duration_v1/` + `W4_REGRESSION_MATRIX.md` + UAT pack.
- Proposed: B4/C3/C2/C1 **RESOLVED_CANDIDATE**; A1 **PARTIAL/OPEN**. UAT propose **UAT_ACCEPT_CANDIDATE**. **STOP** — await user acceptance.


## 2026-10-02 — Wave 3 IMPLEMENTED / TESTED (A7 / B3 / B1 / B2)

- Authorized **WAVE 3 SPEC LOCK + IMPLEMENTATION**. No Wave 4. No W1/W2 reopen. No Stage 8 Market Price changes. No A1 debt fix. No production CURRENT/Registry mass regen. No ticker hardcodes. No auto-close findings. No overall audit PASS/FAIL.
- **SPEC:** `WAVE3_SPEC_DECISIONS_ER5_ER8_v1.md` (SD-W3-ER5 multi-issue named legal facts; SD-W3-ER8 thesis-linked ER8 promotion). Thin cite Stage 9 Plan §0 + Decision Pass.
- **A7** `fa/stage8/normalization.py`: OE = median of per-year (OCF−CapEx); period keys lineage; no silent cross-year mix.
- **B3** `fa/stage8/market_data.py` + `evaluate.py`: general post-period detector; CS statement-date preserved; empty events ≠ proven none.
- **B1** Stage 5/6 semantic: bare PPA requires purchase-accounting context; Precision Agriculture (PPA) excluded.
- **B2** Stage 9 semantic/evaluate: multi-hit ER5; surface all material named legal facts; ER8 promote only with thesis/moat/ops link; ambiguous → no auto-promote + REVIEW/HITL exception path.
- Tests: `tests/fa/test_wave3_external_coherence.py`. Full `tests/fa`: **404 passed** / 1 skipped.
- Isolated held-out: `audit/retests/wave3_external_coherence_v1/` + `W3_REGRESSION_MATRIX.md` (same 2026-09-30 RAW closes).
- Proposed: A7/B3/B1/B2 **RESOLVED_CANDIDATE**; A1 **PARTIAL/OPEN**. **STOP** — await user acceptance.


## 2026-10-02 — Wave 2 SEAL (A4 Stage 6 thin cite + S8+Final replay)

- Stage 6 Decision Pass D4 + Plan §0.D: **thin cite** of SPEC_LOCKED **SD-W2-A4** (client/customer restricted funds); rule text not redesigned — cites `WAVE2_SPEC_DECISIONS_A1_A4_v1.md`.
- Findings register: user-accepted Wave 2 statuses documented (A1 **PARTIAL/OPEN**; A3/A4 STI/A4 client funds/A5/A6 **RESOLVED_CANDIDATE**). A1 not closed.
- Isolated post-W2 Stage 8 + Final FA replay: `investment_intelligence/audit/retests/wave2_seal_s8_final_v1/` (copy-by-value fa_root; frozen 2026-09-30 RAW closes; compare vs `stage8_price_injection_2026-09-30_close_v1`).
- **STOP.** Do not start Wave 3. No overall audit PASS/FAIL.

## 2026-10-02 — Wave 2 XBRL/mapping IMPLEMENTED / TESTED (A1/A3/A4/A5/A6)

- Authorized **WAVE 2 ONLY**: core XBRL/mapping + locked A1/A4 SPEC. No Wave 3/4. No Plan §0 edits. No Market Price. No W1 revert. No mass CURRENT/Registry rewrite. No ticker hardcodes. No invented payables.
- **TAG_MAP** (`fa/map_companyfacts.py`): `secured_debt` (SecuredDebt); cash combined+restricted (DHR); AFS STI current (INTU); `InventoryFinishedGoodsNetOfReserves` (AZO); `ReceivablesNetCurrent` (COST); `funds_held_for_clients` + `client_funds_business` pattern.
- **Stage 2**: include secured in gross_debt; `gross_debt_incomplete` / `opco_fs_split_unavailable` when LTD null with evidence; REVIEW_REQUIRED rather than understated complete debt / invented OpCo split.
- **Stage 6**: exclude client restricted funds from IC; missing cash blocks IC (≠0); `client_funds_incomplete` / `nibol_incomplete` without inventing payable; WC null≠0 → `wc_incomplete` refuse coerced proxy.
- Tests: `tests/fa/test_wave2_mapping.py`. Full `tests/fa`: **388 passed** / 1 skipped.
- Isolated held-out: `audit/retests/wave2_mapping_v1/` + `W2_REGRESSION_MATRIX.md`.
- Proposed: A3/A4-p1/A4-p2/A5/A6 **RESOLVED_CANDIDATE**; A1 **PARTIAL**. Findings **not** auto-closed. STOP — await user acceptance before Wave 3.

## 2026-10-02 — Wave 2 SPEC lock: A1 debt perimeter + A4 client funds

- Locked `WAVE2_SPEC_DECISIONS_A1_A4_v1.md`: consolidated labeled debt / dual exhibits; exclude client restricted funds from IC + honesty flag (no invented payable).
- **Not** Wave 2 implementation. Awaiting separate auth.


## 2026-10-02 — Wave 1 period normalization IMPLEMENTED / TESTED (F-S3-CUM-01 + A2)

- Authorized **WAVE 1 ONLY**: F-S3-CUM-01 + A2 (F-DERIVE-YTD-Q4-01). No Wave 2/3/4. No Plan §0 edits. No Market Price changes. No mass CURRENT/Registry rewrite.
- **W1.1** `fa/stage3/calc.py`: multi-year `cumulative_*` now **FY-only non-overlapping** (`cumulative_basis=FY_only_non_overlapping`); interim/YTD remain in series for trend/latest.
- **W1.2** `fa/quarter_derivation.py`: YTD vs discrete via start/end duration + arithmetic; `Q2d=Q2YTD−Q1YTD`, `Q3d=Q3YTD−Q2YTD`, `Q4d=FY−Q3YTD`; never `FY−(Q1+Q2YTD+Q3YTD)`; ambiguous → MAPPING_AMBIGUOUS; negative CapEx/outflow Q4 after YTD conversion blocked; **no ticker hardcodes**.
- **Map emitter** `fa/map_companyfacts.py`: persist `period_start`/`period_end`; annotate `flow_basis` / `duration_days` on duration CF fields (fiscal label ≠ discrete).
- Tests: `tests/fa/test_wave1_period_normalization.py` + existing Stage3/Q-derivation updated. Full `tests/fa`: **373 passed** / 1 skipped (known S8 freshness not reproducing; not fixed).
- Isolated held-out post-fix: `audit/retests/wave1_period_normalization_v1/` (pre_fix freeze + post_fix copy-by-value DE/INTU/COST/DHR/AZO). Matrix: `W1_REGRESSION_MATRIX.md`.
- Proposed status: **F-S3-CUM-01 = RESOLVED_CANDIDATE**; **A2/F-DERIVE-YTD-Q4-01 = RESOLVED_CANDIDATE**. Findings **not** auto-closed. STOP — await user acceptance before Wave 2.

## 2026-10-02 — Stage 8 Market Price v1 IMPLEMENTED / TESTED (not DONE/UAT)

- Authorized **SPEC_LOCKED Stage 8 Market Price v1 ONLY** implementation.
- Added `fa/market_price/` (Protocol, YahooAdapter, StooqAdapter, `resolve_market_price`, disk cache, `resolve_and_run_stage8` harness).
- Contract: RAW US regular-session close; Yahoo primary + Stooq secondary; cache by ticker+session_date; 1 retry/source; SINGLE_SOURCE; conflict `max($0.02, 0.05% primary)` → PRICE_SOURCE_CONFLICT suppresses usable price; PRICE_UNAVAILABLE → existing missing-price path; persist MP-D6 fields.
- Providers remain **outside** `fa/stage8` analytical modules (no yfinance/Stooq imports there). Explicit `market_price` injection still wins over fetch.
- Tests: `tests/fa/test_market_price_v1.py` → **15 passed**, 1 network skipped. Full `tests/fa` → **361 passed** / 1 skipped; 3 known S8 freshness fails **not reproducing** at this wall-clock (recorded, not fixed).
- Isolated adapter retest: `audit/retests/stage8_market_price_adapter_v1/` — Yahoo live probe OK; Stooq live SSL fail → fixture CSV (labeled); all 5 MATCHED / CURRENT / REVIEW_REQUIRED; Final FA matches prior price-injection pattern.
- **Not** DONE / **not** UAT_ACCEPTED. Valuation formulas untouched. Plan/Decision Pass untouched. A1–A7/B1–B4/C1–C3 untouched. STOP.

## 2026-10-02 — Stage 8 Market Price v1 SPEC_LOCKED (contract only)

- Locked Plan §0.T + companion `03_Fundamental/STAGE_8_MARKET_PRICE_DECISION_PASS_v1.md`.
- RAW regular-session close; latest completed US session; Yahoo (`yfinance`) primary + Stooq secondary; USD; cache ticker+session_date; retry/fallback/conflict threshold; persist fields; adapters replaceable without reopening Stage 8 analytical logic.
- **Not implemented.** No FA code mutation. Audit findings unchanged. No overall PASS/FAIL.


## 2026-10-02 — Isolated Stage 8 price-injection retest (observation)

- Authorized **ISOLATED** Stage 8 retest only: `audit/retests/stage8_price_injection_2026-09-30_close_v1/`.
- Injected fixed 2026-09-30 regular-close prices (DE/INTU/COST/DHR/AZO); `ensure_history=False`; Phase 2 freezes unchanged.
- Result: all five `UNKNOWN/TOO_HARD` → `CURRENT/REVIEW_REQUIRED`; Final FA left uniform `TOO_HARD` (DE/AZO GREEN; INTU/COST/DHR ORANGE).
- **F-S8-PRICE-01 CONFIRMED** empirically; DHR IV/EV still blocked by frozen cash=null (upstream).
- **No** FA code/fix/spec/mapping fixes; **no** finding closures; **no** overall PASS/FAIL.

## 2026-10-02 — Claude cross-check read-only root-cause (A1–A7, B1–B4, C1–C3)

- Independent Claude Phase 4 findings investigated **read-only** against Plan §0 + freeze evidence.
- Wrote `audit/findings/ROOT_CAUSE_CLAUDE_BATCH_A.md`, `ROOT_CAUSE_CLAUDE_BATCH_BC.md`, `ROOT_CAUSE_CLAUDE_CROSSCHECK.md`.
- Appended findings F-MAP-DE-DEBT-01 … F-S2-REVGROWTH-BASIS-01 to `audit/findings/findings_register.md` (26 rows).
- **No** FA code/tests/specs/prompts/mappings mutation; **no** held-out re-run; Phase 2 freezes preserved; Stage 8 retest **not** authorized; no overall PASS/FAIL.
- Skipped re-open of F-S3-CUM-01, F-S8-PRICE-01, DE S2 CONDITIONAL→PROCEED (already diagnosed).


## 2026-10-01 — Final System Audit findings A/B registered (Claude cross-check pending)

- Registered **F-S3-CUM-01** (**IMPLEMENTATION DEFECT**) and **F-S8-PRICE-01** (**TEST EXECUTION GAP**) from `audit/findings/ROOT_CAUSE_A_B.md`.
- Updated both findings registers and evidence indexes; F-HOLD-01 remains **OBSERVATION** and is now explained by F-S8-PRICE-01.
- **No** code fix, company re-run, Phase 2 held-out artifact mutation, or Stage 8 retest authorization; waiting independent Claude cross-check.

## 2026-10-01 — Final System Audit Phase 4 handoff pack ready (ChatGPT; not executed in Grok)

- Prepared **Phase 4 Independent Review** handoff for ChatGPT Project (judge mode only; **no** Phase 4 execution here).
- Wrote `audit/findings/phase4_handoff/`: `00_PHASE4_KICKOFF.md`, `01_EVIDENCE_MANIFEST.md`, `02_REVIEW_CHECKLIST.md`, `03_CHAT_PROMPT.md`, `PHASE4_HANDOFF_FOR_CHATGPT.md`.
- Mirrored pack to production + audit clone `audit/findings/phase4_handoff/`.
- Evidence phases **0–3** and **5–7** remain COMPLETE; all five held-out Final FA = `TOO_HARD` (S8 unevaluable) still **OBSERVATION** pending Phase 4.
- Critical reminder **F-REG-D1**: H1 DE prefer production `audit/heldout/H1_DE` and/or `*_v001.*` (clone CURRENT hardlink-mutated).
- **No** FA logic mutation; `fa/` list digest still `6d6ebbc8…fe60`. **No** overall audit PASS/FAIL.
- Uploaded handoff markdowns to Drive folder `Grok.bot.trade` / `Invetment Intelligence`.
- **Continue:** ChatGPT Phase 4 → Checkpoint C (user). 

## 2026-10-01 — Final System Audit findings register compiled (Checkpoint C pending)

- Evidence collection phases **0–3** and **5–7** marked **COMPLETE** (compile from existing evidence only; **no** company re-runs; **no** FA logic mutation).
- Wrote `audit/findings/findings_register.md` + `AUDIT_EVIDENCE_INDEX.md` on audit clone; mirrored to production `audit/findings/`.
- Held-out set **DE / INTU / COST / DHR / AZO**: all five Final FA → `TOO_HARD` (S8 unevaluable) catalogued as **OBSERVATION** pending independent review — **not** auto company PASS/FAIL.
- Registry rerun append-only checks **PASS**; D1 clone hardlink CURRENT mutation = **TEST_INVALIDATED** risk (use v001 / production mirror); D3 Stage2 CONDITIONAL→PROCEED = **OBSERVATION**.
- Contract probes P1–P5 property **PASS**; static numeric-gate presence = **OBSERVATION** (pending Plan §0 mapping).
- UAT regression: KO/ROP/V **MATCH**; NVDA S8 **DRIFT** = known freshness **NON_BLOCKING** (catalogued). Baseline pytest **343/3** known S8 still catalogued.
- **Checkpoint C** pending user review. **Phase 4** independent arithmetic/provenance deep review still **outstanding** unless user waives.
- `fa/` digest still matches baseline `6d6ebbc8…fe60`. **No overall audit PASS/FAIL declared.**

## 2026-10-01 — Final System Audit Phase 1 (Prompt 0) baseline freeze COMPLETE

- Isolated audit clone: `/workspace/investment_intelligence_audit_clone/` (tar copy; `.pytest_cache` excluded; no project-local `.venv` — tests use `/workspace/.venv`).
- Live SoR remains `/workspace/investment_intelligence`; later held-out writes **only** in clone.
- Baseline evidence: `audit/baseline/` (clone + mirrored to production `audit/baseline/`). Manifest: `AUDIT_BASELINE_MANIFEST.md` / `.json`.
- **NO_GIT** — tree/file SHA-256 fingerprints recorded (`fa/` 234 files; `tests/fa/` 96; `fa_data/` 706).
- Registry DB SHA-256: `393a5f6efb7f296bdb01abb089c45758ce8387d100991f9a26094c3aaac872e8`.
- Pytest from clone: `tests/fa` → **343 passed / 3 failed** (known Stage 8 freshness/date failures **recorded, not fixed**); inventory in `pytest_inventory.txt`.
- Held-out set frozen: **DE / INTU / COST / DHR / AZO** — **no company FA analysis**; none present under `fa_data/companies/`.
- Confirmations: `fa/` hashes identical pre/post pytest; production analytical code untouched; production `fa_data` unchanged except `audit/baseline/` mirror docs.
- Phase 1 status **COMPLETE**; stop awaiting **Human Check #2**.


## 2026-10-01 — Final System Audit AUTHORIZED (Phase 0 started)

- User **AUTHORIZED** Independent Cross-Validation / Final System Audit execution (design: 9-phase black-box plan exceeding handoff `06`).
- Mode: evidence collection; **no** FA analytical logic mutation; **no** silent Stage 8 freshness fixes; live SoR preserved via audit clone (Phase 1).
- Phase 0 in progress: contamination scan on DE / ADBE / COST / DHR / AZO with precommitted substitutes CAT / INTU / WMT / TMO / ORLY; freeze held-out set before any company run.
- Stages 1–9 + Final FA + Registry remain **DONE / UAT_ACCEPTED** (not reopened).
- Next: Human check #1 on frozen held-out set → Phase 1 Prompt 0 baseline freeze.

## 2026-10-01 — Final FA Synthesis UAT ACCEPTED → DONE / UAT_ACCEPTED

- User **ACCEPTED** Final FA Synthesis UAT v2 (Can Soganci): ROP Final FA UAT = ACCEPTED; Visa (V) Final FA UAT = ACCEPTED; Final FA Synthesis component UAT = ACCEPTED.
- Lifecycle → **DONE / UAT_ACCEPTED**. No open blocking Final FA defect (v2 COMPLETE; §0.O stresses PASS).
- Accept artifacts: `fa_data/uat/ROP_final_fa_uat_accepted_v2.md`, `V_final_fa_uat_accepted_v2.md`, `FINAL_FA_component_uat_accepted.md`. v1+v2 reports preserved; Final FA versions + registry history preserved (no delete/rewrite).
- Registry CURRENT Final FA rows (`ff_1bbde40e7cb7` ROP v002; `ff_411b830f7a28` V v002) → `uat_status=accepted` via `set_uat_status` (v001 history untouched).
- Pytest at closure: final_fa **20 passed**; full `tests/fa` **343 passed / 3 known Stage 8 freshness fails** (non-blocking; unchanged; not fixed).
- Stages 1–9 analytical logic untouched. Registry stays DONE. No TA / watchlist / portfolio / Final System Audit.
- Next planned step: **Final System Audit**.


## 2026-10-01 — Final FA UAT UNBLOCK regeneration (ROP+V; still UAT_IN_PROGRESS)

- User authorized regenerate missing required CURRENT then re-UAT Final FA for **ROP + V** only.
- Regenerated (accepted Stage engines; versioned writes; history preserved; methodology unchanged):
  - **ROP:** S1 PROCEED, S2 PROCEED, S3 REVIEW_REQUIRED, S9 REVIEW_REQUIRED (v001 each).
  - **V:** S1 PROCEED, S2 PROCEED, S3 CONDITIONAL, S8 CONDITIONAL (v001 each; S8 market_price 358.64 USD yahoo 2026-10-01T16:13:21Z).
- Completeness: both **COMPLETE** (S1 PROCEED + S2/S3/S6/S8/S9 CURRENT). Soft-missing OK: ROP S5; V S4/S7.
- Re-ran `run_final_fa` → **ROP ORANGE** v002; **V REVIEW_REQUIRED** v002 (FACT breaker, not auto-RED). Registry Final FA rows `uat_in_progress`; prior v001 demoted.
- UAT packs: `fa_data/uat/ROP_final_fa_uat_report_v2.md`, `fa_data/uat/V_final_fa_uat_report_v2.md` (PENDING_HUMAN_REVIEW). v1 preserved.
- §0.O stresses: ROP soft RR→ORANGE **PASS**; V FACT→REVIEW **PASS**. Missing≠RED still holds on soft chips.
- Lifecycle = **TESTED / UAT_IN_PROGRESS**. **NOT DONE / NOT UAT_ACCEPTED**. Recommendation: **FINAL_FA_UAT_ACCEPT_RECOMMENDED**.
- Pytest: final_fa 20 passed; full `tests/fa` 343 passed / 3 known Stage 8 freshness fails (not fixed).
- Stages 1–9 analytical logic untouched. Registry stays DONE.


## 2026-10-01 — Final FA Synthesis UAT_IN_PROGRESS (ROP+V; not DONE / UAT_ACCEPTED)

- User authorized FINAL FA SYNTHESIS **UAT** for **ROP + V** only (Plan §0.O).
- Ran `run_final_fa` on production fa_data using existing Stage CURRENT only (no Stages 1–9 re-run / redesign).
- Outcomes: ROP + V → **`INCOMPLETE`** / `technical_eligible=False` (required CURRENT missing). Artifacts `Thesis/final_fa_CURRENT.{json,md}` v001 + versions; registry Final FA rows `uat_in_progress`.
- UAT packs: `fa_data/uat/ROP_final_fa_uat_report_v1.md`, `fa_data/uat/V_final_fa_uat_report_v1.md` (PENDING_HUMAN_REVIEW).
- Contract highlights: Missing≠RED PASS; no BUY/SELL/weights; soft-missing chips + orange_ceiling; technical_eligible False; registry hook PASS. §0.O color-path stresses **BLOCKED** (ROP missing S1/S2/S3/S9; V missing S1/S2/S3/S8) — FACT→REVIEW / soft-chain color not fully exercised.
- Lifecycle = **TESTED / UAT_IN_PROGRESS**. **NOT DONE / NOT UAT_ACCEPTED**. Recommendation: **FINAL_FA_UAT_FIX_REQUIRED** (artifact completeness).
- Pytest: final_fa 20 passed; full `tests/fa` 343 passed / 3 known Stage 8 freshness fails (not fixed).
- Stages 1–9 analytical logic untouched. Registry stays DONE.

## 2026-10-01 — Final FA Synthesis IMPLEMENTED / TESTED (not DONE / UAT)

- User authorized FINAL FA SYNTHESIS **IMPLEMENT** against SPEC_LOCKED Plan §0 (Plan wins; design frozen — no redesign).
- Lifecycle = **IMPLEMENTED / TESTED**. **NOT DONE / NOT UAT_ACCEPTED**. **Did not run ROP+V UAT.**
- Module: `fa/final_fa/` — `models.py`, `evaluate.py` (completeness → constraints → soft challenges → color/state), `report.py`, `pipeline.py` (`run_final_fa`), `storage.py` (CURRENT+versions + registry hook after artifact).
- Locked rules: outside INCOMPLETE|TOO_HARD|STOP_NO_THESIS|REVIEW_REQUIRED; inside RED|ORANGE|GREEN; U2 tighten soft-missing S4/S5/S7 → ORANGE max / no GREEN; FACT breaker → REVIEW; `technical_eligible` iff GREEN ∧ no open blocks_color; contradiction ≤5; human queue ≤5; consume carry IDs only; no BUY/SELL/scores/weights; Stages 1–9 untouched.
- Artifacts: `Thesis/final_fa_CURRENT.{json,md}` + `final_fa_versions/`.
- Tests: `tests/fa/test_final_fa.py` 20 passed; full `tests/fa` 343 passed / 3 known Stage 8 freshness fails (non-blocking, unrelated).
- Registry stays DONE. Plan banner → IMPLEMENTED/TESTED; §0 locked rules unchanged.

## 2026-10-01 — Company FA History Registry FINAL UAT + CLOSURE (DONE / UAT_ACCEPTED)

- User authorized COMPANY FA HISTORY REGISTRY **FINAL UAT + CLOSURE**.
- Registry UAT = **ACCEPTED**; lifecycle → **DONE / UAT_ACCEPTED**.
- Isolated tmp FA root UAT: SQLite tables/views; real `save_stage3_report` auto-hook; history/CURRENT demotion; idempotent same-version; uat_status distinguish; backfill+drift+matrix CSV+timestamped backup; Final FA stub hook (hand-written artifact; no synthesis). Prod KO/V packs untouched.
- Tests: registry+hooks 25 passed; full `tests/fa` 323 passed / 3 known Stage 8 freshness fails (non-blocking).
- Plan banner → DONE / UAT_ACCEPTED. Stages 1–9 analytical logic unchanged. Final FA synthesis still SPEC_LOCKED / NOT IMPLEMENTED.



## 2026-10-01 — Company FA History Registry automatic write hooks (IMPLEMENTED/TESTED; not DONE/UAT)

- Wired Plan §0.F post-artifact hooks: `fa/registry/hooks.py` (`hook_stage_after_save`, `hook_final_fa_after_artifact` / `register_final_fa_artifact`).
- Stages 1–9 `save_stageN_report` call hook AFTER version+CURRENT write; return shape unchanged `{version_id, path}`.
- Stage 2: added `fa/stage2/storage.py` (Thesis CURRENT+versions+Generated); `fa/pipeline.py` persist block uses `save_stage2_report` only (no evaluate/calc changes).
- Final FA: thin `fa/final_fa/storage.py` stub writes CURRENT+versions + hook — **no synthesis**.
- Failure: artifact SoR intact; registry txn rollback; kill-switch `FA_REGISTRY_HOOKS=0`; `register`/`skip_registry`/`uat_status` kwargs.
- Tests: `tests/fa/test_registry_hooks.py`; registry+hooks pass; full `tests/fa` ~323 pass / 3 known Stage 8 freshness fails (clock).
- Lifecycle remains **IMPLEMENTED / TESTED** — **NOT DONE / NOT UAT_ACCEPTED**.

## 2026-10-01 — Company FA History / Run Registry IMPLEMENTED / TESTED (not DONE / UAT)

- User authorized COMPANY FA HISTORY REGISTRY **IMPLEMENTATION** (SPEC_LOCKED design; Plan wins).
- Lifecycle = **IMPLEMENTED / TESTED**. **NOT DONE / NOT UAT_ACCEPTED**.
- Module: `fa/registry/` — schema DDL, append-only writers, CURRENT demotion, idempotent `(ticker, stage, version_id)`, post-artifact API, backfill, drift (file wins), backups, SQL views, CSV/MD matrix export.
- DB: `fa_data/registry/fa_run_registry.sqlite`; `.gitignore` live `.sqlite` + `backups/`.
- Backfill against existing `fa_data/companies` Thesis artifacts (idempotent). Stages 1–9 analytical logic **unchanged**. Final FA synthesis still **SPEC_LOCKED / NOT IMPLEMENTED**.
- Tests: `tests/fa/test_registry.py`; full `uv run pytest tests/fa -q`.
- Canonical Plan banner → IMPLEMENTED/TESTED; design freeze still Plan §0.


## 2026-09-29 — Company FA History / Run Registry SPEC_LOCKED (design freeze only — NOT IMPLEMENTED)

- User authorized COMPANY FA HISTORY / RUN REGISTRY **SPEC_LOCK** only (no impl; no Stages 1–9 / Final FA logic changes).
- Canonical: butterbear `00_System/COMPANY_FA_HISTORY_REGISTRY_PLAN_v1.md` §0 (**Plan wins**).
- U1–U14 LOCKED: SQLite `fa_data/registry/fa_run_registry.sqlite`; tables; CURRENT/history; write hooks contract; VIEW TablePlus/CSV/MD; Sheets C; JSONL fallback/mirror; backup/Git policy.
- Companions Decision Pass / Architecture banners point to Plan (bodies retained).
- Lifecycle = **SPEC_LOCKED** (design freeze only — **NOT IMPLEMENTED**).
- No registry module. No `fa_data/registry/` created. No FA code changes. No Final FA impl. No UAT.
- Note: Plan + Decision Pass + Architecture live under butterbear `00_System/`; II STATUS/CHANGELOG thin mirror only.


## 2026-09-29 — Company FA History / Run Registry Decision Pass authored (NOT SPEC_LOCKED; NOT IMPLEMENTED)

- User authorized DECISION PASS ONLY for Company FA History / Run Registry (STOP after Decision Pass; no SPEC_LOCK; no impl; Stages 1–9 / Final FA logic untouched).
- Created butterbear `00_System/COMPANY_FA_HISTORY_REGISTRY_DECISION_PASS_v1.md` (U1–U14 APPROVE_RECOMMENDED; **READY_FOR_SPEC_LOCK**).
- Lifecycle = **DECISION_PASS_COMPLETE / awaiting SPEC_LOCK**. **NOT SPEC_LOCKED**. **NOT IMPLEMENTED**.
- Primary: SQLite `fa_data/registry/fa_run_registry.sqlite` + VIEW; Sheets C; JSONL optional mirror; pointers/scalars only; immutable history + CURRENT; hooks contract post-artifact.
- No registry module. No `fa_data/registry/` created. No FA code changes. No Final FA impl. No UAT.
- Note: Decision Pass + Architecture live under butterbear `00_System/`; II STATUS/CHANGELOG thin mirror only.

## 2026-09-29 — Company FA History / Run Registry architecture research (NOT IMPLEMENTED; NOT SPEC_LOCKED)

- User authorized ARCHITECTURE / RESEARCH ONLY for persistent Company FA History / Run Registry (no impl; no SPEC_LOCK; Stages 1–9 / Final FA logic untouched).
- Created butterbear `00_System/COMPANY_FA_HISTORY_REGISTRY_ARCHITECTURE_v1.md`.
- Lifecycle = **DESIGN / RESEARCH** (recommendation written). **NOT IMPLEMENTED**. **NOT SPEC_LOCKED**.
- Primary recommend: local SQLite run registry + regenerable CSV/MD VIEW (Sheets C default). Fallback: JSONL + current_index.json. Pointers/scalars only; immutable history + CURRENT.
- No registry module. No FA code changes. No Final FA impl. No UAT.
- Note: architecture doc lives under butterbear `00_System/` (system/ops index); II STATUS/CHANGELOG thin mirror only.

## 2026-09-29 — Final FA Synthesis SPEC_LOCKED (design freeze only — NOT IMPLEMENTED)

- User authorized FINAL FA SYNTHESIS **SPEC_LOCK** only (no impl; no UAT; no TA/watchlist/portfolio/Audit; Stages 1–9 untouched).
- Canonical: butterbear `03_Fundamental/FINAL_FA_SYNTHESIS_PLAN_v1.md` §0 (**Plan wins**).
- U1–U12 LOCKED; **U2 tighten APPROVED** (required: S1 PROCEED + S2/S3/S6/S8/S9 CURRENT; missing → INCOMPLETE; required TOO_HARD → Final FA TOO_HARD; S4/S5/S7 soft-if-missing: color OK + chip; GREEN NOT allowed; ORANGE max).
- ORANGE lock definition frozen. Standing principles preserved. Companions Decision Pass / Pre-Spec / Research banners point to Plan (not deleted).
- Lifecycle = **SPEC_LOCKED** (design freeze only — **NOT IMPLEMENTED**).
- No Final FA code. No UAT. No Final System Audit. Stages 1–9 untouched.
- No BUY/SELL / scores / weights / watchlist ranking / portfolio / TA.


## 2026-09-29 — Final FA Synthesis PRE-SPEC verify (NOT SPEC_LOCKED)

- Pre-SPEC verification note: butterbear `03_Fundamental/FINAL_FA_SYNTHESIS_PRE_SPEC_VERIFY_v1.md`. Recommends U2 tighten (S4/S5/S7 soft-missing caps ORANGE); U3/U11 unchanged. Decision Pass/Research/Plan not overwritten. **NOT SPEC_LOCKED**. NOT_READY until U2 confirm.

## 2026-09-29 — Final FA Synthesis Decision Pass authored (NOT SPEC_LOCKED)

- Authorized Final FA Synthesis **DECISION PASS ONLY** (no SPEC_LOCK; no impl).
- Created butterbear `03_Fundamental/FINAL_FA_SYNTHESIS_DECISION_PASS_v1.md`.
- Lifecycle = **DECISION_PASS_COMPLETE / awaiting SPEC_LOCK**. **NOT SPEC_LOCKED**. **NOT IMPLEMENTED**.
- U1–U12 = `APPROVE_RECOMMENDED` (U3=Option C: `technical_eligible` iff GREEN ∧ no open blocking queue; ORANGE in color but never TA). Readiness `READY_FOR_FINAL_REVIEW`.
- Research + Plan **preserved** (not overwritten). No Final FA code. No UAT. No Final System Audit. Stages 1–9 untouched.
- No BUY/SELL / scores / weights / watchlist ranking / portfolio / TA.
- Note: Stage PLAN/RESEARCH/Decision Pass docs live under butterbear `03_Fundamental/` only (same as Stage 8/9).


## 2026-09-29 — Final FA Synthesis design/pre-analysis started (NOT SPEC_LOCKED)

- Authorized Final FA Synthesis **RESEARCH + ARCHITECTURE / DESIGN ONLY**.
- Created butterbear `03_Fundamental/FINAL_FA_SYNTHESIS_RESEARCH_v1.md` + `FINAL_FA_SYNTHESIS_PLAN_v1.md`.
- Lifecycle = **DESIGN / RESEARCH_IN_PROGRESS**. **NOT SPEC_LOCKED**. **NOT IMPLEMENTED**.
- No Final FA code. No Decision Pass. No UAT. No Final System Audit. Stages 1–9 untouched.
- Proposed: reconciliation (not averaging); outside-color INCOMPLETE/TOO_HARD/STOP_NO_THESIS/REVIEW_REQUIRED + colors RED/ORANGE/GREEN; hard vs soft; contradiction engine compact; human queue 0–5; technical handoff = GREEN eligibility; watchlist/audit excluded; UAT candidate **ROP + V**.
- Note: Stage PLAN/RESEARCH docs live under butterbear `03_Fundamental/` only (same as Stage 8/9); no II doc mirror required.


## 2026-09-29 — Stage 9 RIO ACCEPTED + component DONE / UAT_ACCEPTED

- User ACCEPTED **RIO Stage 9 UAT v1**; Visa Stage 9 UAT v1 **ACCEPTED** preserved.
- Recorded: Visa Stage 9 UAT v1 = ACCEPTED; RIO Stage 9 UAT v1 = ACCEPTED; Stage 9 component UAT = ACCEPTED.
- Accept artifacts: `fa_data/uat/RIO_stage9_uat_accepted_v1.md`, `fa_data/uat/STAGE9_component_uat_accepted.md` (RIO report lightly marked; Baowu/env + China≠geo + Visa primary-legal/HFA verification/fix history preserved).
- Closure checks: `uv run pytest tests/fa -q` → **301 passed**; no open blocking generic Stage 9 defect; UAT artifacts preserved; Visa accepted regression preserved; Stages 1–8 production modules untouched; **Final FA = PLANNED, not started**.
- Closed Stage 9 as **DONE / UAT_ACCEPTED**. Stages 1–9 DONE. No final FA synthesis.

## 2026-09-29 — Stage 9 RIO Baowu materiality + env/permitting pre-accept verify (UAT_IN_PROGRESS)

- Pre-accept verified RIO Stage 9 on **Baowu materiality** + **env/permitting ER5** only.
- **Generic defects fixed:** (1) largest-customer alone ≠ automatic material concentration — `excerpt_has_concentration_quant` gates escalate + customer=high; named-without-quant → monitor/uncertainty (not RR); (2) TB_CONCENTRATION requires material FACT on the high axes (no unrelated-axis fallback); (3) ER5 `environmental_permitting` topic (env reg / permitting / mine licences / remediation/closure / approvals) — research-depth fix, not ESG warehouse.
- Re-ran RIO → machine **CONDITIONAL** (v005); customer=**unknown**; TB_CONCENTRATION demoted to monitor; env findings under ER5; soft A8 retained; NON-TERMINATING. Counterfactual: Baowu not material → not RR.
- Visa regression **PASS** (RR; REGULATORY_MATERIAL + THESIS_BREAKER_ACTIVE; TB_REG_SWORD FACT active).
- Updated `RIO_stage9_uat_report_v1.md`. Pytest `tests/fa`: **301 passed**. Stage 9 remains **TESTED / UAT_IN_PROGRESS** — not UAT_ACCEPTED / not DONE. No final FA synthesis. Stages 1–8 preserved.

## 2026-09-29 — Stage 9 RIO pre-accept verify (UAT_IN_PROGRESS)

- Pre-accept verified RIO Stage 9 UAT vs user checks (China≠GEO_MATERIAL; TB_CONCENTRATION INFERENCE discipline; RR causality).
- **Generic defects fixed:** China demand/market/pathway ≠ geo substance; `S9_HFA_GEO_MATERIAL` requires geo mechanism **and** company footprint (Russia-Ukraine price-vol alone demoted); TB_CONCENTRATION INFERENCE-alone → monitor (FACT disclosure → inactive FACT breaker; never ACTIVE); RR why names exact FACT escalate path (soft A8/CLAIM/inactive GEO-CYCLE ≠ mechanical RR).
- Re-ran RIO + Visa Stage 9; updated `RIO_stage9_uat_report_v1.md` + Visa regression note in `V_stage9_uat_report_v1.md`.
- RIO machine **REVIEW_REQUIRED** from material concentration FACT (China Baowu); **no** `S9_HFA_GEO_MATERIAL`; TB_CONCENTRATION FACT/inactive; soft A8 LOW retained as packaging only; NON-TERMINATING.
- Visa regression **PASS** (RR; REGULATORY_MATERIAL + THESIS_BREAKER_ACTIVE; TB_REG_SWORD FACT active).
- Pytest `tests/fa`: **299 passed**. Stage 9 remains **TESTED / UAT_IN_PROGRESS** — not UAT_ACCEPTED / not DONE. No final FA synthesis. Stages 1–8 production behavior preserved.

## 2026-09-29 — Stage 9 Visa ACCEPTED + RIO full UAT pack (UAT_IN_PROGRESS)

- User ACCEPTED **V (Visa) Stage 9 UAT v1** → `fa_data/uat/V_stage9_uat_accepted_v1.md` (report lightly marked; primary-legal/HFA verification/fix history preserved).
- Ran RIO production-like `run_stage9("RIO", require_fa_list=False, ensure_history=True)` (live SEC); wrote `fa_data/uat/RIO_stage9_uat_report_v1.md` (PENDING_HUMAN_REVIEW).
- RIO machine **REVIEW_REQUIRED**, NON-TERMINATING; soft **A8** (`semantic_soft_commodity`); concentration customer/geo high (China Baowu / China demand); `S9_HFA_GEO_MATERIAL`; windfall≠franchise + capital_cycle + china_geo_demand emphasis; **no mechanical commodity=bad**.
- **Generic defects fixed:** IFRS/20-F revenue discovery; pension "new entrants" ≠ moat attack; geo country-name substance tightening; soft A8 commodity packaging + A8-aware TB_DISRUPTION wording. Visa CapEx/primary-legal/HFA fixes retained.
- Pytest `tests/fa`: **292 passed**. Stage 9 remains **TESTED / UAT_IN_PROGRESS** — not UAT_ACCEPTED / not DONE. No final FA synthesis. Stages 1–8 production behavior preserved.

## 2026-09-29 — Stage 9 IMPLEMENTED + TESTED / UAT_IN_PROGRESS (Visa UAT pack; STOP for accept)

- User authorized FA Stage 9 **IMPLEMENTATION** (SPEC_LOCKED plan).
- Created `fa/stage9/` thin architecture (mirror Stage 7/8): `__init__`, `questions`, `calc`, `handoff`, `semantic`, `evaluate`, `report`, `pipeline` (`run_stage9`), `storage`.
- Thin additive types on `fa/models.py` (`Stage9Report`, ER lenses, thesis breakers, semantic, `AnalyzeResult.stage9`).
- ER1–ER8; FP-E1–E12 flags; S9_HFA_* carries; NON-TERMINATING outcomes; source-first filings heuristic MVP.
- ER2: Gate2/S1/S5 hypotheses only — no S5 pricing-power redo / no S1 thesis restatement.
- ER8: 3–7 falsifiers — NOT giant risk register.
- Pytest `tests/fa`: **288 passed** (Stages 1–8 preserved).
- First full UAT: **V (Visa)** → `fa_data/uat/V_stage9_uat_report_v1.md` (PENDING_HUMAN_REVIEW). Machine outcome **REVIEW_REQUIRED**, NON-TERMINATING.
- **RIO not run.** Stage 9 = **TESTED / UAT_IN_PROGRESS** — **not** UAT_ACCEPTED / **not** DONE.
- No `analyze_company` wire. No final FA synthesis. Stages 1–8 untouched. No BUY/SELL/scores/colors/numeric risk gates.

# Changelog

## 2026-10-01 — Company FA History Registry automatic write hooks (IMPLEMENTED/TESTED; not DONE/UAT)

- Wired Plan §0.F post-artifact hooks: `fa/registry/hooks.py` (`hook_stage_after_save`, `hook_final_fa_after_artifact` / `register_final_fa_artifact`).
- Stages 1–9 `save_stageN_report` call hook AFTER version+CURRENT write; return shape unchanged `{version_id, path}`.
- Stage 2: added `fa/stage2/storage.py` (Thesis CURRENT+versions+Generated); `fa/pipeline.py` persist block uses `save_stage2_report` only (no evaluate/calc changes).
- Final FA: thin `fa/final_fa/storage.py` stub writes CURRENT+versions + hook — **no synthesis**.
- Failure: artifact SoR intact; registry txn rollback; kill-switch `FA_REGISTRY_HOOKS=0`; `register`/`skip_registry`/`uat_status` kwargs.
- Tests: `tests/fa/test_registry_hooks.py`; registry+hooks pass; full `tests/fa` ~323 pass / 3 known Stage 8 freshness fails (clock).
- Lifecycle remains **IMPLEMENTED / TESTED** — **NOT DONE / NOT UAT_ACCEPTED**.

## 2026-09-29 — Stage 9 SPEC_LOCKED (design freeze)

- User authorized DESIGN FREEZE / SPEC_LOCK for FA Stage 9.
- Plan §0 Locked operating model; D1–D15 APPROVED; Decision Pass + Research = SPEC_LOCKED companions (Plan wins).
- Lifecycle = **SPEC_LOCKED** only — **NOT IMPLEMENTED** / **NOT TESTED** / **NOT UAT_ACCEPTED** / **NOT DONE**.
- No `fa/stage9`. No UAT. No final FA synthesis. Stages 1–8 untouched.
- Docs under butterbear `03_Fundamental/STAGE_9_EXTERNAL_RISK_{PLAN,DECISION_PASS,RESEARCH}_v1.md`.

## 2026-09-29 — Stage 9 Decision Pass APPROVED D1–D15 (NOT SPEC_LOCKED)

- Created `STAGE_9_EXTERNAL_RISK_DECISION_PASS_v1.md`; Plan §0 lightly annotated.
- D1–D15 **APPROVED** (Plan recommendations + locked ER2/ER8 constraints).
- Lifecycle = **DECISION_PASS_COMPLETE** / awaiting SPEC_LOCK. **NOT SPEC_LOCKED**. **NOT IMPLEMENTED**.
- No `fa/stage9`. No UAT. No final FA synthesis. Stages 1–8 untouched.
- Docs under butterbear `03_Fundamental/STAGE_9_EXTERNAL_RISK_{DECISION_PASS,RESEARCH,PLAN}_v1.md`.

## 2026-09-29 — Stage 9 design/pre-analysis started (NOT SPEC_LOCKED)

- Created FA Stage 9 Research + Plan v1 (design only): industry/competition/macro/external risk.
- Lifecycle = **DESIGN / RESEARCH_IN_PROGRESS**. **NOT SPEC_LOCKED**. **NOT IMPLEMENTED**.
- No `fa/stage9`. No Decision Pass. No UAT. No final FA synthesis. Stages 1–8 untouched.
- Proposed: ER1–ER8; risk=mechanism+exposure+evidence; source-first (no warehouse); NON-TERMINATING outcomes; UAT candidate **V + RIO**; D1–D15 OPEN.
- Docs live under butterbear `03_Fundamental/STAGE_9_EXTERNAL_RISK_{RESEARCH,PLAN}_v1.md`.

## 2026-09-29 — Stage 8 NVDA ACCEPTED + component DONE / UAT_ACCEPTED

- User ACCEPTED **NVDA Stage 8 UAT v1**; ROP Stage 8 UAT v1 **ACCEPTED** preserved.
- Recorded: ROP Stage 8 UAT v1 = ACCEPTED; NVDA Stage 8 UAT v1 = ACCEPTED; Stage 8 component UAT = ACCEPTED.
- Accept artifacts: `fa_data/uat/NVDA_stage8_uat_accepted_v1.md`, `fa_data/uat/STAGE8_component_uat_accepted.md` (NVDA report lightly marked; verification/fix history preserved).
- Closure checks: `uv run pytest tests/fa -q` → **269 passed**; no open blocking generic Stage 8 defect (CapEx-proxy, opacity≠incoherent, ceiling provenance, EXIT_FCFF_MULTIPLE, regime-mismatch MIXED — all fixed); UAT artifacts preserved; ROP accepted regression preserved; Stages 1–7 production modules untouched; **Stage 9 = PLANNED, not started**.
- Closed Stage 8 as **DONE / UAT_ACCEPTED**.


## 2026-09-29 — Stage 8 pre-accept verification (NVDA) — ceiling / exit-multiple / VA3 regime

- Verified FA Stage 8 before NVDA UAT accept; lifecycle remains **TESTED / UAT_IN_PROGRESS** (not UAT_ACCEPTED / not DONE). No Stage 9.
- **Generic defect fixed:** reverse-DCF search ceiling no longer presented as solved point estimate — `unresolved_above_search_range` / `lower_bound_only` / `implied_fcff_growth > 30%` + EV residual at ceiling.
- **Generic defect fixed:** `EXIT_EBITDA_MULTIPLE` applied to FCFF → honest rename **`EXIT_FCFF_MULTIPLE`** (formula `TV=final_FCFF×multiple`; not_ebitda explicit). No EBITDA invented.
- **Generic defect fixed:** VA3 PASS from generic low-growth RESEARCH_CANDIDATE paths when Stage4 shows high-growth regime → **VA3/VA7 MIXED**, `defensible_iv=False`, uncertainty↑; **did not** retune assumptions to market price.
- CapEx-proxy≠FCFF + opacity≠incoherent fixes **retained**.
- Re-ran NVDA Stage 8 + accepted ROP Stage 8 regression; updated `NVDA_stage8_uat_report_v1.md` + `ROP_stage8_uat_report_v1.md`.
- Pytest `tests/fa`: **269 passed**.


## 2026-09-29 — Stage 8 ROP ACCEPTED + NVDA UAT pack (UAT_IN_PROGRESS)

- User ACCEPTED **ROP Stage 8 UAT v1** → `fa_data/uat/ROP_stage8_uat_accepted_v1.md` (report lightly marked; CapEx-proxy + opacity≠incoherent verification/fix history preserved).
- Ran NVDA production-like Stage 4/6/7 + Stage 8; wrote `fa_data/uat/NVDA_stage8_uat_report_v1.md` (PENDING_HUMAN_REVIEW).
- NVDA machine **REVIEW_REQUIRED**; expectations=**heroic** (≥30% reverse-DCF ceiling-bound); uncertainty=high; freshness=CURRENT; PRIMARY **A4**; FCFF with CapEx; dual-terminal CROSS-CHECKS ~8.6% never averaged; price≫envelope = descriptive premium **not** auto-expensive/SELL.
- Generic fixes: history `_revenue_series` freshest FY tag; Jan-FYE quarter prior-calendar alignment; Stage 8 gross_debt display from bridge; `periods_used` FY sort.
- Pytest `tests/fa`: **266 passed**. Stage 8 remains **TESTED / UAT_IN_PROGRESS** — not UAT_ACCEPTED / not DONE. No Stage 9. Stages 1–7 production behavior preserved.


## 2026-09-29 — Stage 8 reverse-DCF opacity≠incoherent verification fix (ROP UAT pack update)

- **Generic defect fixed:** `(heroic|demanding) AND A7 AND S6_H7_ACQ_RETURN_OPACITY` no longer forces `incoherent_with_evidence`.
- Opacity / acquisition-return opacity = **uncertainty↑ / REVIEW lean**; keep provisional rate-band label (`heroic` for ROP ~17.7%).
- `incoherent_with_evidence` retained only for actual contradictory prior-stage evidence (e.g. Stage4 growth hint << implied heroic).
- CapEx-proxy fix (`OCF_PROXY_INCOMPLETE_NOT_FCFF`) kept intact.
- Regression tests: A7+opacity alone ≠ incoherent; Stage4 contradiction still can. pytest **264**.
- ROP Stage 8 re-run + `fa_data/uat/ROP_stage8_uat_report_v1.md` updated. Lifecycle remains **TESTED / UAT_IN_PROGRESS**. NVDA not run. No Stage 9.

## 2026-09-29 — Stage 8 CapEx-proxy verification fix (ROP UAT pack update)

- **Generic defect fixed:** CapEx null / `ocf_proxy_capex_unknown` no longer silently treated as FCFF with VA3 PASS.
- DCF method becomes `OCF_PROXY_INCOMPLETE_NOT_FCFF`; `base_incomplete=True`; `authoritative_fcff=False`; `base_fcff=None`.
- VA3/VA7 → **MIXED** with explicit PROVISIONAL / OCF-proxy ≠ FCFF; VA8 WHY notes RESEARCH_CANDIDATE provisional.
- Reverse-DCF `incoherent_with_evidence` verified to require A7+S6 evidence conflict (rate-alone → `heroic` only) — no defect.
- ROP Stage 8 re-run + `fa_data/uat/ROP_stage8_uat_report_v1.md` updated. Lifecycle remains **TESTED / UAT_IN_PROGRESS**. pytest **262**. NVDA not run. No Stage 9.


## 2026-09-29 — Stage 8 TESTED / UAT_IN_PROGRESS (ROP first UAT)

- Authorized FA Stage 8 implementation per Plan §0 SPEC_LOCKED.
- Added `fa/stage8/` (calc/market_data/normalization/dcf/reverse_dcf/archetype/benchmark/semantic/evaluate/report/pipeline/storage/questions).
- Thin Stage 8 types on `fa/models.py`; `AnalyzeResult.stage8`; **not** wired into `analyze_company`.
- Pytest `tests/fa`: **260 passed**. Stage 8 = **TESTED / UAT_IN_PROGRESS** (not UAT_ACCEPTED / not DONE).
- ROP Stage 8 UAT v1 pack: `fa_data/uat/ROP_stage8_uat_report_v1.md` — machine **REVIEW_REQUIRED**; expectations=incoherent_with_evidence; A7 dual exhibits; dual-terminal CROSS-CHECKS never averaged; freshness=CURRENT; NON-TERMINATING.
- NVDA not run. Stage 9 not started. Stages 1–7 behavior preserved. No BUY/SELL/scores/colors/universal valuation gates.

## 2026-09-29 — Stage 7 META ACCEPTED + component DONE / UAT_ACCEPTED

- User ACCEPTED **META Stage 7 UAT v1**; ROP Stage 7 UAT v1 **ACCEPTED** preserved.
- Recorded: ROP Stage 7 UAT v1 = ACCEPTED; META Stage 7 UAT v1 = ACCEPTED; Stage 7 component UAT = ACCEPTED.
- Accept artifacts: `fa_data/uat/META_stage7_uat_accepted_v1.md`, `fa_data/uat/STAGE7_component_uat_accepted.md` (META report lightly marked; provenance audit preserved).
- Closure checks: full `pytest tests/fa` → **241 passed**; no open blocking generic Stage 7 defect; UAT/provenance artifacts preserved; ROP accepted regression preserved; Stages 1–6 untouched; **Stage 8 = PLANNED, not started**.
- Closed Stage 7 as **DONE / UAT_ACCEPTED**.

## 2026-09-29 — Stage 7 META MG8 evidence-sufficiency fix (UAT_IN_PROGRESS)

- Verified MG8 Communication & Execution Credibility on META: prior PASS with `execution_tag=unknown` was **not** justified (combined lens).
- Generic fix E4: taxonomy alone ≠ PASS when execution half UNKNOWN → **MIXED**; `insufficient_history` may still PASS (ROP posture).
- META Stage 7 re-run v009: MG8=**MIXED**; ROP v011 regression unchanged (MG8 PASS / REVIEW_REQUIRED). pytest **241 passed**.
- Stage 7 remains **TESTED / UAT_IN_PROGRESS** — not UAT_ACCEPTED / not DONE. No Stage 8.

# Changelog

## 2026-10-01 — Company FA History Registry automatic write hooks (IMPLEMENTED/TESTED; not DONE/UAT)

- Wired Plan §0.F post-artifact hooks: `fa/registry/hooks.py` (`hook_stage_after_save`, `hook_final_fa_after_artifact` / `register_final_fa_artifact`).
- Stages 1–9 `save_stageN_report` call hook AFTER version+CURRENT write; return shape unchanged `{version_id, path}`.
- Stage 2: added `fa/stage2/storage.py` (Thesis CURRENT+versions+Generated); `fa/pipeline.py` persist block uses `save_stage2_report` only (no evaluate/calc changes).
- Final FA: thin `fa/final_fa/storage.py` stub writes CURRENT+versions + hook — **no synthesis**.
- Failure: artifact SoR intact; registry txn rollback; kill-switch `FA_REGISTRY_HOOKS=0`; `register`/`skip_registry`/`uat_status` kwargs.
- Tests: `tests/fa/test_registry_hooks.py`; registry+hooks pass; full `tests/fa` ~323 pass / 3 known Stage 8 freshness fails (clock).
- Lifecycle remains **IMPLEMENTED / TESTED** — **NOT DONE / NOT UAT_ACCEPTED**.

## 2026-09-29 — Stage 7 ROP ACCEPTED + META UAT pack (UAT_IN_PROGRESS)

- Recorded ROP Stage 7 UAT v1 **ACCEPTED** → `fa_data/uat/ROP_stage7_uat_accepted_v1.md` (report lightly marked; history preserved).
- Ran META production-like Stage 6 + Stage 7; wrote `fa_data/uat/META_stage7_uat_report_v1.md` (PENDING_HUMAN_REVIEW).
- META outcome **REVIEW_REQUIRED** (NON-TERMINATING); MG1 **aligned**; dividend **residual**; dual-class/founder neutral (FP-M1/M7 watchable only).
- Fixed 4 generic Stage 7 defects (hierarchy CapEx/return-of-capital; Dividend Policy heading ≠ commitment; buyback boilerplate; ASC guidance noise).
- Pytest `tests/fa`: **237 passed**. Stage 7 remains **TESTED / UAT_IN_PROGRESS** — not UAT_ACCEPTED / not DONE. No Stage 8.

## 2026-09-29 — Stage 7 IMPLEMENTED → TESTED (ROP UAT pack; STOP before META)

- Authorized FA Stage 7 implementation per Plan §0 SPEC_LOCKED.
- Added `fa/stage7/` (calc/semantic/benchmark/evaluate/report/pipeline/storage/questions/archetype).
- Thin Stage 7 types on `fa/models.py`; `AnalyzeResult.stage7` field; **not** wired into `analyze_company`.
- Pytest `tests/fa`: **233 passed**. Stage 7 = **TESTED** (not UAT_ACCEPTED / not DONE).
- ROP Stage 7 UAT v1 pack prepared; META not started; Stage 8 not started; Stages 1–6 behavior preserved.

## 2026-09-29 — Stage 7 design/pre-analysis (NOT SPEC_LOCKED)

- Authorized FA Stage 7 RESEARCH + ARCHITECTURE/DESIGN only → lifecycle **DESIGN / RESEARCH_IN_PROGRESS**.
- Created transition docs: `STAGE_7_MANAGEMENT_ALLOCATION_RESEARCH_v1.md` + `STAGE_7_MANAGEMENT_ALLOCATION_PLAN_v1.md`.
- Core objective: allocation / incentives / communication / execution for long-term owner value (not “is management good?”).
- Boundaries: Stage 6 owns ROIC math; Stage 7 consumes `S6_H7_*` only; Stage 8 not started.
- Plan §24 D1–D15 OPEN. UAT lean ROP+META. Dashboard 8 blocks. MG1–MG9 proposed (challenge/reduce).
- Confirmed **no** `fa/stage7`. Stages 1–6 untouched. **NOT SPEC_LOCKED.**

# Changelog

## 2026-10-01 — Company FA History Registry automatic write hooks (IMPLEMENTED/TESTED; not DONE/UAT)

- Wired Plan §0.F post-artifact hooks: `fa/registry/hooks.py` (`hook_stage_after_save`, `hook_final_fa_after_artifact` / `register_final_fa_artifact`).
- Stages 1–9 `save_stageN_report` call hook AFTER version+CURRENT write; return shape unchanged `{version_id, path}`.
- Stage 2: added `fa/stage2/storage.py` (Thesis CURRENT+versions+Generated); `fa/pipeline.py` persist block uses `save_stage2_report` only (no evaluate/calc changes).
- Final FA: thin `fa/final_fa/storage.py` stub writes CURRENT+versions + hook — **no synthesis**.
- Failure: artifact SoR intact; registry txn rollback; kill-switch `FA_REGISTRY_HOOKS=0`; `register`/`skip_registry`/`uat_status` kwargs.
- Tests: `tests/fa/test_registry_hooks.py`; registry+hooks pass; full `tests/fa` ~323 pass / 3 known Stage 8 freshness fails (clock).
- Lifecycle remains **IMPLEMENTED / TESTED** — **NOT DONE / NOT UAT_ACCEPTED**.

## 2026-09-29 — Stage 6 closure

- Accepted `fa_data/uat/V_stage6_uat_report_v1.md` via `fa_data/uat/V_stage6_uat_accepted_v1.md` and preserved the historical report with light status markers.
- Confirmed existing ROP Stage 6 acceptance artifacts.
- Added `fa_data/uat/STAGE6_component_uat_accepted.md` and closed Stage 6 as **DONE / UAT_ACCEPTED**.
- Verified `python -m pytest tests/fa -q --tb=line`: **212 passed**.
- Verified no open generic Stage 6 automation defect blocks closure; disclosure/judgment limitations remain non-blocking.
- Kept Stages 1–5 untouched. Stage 7 remains **PLANNED**, not started.
