# Wave 4 deliverable — B4 disruption wording / C3 growth basis / C2 duration / C1 dual-series

**When:** 2026-10-02 (Europe/Istanbul)  
**Auth:** WAVE 4 SPEC LOCK + IMPLEMENTATION + REGRESSION + UAT (Can Soganci). Wave 3 **ACCEPTED/CLOSED**. Wave 4 **ACCEPTED** by Can Soganci on **2026-10-02**. **NO Wave 5.**

## Accepted finding status (user accepted 2026-10-02)

| Finding | ID | Accepted status |
|---------|----|-----------------|
| B4 fintech template leakage | F-S9-FINTECH-TEMPLATE-01 (B4) | **RESOLVED** |
| C3 Stage 2 growth basis | F-S2-REVGROWTH-BASIS-01 (C3) | **RESOLVED** |
| C2 53-week / duration | F-DURATION-53W-01 (C2) | **RESOLVED** |
| C1 Veralto / dual-series | F-COMPARABILITY-SPIN-01 (C1) | **RESOLVED** (mechanism; held-out filing-stub auto-path note) |
| A1 DE debt | F-MAP-DE-DEBT-01 | **PARTIAL/OPEN** (outside W4 — unchanged) |

## 1. SPEC files

- `docs/WAVE4_SPEC_DECISIONS_B4_C1_C2_C3_v1.md` (+ mirror `03_Fundamental/`) — **SD-W4-B4 / C1 / C2 / C3 SPEC_LOCKED**
- Thin cites: Stage 9 Plan §0.F + Decision Pass (B4); Stage 4 Plan §0 (C1/C2); Stage 2 Plan (C3); Stage 6 Plan (C1); `FUNDAMENTAL_DATA_ARCHITECTURE_v1.md` (C1/C2); Stage 6 Decision Pass doc control

## 2. Code files

- `fa/stage9/evaluate.py` — B4 conditioned disruption wording helpers
- `fa/stage2/calc.py` + `fa/stage2/evaluate.py` — C3 `revenue_growth_qoq` / basis / `revenue_growth_yoy`
- `fa/stage4/calc.py` + `fa/map_companyfacts.py` — C2 `duration_days` / unequal-duration YoY honesty
- `fa/comparability.py` (new) + `fa/stage4/calc.py` / `evaluate.py` + `fa/stage6/calc.py` / `evaluate.py` — C1 dual-series / COMPARABILITY_BREAK
- `tests/fa/test_wave4_dual_series_duration.py` — focused Wave 4 suite
- `PROJECT_STATUS.md`, `CHANGELOG.md` — thin Wave 4 notes

## 3. Tests + results

| Suite | Result |
|-------|--------|
| Focused Wave 4 | **12 passed** |
| Stage 2 | **18 passed** |
| Norm/duration (Q-derivation + W1) | **27 passed** |
| Relevant S4/5/6/8 | **57 passed** |
| Stage 9 + Final + Wave 3 | **67 passed** |
| Full `tests/fa` | **416 passed**, 1 skipped |

## 4. Held-out matrix

See `W4_REGRESSION_MATRIX.md` (+ `pre_fix/`, `post_fix/`).

| Ticker | Key post-W4 result |
|--------|-------------------|
| DE | B4 fintech cleared; C3 qoq=−5.69% labeled + yoy≈+4.91%; C2 unequal-duration; Final REVIEW_REQUIRED |
| INTU | B4 fintech breaker retained (supported); C3 basis labeled; Final REVIEW_REQUIRED |
| COST | C2 53-week / unequal-duration; B4 no fintech; Final ORANGE |
| DHR | B4 no fintech; C1 cue-path COMPARABILITY_BREAK on FY2022→FY2023; pipeline semantic miss on filing stubs; Final REVIEW_REQUIRED |
| AZO | B4 fintech cleared; C2 unequal-duration; Final GREEN→ORANGE (soft gaps — user review) |

Phase 2 freezes and production fa_data/Registry **not** mutated. Same 2026-09-30 price baseline.

## 5. UAT results

See `uat/WAVE4_UAT_REPORT.md` + `uat/uat_non_regression_results.json`.  
**UAT_ACCEPTED / DONE** (accepted by Can Soganci on 2026-10-02).

## 6. Stage / Final diffs (W4-attributable)

- **S9 (B4):** unsupported fintech monitor noun phrase removed for non-fintech issuers; V/INTU retain supported fintech.
- **S2 (C3):** growth basis explicit; YoY companion when prior-year period exists.
- **S4 (C2/C1):** duration exhibits + unequal-duration flags; comparability breaks when perimeter cues/disclosure present; as-reported never overwritten.
- **S6 (C1):** ROIC windows annotated when breaks present; `roic_series_primary=as_reported`.
- **Final:** AZO ORANGE vs prior GREEN on re-run — retained as an accepted-UAT narrative outcome; not a separate finding closure.

## 7. Proposed statuses

B4 **RESOLVED** · C3 **RESOLVED** · C2 **RESOLVED** · C1 **RESOLVED** · A1 **PARTIAL/OPEN**.

## 8. UAT status

**UAT_ACCEPTED / DONE** — accepted by Can Soganci on **2026-10-02**.

## 9. New finding / ambiguity

- Isolated Wave 4 `fa_root` DHR Source filings are **stubs** (~60KB metadata) without full 10-K narrative → Stage 4 semantic does not auto-surface Veralto/discontinued cues. Mechanism verified via unit tests + disclosed-perimeter **cue-path**. Not treated as ticker hardcode. Full-text filing semantic fire remains environment-dependent.
- AZO Final GREEN→ORANGE on isolated re-run attributed to soft packaging gaps — user should confirm whether acceptable narrative drift.

## STOP

Wave 4 acceptance is recorded. Do **not** start Wave 5. Preserve all audit/retest evidence. No overall audit PASS/FAIL.
