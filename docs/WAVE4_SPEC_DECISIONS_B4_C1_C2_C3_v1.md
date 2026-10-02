# Wave 4 Spec Decisions — B4 Disruption Wording / C1 Dual-Series / C2 Duration / C3 Growth Basis — v1

**Date:** 2026-10-02 (Europe/Istanbul)  
**Status:** **SPEC_LOCKED** (user authorized Wave 4 SPEC lock + implementation)  
**Scope:** Thin lock for B4 / C1 / C2 / C3. No Wave 5. No W1–W3 reopen. No A1 fix. No Market Price/Stooq. No historical S8 freshness. No production CURRENT/Registry mass regen. No overall audit PASS/FAIL. No BUY/SELL/scoring. No ticker hardcodes.  
**Companions:** Stage 9 / Stage 2 / Stage 4 / Stage 6 Plan §0 thin cites; `FUNDAMENTAL_DATA_ARCHITECTURE_v1.md`; audit `ROOT_CAUSE_CLAUDE_BATCH_BC.md` (B4, C1–C3)

---

## SD-W4-B4 — Archetype/evidence-conditioned disruption wording

**APPROVED (existing SPEC enough — implement wording honesty):**
1. Disruption monitor/breaker templates must be **archetype- and evidence-conditioned**.
2. Do **NOT** paint every issuer with generic **fintech / payments / platform / multi-homing / attack-surface** diction from a weak universal template.
3. Keep legitimate fintech/payments/network language **when supported** (PRIMARY A3, payments/network traits, or semantic excerpts with fintech/payments/multi-homing/financial-technology substance).
4. Non-supported industries use **generic substitute / mechanism** wording (no fintech noun phrase).
5. Substance bar unchanged (mechanism + exposure + attacker economics).

**NOT authorized:** ticker hardcodes; Stage 9 philosophy redesign; scores; auto-close findings.

**Regression examples only (never special branches):** DE / DHR / AZO (must not emit unsupported `fintech`); INTU/V may retain fintech when evidence/archetype supports.

---

## SD-W4-C1 — Dual-series honesty / comparability breaks (spin / continuing-ops)

**APPROVED:**
1. Preserve **AS-REPORTED** series **unchanged** (never overwrite).
2. If **authoritative continuing-ops / recast** is disclosed in structured/accepted evidence → emit a **separate COMPARABLE companion** series; never overwrite as-reported.
3. If continuing-ops/recast is **not** disclosed/available → **NO synthesize / auto-recast / model-created reconstruction** → surface **COMPARABILITY_BREAK** / honesty flag.
4. Trend / growth / ROIC / valuation paths that **cross** a break must **know which series** they use and carry the break label (not silent clean YoY).
5. No model-created reconstruction of pre-spin continuing-ops levels.

**NOT authorized:** silent overwrite of as-reported; invented recast math; ticker hardcodes; mass Registry rewrite.

**Regression example only:** DHR / Veralto spin cliff FY2022→FY2023 — flag break; do not invent continuing-ops history.

---

## SD-W4-C2 — Duration disclosure (52-/53-week honesty)

**APPROVED:**
1. Preserve **reported** period values unchanged.
2. Persist **`duration_days`** (from `period_start`/`period_end` when available).
3. Flag **unequal-duration** comparisons (e.g. 53-week vs 52-week YoY).
4. **NO** auto-normalize 53→52.
5. **NO** synthetic week-adjusted values.
6. Calcs may use reported figures; **consumers must see duration** / unequal-duration honesty.

**NOT authorized:** week-adjusted synthetic metrics; ticker hardcodes; silent length normalization.

**Examples only:** COST FY2023, AZO FY2024, DE FY2025 (371-day / ~53-week class).

---

## SD-W4-C3 — Stage 2 revenue growth basis honesty (QoQ vs YoY)

**APPROVED:**
1. Keep existing **QoQ / sequential prior-period** math.
2. Expose it as **`revenue_growth_qoq`** (or equally unambiguous name) with **explicit basis**.
3. Add **`revenue_growth_yoy`** companion when a valid prior-year same-shape period exists.
4. **NO** silent redefine of QoQ → YoY.
5. **NO** new Stage 2 gate from missing YoY.
6. Any alias of `revenue_growth` must make the **basis explicit** (label / basis field).

**NOT authorized:** changing WC stress gates solely for missing YoY; ticker hardcodes; presenting unlabeled growth as FY YoY.

**Example only:** DE −5.69% = Q3 vs Q2 sequential label/basis (not FY YoY).

---

## Implementation order (LOCKED)

Prefreeze → **B4 → C3 → C2 → C1** → focused tests → held-out isolated retest → UAT non-regression → propose statuses → **STOP** for user acceptance.

Propose only **UAT_ACCEPT_CANDIDATE** or **UAT_BLOCKED** — do **not** mark Wave 4 UAT_ACCEPTED. Do **not** auto-close findings.

---

## Authority

User: Can Soganci — 2026-10-02 — **AUTHORIZE WAVE 4 SPEC LOCK + IMPLEMENTATION + REGRESSION + UAT** for Investment Intelligence.  
Wave 3 ACCEPTED/CLOSED. Out of scope: new wave beyond W4 deliverable; W1–W3 reopen; A1 fix; Market Price/Stooq; historical S8 freshness; production CURRENT/Registry mass regen; overall audit PASS/FAIL; BUY/SELL/scoring; ticker hardcodes; auto-close findings.

**STOP after Wave 4 deliverable for user acceptance.**
