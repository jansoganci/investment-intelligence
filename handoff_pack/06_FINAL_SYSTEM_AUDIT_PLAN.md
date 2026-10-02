# 06 — Final System Audit Plan (DRAFT ONLY — DO NOT EXECUTE)

**Status:** **PLANNED draft** for independent Final System Audit  
**Authority:** Handoff documentation only. **Do NOT run** the audit, fix code, re-UAT, or change analytical logic under this doc alone.  
**As of:** 2026-10-01 (Europe/Istanbul)  
**Prerequisite state:** Stages 1–9 + Final FA + Registry = DONE / UAT_ACCEPTED; 3 known S8 freshness pytest fails non-blocking.

---

## 1. Audit objective

Provide an **independent** verification that Investment Intelligence FA (Stages 1–9 + Final FA + Registry) behaves as specified in locked Plans — without relying on the implementing agent’s memory or informal claims.

**Out of scope for this audit (unless separately authorized):**  
TA, watchlist ranking, portfolio, Dragonomi, inventing thresholds, BUY/SELL advice, “improving” philosophy, fixing the 3 S8 freshness fails as a silent side quest (may **report** them).

---

## 2. Audit principles

| Principle | Meaning |
|-----------|---------|
| Clean-room | Prefer auditors / agents without prior implementation chat bias; use this handoff pack + canonical Plans |
| Deterministic first | Reproduce numbers from fixtures/artifacts with code/math; do not trust LLM restatement of arithmetic |
| Spec-anchored | Pass/fail vs Plan §0 + accepted UAT packs — not vs taste |
| No silent mutation | Audit may read and compute; **must not** modify production analytical logic without separate fix auth |
| Uncertainty explicit | Mark UNKNOWN / not evidenced rather than inventing |
| No BUY/SELL | Audit eligibility machinery and provenance — not investment recommendations |

---

## 3. Workstreams (draft)

### 3.A Clean-room deterministic verification

- Re-run **pytest** `tests/fa` in a clean environment; record full pass/fail inventory.  
- Expectation (from STATUS): ~343 pass class + **exactly document** the 3 known S8 freshness failures (names, assertions, whether clock/date dependent).  
- Spot-check deterministic CFS recon / FCF / ROIC exhibits / Final FA completeness gates against frozen fixtures or CURRENT artifacts for UAT tickers.  
- Confirm **no LLM arithmetic** paths for reconciling OCF / FCF / IV math (code owns math).

### 3.B Independent LLM / code / spec review

- Map each Stage Plan §0 lock → corresponding `fa/stageN/` module responsibilities (structure + key branches).  
- Flag any code path that appears to: invent numeric gates marked NOT LOCKED; emit R/O/G inside Stages 1–9; average dual-terminal IV; auto-RED on FACT breaker; auto-promote lists; hardcode UAT tickers into evaluate logic.  
- Confirm Final FA Plan wins behaviors: soft-missing ORANGE ceiling; FACT→REVIEW; `technical_eligible` definition; reconciliation ≠ voting.  
- Confirm Registry Plan: artifacts truth; no full JSON duplication; hooks post-write; CURRENT uniqueness.

### 3.C Accepted UAT reproduction (separate workstream)

- Re-run or re-load **accepted UAT companies** as a **separate** workstream from held-out black-box testing.  
- Stages (primary UAT names used during development): KO (1–5), ROP (4,6,7,8, Final FA), V (5,6,9, Final FA), META (7), NVDA (8), RIO (9).  
- Compare machine outcomes to accept packs: `process_outcome` / `final_state` / `technical_eligible` / key carries (or explain drift with artifact version IDs).  
- Prefer not peeking at expected narrative before the first freeze of reproduction outputs; then compare.

### 3.D Independent black-box / held-out company testing

**Required (strengthen independence):**

