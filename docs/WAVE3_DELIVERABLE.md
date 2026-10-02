# Wave 3 deliverable — A7 OE coherence / B3 post-period / B1 PPA / B2 ER5-ER8

**When:** 2026-10-02 (Europe/Istanbul)  
**Auth:** WAVE 3 SPEC LOCK + IMPLEMENTATION (Can Soganci). Findings **not** auto-closed. **STOP** for user acceptance. **NO Wave 4.**

## Proposed finding status (for acceptance — not auto-closed)

| Finding | ID | Proposed status |
|---------|----|-----------------|
| A7 OE cross-year mix | F-S8-BASE-PERIOD-MIX-01 | **RESOLVED_CANDIDATE** |
| B3 post_period honesty | F-S8-POST-PERIOD-01 (B3) | **RESOLVED_CANDIDATE** |
| B1 PPA semantic | F-SEM-PPA-01 (B1) | **RESOLVED_CANDIDATE** |
| B2 ER5/ER8 legal | F-S9-ER5-PRIMARY-01 (B2) | **RESOLVED_CANDIDATE** |
| A1 DE debt | F-MAP-DE-DEBT-01 | **PARTIAL/OPEN** (outside W3 — unchanged) |

## 1. SPEC files changed

- `docs/WAVE3_SPEC_DECISIONS_ER5_ER8_v1.md` (+ mirror `03_Fundamental/WAVE3_SPEC_DECISIONS_ER5_ER8_v1.md`) — **SD-W3-ER5 / SD-W3-ER8 SPEC_LOCKED**
- `03_Fundamental/STAGE_9_EXTERNAL_RISK_PLAN_v1.md` — thin cite SD-W3-ER5/ER8 in §0.D / §0.G / §0.I + doc control
- `03_Fundamental/STAGE_9_EXTERNAL_RISK_DECISION_PASS_v1.md` — thin cite after §4 ER8 lock + doc control

## 2. Code files changed

- `fa/stage8/normalization.py` — A7 period-coherent OE (median of per-year OCF−CapEx; lineage keys; no cross-year mix)
- `fa/stage8/market_data.py` — B3 `detect_material_post_period_events` + CS freshness honesty (`empty ≠ proven none`)
- `fa/stage8/evaluate.py` — auto-detect post-period when caller omits; S8-S3 evidence_status
- `fa/stage5/semantic.py` — B1 contextual PPA (reject Precision Agriculture segment acronym)
- `fa/stage6/semantic.py` — B1 same PPA disambiguation on `acquisition_context`
- `fa/stage9/semantic.py` — B2 multi-hit ER5 topics; FTC/settlement/right-to-repair patterns; primary-legal tighten
- `fa/stage9/evaluate.py` — ER5 multi-issue named facts; ER8 thesis-link promotion gate (SD-W3-ER8)
- `tests/fa/test_wave3_external_coherence.py` — new (16 tests)
- `PROJECT_STATUS.md`, `CHANGELOG.md` — thin Wave 3 notes

## 3. Tests + results

| Suite | Result |
|-------|--------|
| Focused Wave 3 | **16 passed** |
| Relevant Stage 8/9 + Final + S5/S6 | **83 passed** |
| Full `tests/fa` | **404 passed**, 1 skipped |

## 4. Held-out matrix

See `audit/retests/wave3_external_coherence_v1/W3_REGRESSION_MATRIX.md` (+ `pre_fix/`, `post_fix/`).

| Ticker | Key post-W3 result |
|--------|-------------------|
| DE | B1 PPA FP cleared; B2 FTC/settlement surfaced + TB_REG_SWORD active; Final GREEN→REVIEW_REQUIRED |
| INTU | A7 OE 6032→6123M; B3 empty≠none honesty; B2 named legal + TB_REG; Final→REVIEW_REQUIRED |
| COST | A7 OE 6629→6745M (=fcf_like); B3 searched_none_material; Final ORANGE |
| DHR | A7 OE 5305→5296M; B3 Masimo acq+debt events_found; S9 REGULATORY_MATERIAL (no auto TB_REG — thesis link not forced); Final ORANGE |
| AZO | A7 coherent; B3 share buyback flagged; Final GREEN |

Phase 2 freezes and production fa_data/Registry **not** mutated. Same 2026-09-30 price baseline.

## 5. Downstream S8 / S9 / Final diffs (W3-attributable)

- **S8 valuation inputs (A7):** OE bases period-aligned (INTU/DHR/COST numeric deltas above). OCF/FCF-like methodology otherwise unchanged.
- **S8 freshness (B3):** post_period_events + evidence_status; CS statement-date bases unchanged; `material_stale_cs_risk` when events found.
- **S9 (B2):** DE/INTU/DHR gain `S9_HFA_REGULATORY_MATERIAL`; DE/INTU gain active `TB_REG_SWORD` + `S9_HFA_THESIS_BREAKER_ACTIVE` when thesis-linked; multi-issue ER5_LEGAL_* bullets.
- **Final FA:** DE GREEN→REVIEW_REQUIRED (eligible False); INTU ORANGE→REVIEW_REQUIRED; COST/DHR/AZO final_state unchanged vs seal colors at headline.

## 6. Proposed statuses

A7 **RESOLVED_CANDIDATE** · B3 **RESOLVED_CANDIDATE** · B1 **RESOLVED_CANDIDATE** · B2 **RESOLVED_CANDIDATE** · A1 remains **PARTIAL/OPEN**.

## 7. New finding / ambiguity

- Stage 6 offline semantic runner yielded 0 filing hits in this isolated root (retrieval/meta); B1 validated via Stage 5 retest + unit positive/negative fixtures — not treated as new product defect.
- DHR has REGULATORY_MATERIAL without auto TB_REG promotion (SD-W3-ER8 ambiguous-link path working as designed).
- B3 general thresholds ($500M acq / 10% or $1B debt / 1% shares) are RESEARCH_CANDIDATE calibration defaults — not ticker hardcodes; may need future tuning (not Wave 4 here).

## STOP

Await user acceptance. Do **not** start Wave 4. Do **not** auto-close findings. No overall audit PASS/FAIL.
