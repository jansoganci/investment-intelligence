# Project Status

**As of:** 2026-10-02 (Europe/Istanbul) — POST-REMEDIATION FULL REVALIDATION frozen; Checkpoint C READY_FOR_USER_DECISION; A1 PARTIAL/OPEN; no Wave 5; no Audit PASS/FAIL

| Scope | Status |
|-------|--------|
| Stages 1–8 | **DONE / UAT_ACCEPTED** (unchanged) |
| Stage 9 | **DONE / UAT_ACCEPTED** (unchanged) |
| Final FA synthesis | **DONE / UAT_ACCEPTED** |
| Company FA History / Run Registry | **DONE / UAT_ACCEPTED** |
| Final System Audit (evidence 0–3, 5–7 + Claude cross-check RC) | **IN PROGRESS** — Wave 1 IMPLEMENTED/TESTED; Wave 2 SEALED; Wave 3 **ACCEPTED/CLOSED**; Wave 4 **DONE / UAT_ACCEPTED** (B4/C1/C2/C3 accepted 2026-10-02; A1 remains PARTIAL/OPEN); Market Price v1 still IMPLEMENTED/TESTED; Checkpoint C open; no Wave 5 |







## Wave 4 dual-series / duration / growth-basis / disruption wording (2026-10-02) — DONE / UAT_ACCEPTED

- Scope: **B4** archetype/evidence-conditioned disruption wording; **C3** Stage 2 growth basis (QoQ + YoY companion); **C2** duration_days / unequal-duration flag; **C1** dual-series honesty / COMPARABILITY_BREAK.
- Spec: `docs/WAVE4_SPEC_DECISIONS_B4_C1_C2_C3_v1.md` (SD-W4-B4/C1/C2/C3); thin cites Stage 9/4/2/6 Plan + Data Architecture.
- Code: `fa/stage9/evaluate.py`; `fa/stage2/calc.py`+`evaluate.py`; `fa/stage4/calc.py`+`map_companyfacts.py`; `fa/comparability.py`; `fa/stage6/calc.py`+`evaluate.py`.
- Tests: `tests/fa/test_wave4_dual_series_duration.py` (12); full `tests/fa` **416 passed** / 1 skipped.
- Retest pack: `audit/retests/wave4_dual_series_duration_v1/` (pre_fix + post_fix + `W4_REGRESSION_MATRIX.md` + UAT).
- User acceptance: Can Soganci **ACCEPTED** Wave 4 on **2026-10-02**. B4/C3/C2/C1 are **RESOLVED**; A1 remains **PARTIAL/OPEN**. UAT = **UAT_ACCEPTED / DONE**. No overall audit PASS/FAIL.
- Wave 3 **ACCEPTED/CLOSED**. No W1–W3 reopen. No A1 fix. No Market Price. No production CURRENT/Registry mass regen. No ticker hardcodes.
- **DONE / UAT_ACCEPTED** — acceptance recorded. Preserve all audit/retest evidence. Do **not** start Wave 5.

## Wave 3 external coherence (2026-10-02) — IMPLEMENTED / TESTED

- Scope: **A7** OE period coherence; **B3** material post-period events honesty; **B1** PPA semantic; **B2** ER5/ER8 (SPEC-locked SD-W3-ER5/ER8).
- Spec: `docs/WAVE3_SPEC_DECISIONS_ER5_ER8_v1.md`; thin cite Stage 9 Plan §0 + Decision Pass.
- Code: `fa/stage8/normalization.py`, `market_data.py`, `evaluate.py`; `fa/stage5/semantic.py`; `fa/stage6/semantic.py`; `fa/stage9/semantic.py`, `evaluate.py`.
- Tests: `tests/fa/test_wave3_external_coherence.py`; full `tests/fa` **404 passed** / 1 skipped.
- Retest pack: `audit/retests/wave3_external_coherence_v1/` (pre_fix + post_fix + `W3_REGRESSION_MATRIX.md`).
- Proposed: A7/B3/B1/B2 **RESOLVED_CANDIDATE**; A1 **PARTIAL/OPEN** (outside W3). **Not** auto-closed. No overall audit PASS/FAIL.
- **STOP** — await user acceptance. Do **not** start Wave 4. No Market Price changes. No W1/W2 reopen. No production CURRENT/Registry mass regen.

## Wave 2 XBRL/mapping (2026-10-02) — IMPLEMENTED / TESTED

