# Wave 3 Spec Decisions — ER5 Legal Facts & ER8 Thesis-Linked Promotion — v1

**Date:** 2026-10-02 (Europe/Istanbul)  
**Status:** **SPEC_LOCKED** (user authorized Wave 3 SPEC lock + implementation)  
**Scope:** Thin lock for Stage 9 ER5/ER8 (B2). Companions: A7 OE period coherence, B3 post-period honesty, B1 PPA semantic (implementation defects; Plan reopen NOT required).  
**Companions:** `STAGE_9_EXTERNAL_RISK_PLAN_v1.md` §0; `STAGE_9_EXTERNAL_RISK_DECISION_PASS_v1.md`; audit `ROOT_CAUSE_CLAUDE_BATCH_BC.md` (B1/B2/B3), `ROOT_CAUSE_CLAUDE_BATCH_A.md` (A7)

---

## SD-W3-ER5 — Material named legal/regulatory facts (multi-issue)

**APPROVED (implement as written):**
1. Surface **ALL MATERIAL, NAMED** legal/regulatory facts with **primary evidence** (agency/action/order/judgment/settlement identity + provenance/source/date/status).
2. Do **NOT** force a singular “primary” when several exist — preserve each separately.
3. No collapse to generic Risk Factors / “subject to antitrust laws” boilerplate as the sole ER5 surface when named facts exist in ingested filings.
4. No invented numeric rank / headline-count score.
5. Closed / settled matters may remain visible when still thesis-, economic-, or reputationally relevant (label status honestly).

**NOT authorized:** ticker hardcodes; universal legal-risk threshold; Stage 9 philosophy redesign; auto-close findings.

---

## SD-W3-ER8 — Compact thesis-breaker set; legal promotion gate

**APPROVED (implement as written):**
1. Keep compact **3–7** thesis-breaker set (existing ER8 lock unchanged in spirit).
2. Promote an ER5 legal/regulatory issue into ER8 **ONLY** with a **supported link** to ownership thesis / falsifiers / moat / operating economics.
3. No new scoring; no universal legal-risk threshold.
4. If thesis link is **materially ambiguous** → do **not** auto-promote; preserve ER5 evidence; `REVIEW_REQUIRED` / HITL as appropriate.
5. HITL = **exception path**, not default.

**Cross-cite:** Stage 9 Decision Pass §4 + Plan §0.D carry a **thin cite** of SD-W3-ER5 / SD-W3-ER8 (rule text lives here; not redesigned).

---

## Implementation companions (no Plan reopen)

| ID | Fix | Spec reopen? |
|----|-----|--------------|
| **A7** | Stage 8 OE/OCF−CapEx **period coherence** only — same compatible fiscal period for components; preserve lineage; no silent cross-year; if no compatible pair → missing/uncertain (do not substitute another year). Locked OE formula/aggregation methodology unchanged aside from pairing. | NO |
| **B3** | General material **post-period events** mechanism — historical CS bases stay on statement date; events = separate evidence; empty list must **not** imply search established “none” when evidence insufficient; preserve event date/source/type/relationship; explicit uncertainty. DHR/Masimo = regression example only. | NO |
| **B1** | Bare `PPA` ≠ auto Purchase Price Allocation — require acquisition/accounting context; “Production & Precision Agriculture (PPA)” must not hit; keep real acquisition PPA; no ticker hardcodes. | NO |
| **B2** | Implement SD-W3-ER5 / SD-W3-ER8. DE/FTC right-to-repair = regression example only — never special branch. | Thin cite only |

---

## Authority

User: Can Soganci — 2026-10-02 — **AUTHORIZE WAVE 3 SPEC LOCK + IMPLEMENTATION** for Investment Intelligence.  
Out of scope: Wave 4; reopen W1/W2; Stage 8 Market Price changes; A1 DE debt fix; historical S8 freshness unless required by W3; ticker hardcodes; auto-close findings; overall audit PASS/FAIL; production CURRENT/Registry mass regen.

**STOP after Wave 3 deliverable for user acceptance.**
