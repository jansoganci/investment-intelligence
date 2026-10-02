# Wave 2 Spec Decisions — A1 Debt Perimeter & A4 Client Funds — v1

**Date:** 2026-10-02 (Europe/Istanbul)  
**Status:** **SPEC_LOCKED** (user accepted agent recommendations)  
**Scope:** Decision only — **does not authorize Wave 2 implementation** until separate auth  
**Companions:** Stage 2/6/8 Plan §0; `STAGE_6_CAPITAL_TREATMENT_DECISION_PASS_v1.md`; audit `ROOT_CAUSE_CLAUDE_BATCH_A.md` (A1, A4)

---

## SD-W2-A1 — Interest-bearing debt / captive finance (Deere class)

**APPROVED:**
1. Map **all disclosed interest-bearing debt components** available from companyfacts/face (ST, securitization/secured borrowings, LT, CPLTD as applicable) — do not silently publish ST-only as complete gross debt.
2. When Equipment vs Financial Services (captive) split is available, **label and exhibit dual debt / EV views**; do not pretend OpCo-only without labels.
3. If the OpCo vs FS split cannot be formed honestly → **do not invent**; surface `REVIEW_REQUIRED` / TOO_HARD on OpCo-only EV path rather than a understated single debt number.
4. Null LTD must not coerce to zero in gross_debt when other debt components or incompleteness evidence exist — mark incomplete / REVIEW.

**NOT authorized by this lock alone:** implementation; ticker hardcodes; redesign of DONE Stage 2/6/8 beyond mapping + honesty exhibits.

---

## SD-W2-A4 — Client / customer funds (Intuit class)

**APPROVED:**
1. **Exclude customer-related restricted funds** from invested-capital cash policy (matched-book / not owner free cash).
2. If customer funds **payable** is not mapped from structured tags → **do not invent** the liability; set honesty flag (`nibol_incomplete` and/or client-funds incomplete).
3. Do **not** force NIBOL inclusion of client payables without a real structured field.
4. STI mapping (A4-part1) remains a separate factual TAG_MAP fix (AFS debt securities current, etc.) — not blocked by this decision.

**NOT authorized by this lock alone:** Wave 2 code; inventing payables from narrative.

**Cross-cite (Wave 2 seal):** Stage 6 Decision Pass D4 + Plan §0.D now carry a **thin cite** of SD-W2-A4 (rule text remains here; not redesigned).

---

## Authority

User: Can Soganci — 2026-10-02 — accepted recommendations (A1 dual/consolidated labeled; A4 exclude client funds from IC + honesty flag).

**STOP — await separate Wave 2 implementation authorization.**