- Scope: **A1** debt perimeter honesty + SecuredDebt; **A3** DHR cash tag; **A4-p1** INTU STI AFS; **A4-p2** client funds IC exclude + honesty (no invented payable); **A5** AZO inventory NetOfReserves; **A6** COST ReceivablesNetCurrent.
- Spec: locked `WAVE2_SPEC_DECISIONS_A1_A4_v1.md` (A1 dual/incomplete honesty; A4 exclude client restricted + flag).
- Code: `fa/map_companyfacts.py`, `fa/contract.py`, `fa/stage2/calc.py`, `fa/stage2/evaluate.py`, `fa/stage6/calc.py`.
- Tests: `tests/fa/test_wave2_mapping.py`; full `tests/fa` **388 passed** / 1 skipped.
- Retest pack: `audit/retests/wave2_mapping_v1/` (pre_fix + post_fix + `W2_REGRESSION_MATRIX.md`).
- User-accepted statuses: A3/A4 STI/A4 client funds/A5/A6 **RESOLVED_CANDIDATE**; A1 **PARTIAL/OPEN** (keep — do not close).
- Seal: Stage 6 Decision Pass D4 + Plan §0.D thin-cite SD-W2-A4 (rule not redesigned); isolated S8+Final replay `audit/retests/wave2_seal_s8_final_v1/` vs pre-W2 price-injection baseline (same 2026-09-30 RAW closes).
- **STOP** — Wave 2 sealed. Do **not** start Wave 3. Do **not** close A1. No overall audit PASS/FAIL.

## Wave 1 period normalization (2026-10-02) — IMPLEMENTED / TESTED

- Scope: **F-S3-CUM-01** + **A2/F-DERIVE-YTD-Q4-01** only.
- Code: `fa/stage3/calc.py`, `fa/quarter_derivation.py`, `fa/map_companyfacts.py`.
- Tests: `tests/fa/test_wave1_period_normalization.py`; full `tests/fa` 373 passed / 1 skipped.
- Retest pack: `audit/retests/wave1_period_normalization_v1/` (pre_fix + post_fix + `W1_REGRESSION_MATRIX.md`).
- Proposed: F-S3-CUM-01 **RESOLVED_CANDIDATE**; A2 **RESOLVED_CANDIDATE**. **Not** auto-closed. No overall audit PASS/FAIL.
- **STOP** — wait for user acceptance before Wave 2.

## Audit retest note (2026-10-02)

- Isolated Stage 8 price-injection retest completed under authorization (observation only).
- Artifacts: `audit/retests/stage8_price_injection_2026-09-30_close_v1/`.
- F-S8-PRICE-01 **CONFIRMED** by retest evidence; register **not** closed; no code fixes; no overall PASS/FAIL.

## Market Price v1 (2026-10-02) — IMPLEMENTED / TESTED (not DONE / not UAT_ACCEPTED)

- Code: `fa/market_price/` — Yahoo primary + Stooq secondary; RAW close; cache; retry; conflict threshold; `resolve_and_run_stage8` harness.
- Tests: `tests/fa/test_market_price_v1.py` (15 passed, 1 network skipped). Full `tests/fa`: 361 passed / 1 skipped; **3 known Stage 8 freshness fails not reproducing at this wall-clock** (left unfixed).
- Adapter retest: `audit/retests/stage8_market_price_adapter_v1/` (fixture-labeled; Stooq live SSL fail documented).
- Stage 8 analytical logic (DCF/reverse DCF/MoS/VA) **untouched**. Plan/Decision Pass markdown **untouched**. Findings **not** fixed.
- Lifecycle: **IMPLEMENTED / TESTED** only — **not** DONE / **not** UAT_ACCEPTED (no user UAT).


## Final FA synthesis (DONE / UAT_ACCEPTED)

- Auth: Final FA Synthesis UAT v2 **ACCEPTED** by Can Soganci (2026-10-01). Lifecycle = **DONE / UAT_ACCEPTED**.
- Canonical: butterbear `03_Fundamental/FINAL_FA_SYNTHESIS_PLAN_v1.md` §0 (**Plan wins**; locked rules unchanged).
- Code: `fa/final_fa/` — `run_final_fa` on production fa_data; Stages 1–9 analytical logic **untouched**.
- Accepted UATs: ROP Final FA UAT = **ACCEPTED**; Visa (V) Final FA UAT = **ACCEPTED**; Final FA Synthesis component UAT = **ACCEPTED**.
- Packs: `fa_data/uat/ROP_final_fa_uat_report_v2.md` + `ROP_final_fa_uat_accepted_v2.md`; `V_final_fa_uat_report_v2.md` + `V_final_fa_uat_accepted_v2.md`; `FINAL_FA_component_uat_accepted.md`. v1 packs preserved.
- Outcomes (v002 CURRENT at UAT close; later audit regression bumped version under clone): **ROP `ORANGE`** / `technical_eligible=False`; **V `REVIEW_REQUIRED`** / `technical_eligible=False` (FACT breaker, not auto-RED).
- Pytest at closure: `tests/fa/test_final_fa.py` **20 passed**; full `tests/fa` **343 passed / 3 known Stage 8 freshness fails** (non-blocking; not fixed).
- Next: Final System Audit Checkpoint C / optional Phase 4. No TA / watchlist / portfolio.