1. Select **at least 2 held-out companies** that were **not** used as primary UAT names during Stage 1–9 / Final FA development (i.e. avoid treating KO, ROP, V, META, NVDA, RIO as the held-out set).  
2. Auditor must **not** inspect expected outputs / accept packs / prior Final FA narratives for those tickers **before** running the system.  
3. **First** run the system (Stages as needed + Final FA where completeness allows) and **preserve / freeze** all outputs (artifacts + registry rows + audit log of versions).  
4. **Only after** outputs are frozen, compare results against locked Plans / expected **qualitative** behavior (completeness gates, Missing≠RED, FACT→REVIEW, soft-missing ORANGE ceiling, no BUY/SELL/weights, provenance present).  
5. Document whether any **hidden ticker-specific behavior** or **overfitting** to UAT names is suspected.  
6. Do **not** require a predetermined GREEN / ORANGE / RED (or any inside-color) result for held-out names.  
7. Honest **INCOMPLETE** / **REVIEW_REQUIRED** (and other outside-color states) is **acceptable** when supported by missing or ambiguous evidence — inventing color to look “complete” is a fail.

Pressure-set names may inform selection only if they were not primary UAT accept targets; document the selection rationale.

### 3.E Artifact / registry consistency

- For sample tickers: disk CURRENT pointers vs `fa_run_registry.sqlite` CURRENT flags / version_ids / paths / hashes.  
- Drift scanner results: registry vs filesystem disagreements → artifact must win; list unrepaired drift.  
- VIEW matrix regenerable and consistent with DB scalars.  
- History immutability: version folders preserved; UAT v1 packs still present where STATUS claims preservation.  
- Final FA CURRENT + `final_fa_versions/` align with registry Final FA rows; `uat_status=accepted` on CURRENT only (history untouched).

### 3.F Provenance / hardcode / skip / xfail checks

| Check | Pass criteria (draft) |
|-------|------------------------|
| Provenance | Material metrics cite source/lineage fields; CFS recon residual explained |
| No ticker hardcodes | Evaluate/pipeline paths free of UAT-only special cases (grep + review) |
| No silent skips | Missing data → UNKNOWN/NOT_DISCLOSED/INCOMPLETE — not fabricated |
| Pytest hygiene | xfails/skips inventoried; known 3 S8 freshness fails classified (xfail vs bare fail) |
| Independence | `run_stage8` / `run_stage9` wiring status documented (not in `analyze_company`) |
| Non-goals intact | No brokerage, no BUY/SELL emitters, no watchlist ranker shipped under FA modules |

---

## 4. Acceptance criteria (draft — for future Audit auth)

Audit may be closed as **PASS** only if all hold (or waivers are **explicit user** decisions):

1. Spec locks in Plan §0 for Stages 1–9 / Final FA / Registry are reflected in behavior of CURRENT code + artifacts (no contradictory production gates).  
2. Accepted UAT companies reproduce accepted eligibility / process outcomes within documented versioning (or diffs explained + user-accepted).  
2b. Independent black-box: ≥2 held-out non-primary-UAT companies run blind-first; outputs frozen before comparison; no predetermined color required; honest INCOMPLETE/REVIEW allowed when evidence supports.  
3. Registry ↔ artifact consistency within drift policy; no unexplained CURRENT mismatch.  
4. No evidence of BUY/SELL automation, stage-level R/O/G emission, or threshold invention beyond RESEARCH_CANDIDATE labels.  
5. Known limitations catalogued (incl. 3 S8 freshness fails, soft-missing rules, independent S8/S9 runners) — none silently “fixed” or denied.  
6. Handoff pack + STATUS + CHANGELOG agree on lifecycle vocabulary for closed components.  

Audit **FAIL** if: silent hardcodes altering UAT tickers; Final FA auto-RED on FACT breaker; GREEN with soft-missing S4/S5/S7; registry rewriting artifact JSON; history deleted; or audit mutates production without auth.

---

## 5. Deliverables (when Audit is authorized)

1. Audit report markdown (pass/fail per workstream + evidence paths)  
2. Pytest inventory attachment  
3. Drift / provenance findings list  
4. Recommended follow-ups (each requiring separate auth)  
5. STATUS + CHANGELOG entries only after user acceptance of audit result  

---

## 6. Explicit non-execution banner

```
THIS DOCUMENT IS A DRAFT PLAN ONLY.
DO NOT EXECUTE the Final System Audit from handoff-pack creation alone.
DO NOT modify fa/ analytical logic, re-UAT, or “fix” S8 freshness fails under this banner.
Separate user authorization required to start Audit.
```