## Company FA History / Run Registry (DONE / UAT_ACCEPTED)

- Auth: IMPLEMENT (2026-10-01) + **FINAL UAT + CLOSURE** (2026-10-01). Lifecycle = **DONE / UAT_ACCEPTED**. Registry UAT = **ACCEPTED**.
- Canonical: butterbear `00_System/COMPANY_FA_HISTORY_REGISTRY_PLAN_v1.md` §0 (**Plan wins**; design freeze still authoritative for schema).
- Code: `fa/registry/` (schema, writers, backfill, drift, backup, views export, **hooks**). DB: `fa_data/registry/fa_run_registry.sqlite`.
- Stages 1–9 analytical logic **unchanged**.

## Stage 9 (closed — unchanged)

- Code: `fa/stage9/` (`run_stage9` independent; not wired into `analyze_company`).
- Spec: `STAGE_9_EXTERNAL_RISK_PLAN_v1.md` §0 SPEC_LOCKED (Plan wins; Decision Pass + Research companions).
- Full UAT #1: **V (Visa)**; #2: **RIO** → Component **DONE / UAT_ACCEPTED**.

## Stage 8 (closed — unchanged)

- Code: `fa/stage8/`. Spec: `STAGE_8_VALUATION_PLAN_v1.md` §0 SPEC_LOCKED.
- ROP+NVDA UAT accepted. Component DONE / UAT_ACCEPTED.
- Known 3 Stage 8 freshness pytest fails + NVDA regression STALE→TOO_HARD: **catalogued NON_BLOCKING**; not fixed.

## Where we stopped

**2026-10-02 (Europe/Istanbul):** POST-REMEDIATION FULL REVALIDATION **completed / frozen** under `investment_intelligence/audit/post_remediation_full_revalidation_2026-10-02/`. Pytest 417 passed / 1 skipped. Five-company E2E complete; Stage 8 Yahoo YES×5; Stooq OPEN; A1 PARTIAL/OPEN. Proposed revalidation status **PARTIAL**. Checkpoint C **READY_FOR_USER_DECISION**. No Final System Audit PASS/FAIL declared. No Wave 5. No FA code edits this run.


## Continue here

0. **Wave 4 DONE / UAT_ACCEPTED** (2026-10-02): B4/C1/C2/C3 accepted by user; see Wave 4 section. No Wave 5. Spec `docs/WAVE4_SPEC_DECISIONS_B4_C1_C2_C3_v1.md`.
0. **Wave 3 ACCEPTED/CLOSED** (2026-10-02). Spec `docs/WAVE3_SPEC_DECISIONS_ER5_ER8_v1.md`.
0. **Wave 2 SEALED** (2026-10-02): A1 remains PARTIAL/OPEN. Spec `docs/WAVE2_SPEC_DECISIONS_A1_A4_v1.md`.
0. **Stage 8 Market Price v1** = **IMPLEMENTED / TESTED** (2026-10-02): `fa/market_price/`; Plan §0.T still canonical; **not** DONE/UAT_ACCEPTED without user UAT.
0. **User review** of Claude RC pack + priority table; authorize (or waive) fix waves — **do not** start fixes without auth.
1. Before any Stage 8 retest: authorize F-S8-PRICE-01 price injection **and** B3 post_period honesty (empty events = false negative).
2. Highest-severity remaining candidates: A1 debt, A2 YTD→Q4; then B2 FTC miss, A7 OE, and any still-open items in the findings register.
3. Spec reopen candidates: A1 captive FS; A4 client funds. Wave 4 C1/C2 are resolved; any reopen requires new authorization.
4. Phase 2 held-out freezes remain **authoritative / unchanged**. Known 3 S8 freshness pytest fails stay catalogued.
2. **Checkpoint C** awaiting **user** after ChatGPT Phase 4 review of findings (agent does **not** declare overall audit PASS/FAIL).
3. Do **not** modify Stages 1–9 / Final FA / Registry analytical logic; do **not** silently fix 3 known S8 freshness pytest fails; do **not** start TA / watchlist / portfolio under this audit.
4. For H1 freeze review: prefer production `audit/heldout/H1_DE/` and/or versioned `*_v001.*` (clone CURRENT hardlink mutation = TEST_INVALIDATED risk / F-REG-D1).
5. **Final FA synthesis** — **DONE / UAT_ACCEPTED** (closed).
6. **Company FA History / Run Registry** — **DONE / UAT_ACCEPTED** (closed).
7. Separate/open: **Dragonomi** RI adapter.
