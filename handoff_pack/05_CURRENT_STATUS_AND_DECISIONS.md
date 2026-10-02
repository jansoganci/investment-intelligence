# 05 — Current Status and Decisions

**Canonical current truth** | As of: **2026-10-01 (Europe/Istanbul)**  
**Sources:** `PROJECT_STATUS.md` (II + `00_System`), `CHANGELOG.md`, component UAT accepts.  
Do not invent. No BUY/SELL.

---

## 1. Where we are now

| Scope | Status |
|-------|--------|
| FA Stages **1–9** | **DONE / UAT_ACCEPTED** |
| **Final FA** synthesis | **DONE / UAT_ACCEPTED** |
| Company FA History / **Run Registry** | **DONE / UAT_ACCEPTED** |
| Research Intelligence (core + Emtia) | `UAT_ACCEPTED` |
| Dragonomi RI adapter | `PLANNED` / deferred |
| Technical / Portfolio / Watchlist ranking | `PLANNED` — **do not start under this closure** |
| **Final System Audit** | **Next planned step** — separate auth; **not started** |

**One-line stop:** Stages 1–9 + Registry + Final FA complete.

---

## 2. Continue here (ordered)

1. **Final System Audit** — next planned step (separate authorization; draft plan in `06_FINAL_SYSTEM_AUDIT_PLAN.md` — **do not execute** under handoff-only auth).  
2. Do **not** start TA / watchlist / portfolio under this closure; Stages 1–9 preserved; do **not** fix the **3 known Stage 8 freshness pytest fails** under Final FA / Registry closure auth.  
3. Final FA — **closed** (DONE / UAT_ACCEPTED).  
4. Registry — **closed** (DONE / UAT_ACCEPTED).  
5. Separate/open: **Dragonomi** RI adapter.

---

## 3. Known Stage 8 freshness test issue

**Fact (STATUS / Final FA accept):** Full `tests/fa` at Final FA closure = **343 passed / 3 failed**. Failures = **known Stage 8 freshness / clock / STALE** issues.  

**Treatment:** **Non-blocking.** Explicitly **not fixed** under Final FA / Registry UAT closures. Unrelated to Registry correctness and Final FA §0 rules.

**Implication for Audit:** Audit plan should include freshness/provenance checks; fixing the 3 fails requires **separate** authorization (not implied by this handoff pack).

---

## 4. Major locked decisions (WHY + WHAT)

| Decision | WHAT | WHY (documented) |
|----------|------|------------------|
| Quality / moat / compounding path | Primary v1 equity framework | Avoid mixing cigar-butt into same rulebook; Gate 2 requires durable-advantage hypothesis |
| Whitelist attention layers | MI ≠ Coverage ≠ FA List ≠ Color | Broad ingest without automatic company FA / color churn |
| TOO HARD outside color | Not RED | Unevaluable ≠ bad company; may stay on Research Coverage |
| GREEN ≠ BUY | Eligibility only | Price/timing = later technical; prevents FA from becoming trade signal |
| Stage order 1→9 then Final FA | Survival/cash/growth/econ/ROIC/mgmt/val/risk then reconcile | Ownership philosophy sequence; “survival before poetry”; valuation not in Gate 2 |
| Benchmark ≠ hard gate | Labels ≠ decisions | Prevent count/percentile engines from faking objectivity |
| Numeric bands NOT LOCKED (NC*, GM/OP/IM, ROIC/WACC, MoS %) | Research candidates | User refused invented thresholds; lock only with separate auth |
| Stages 3–9 NON-TERMINATING default | Carry concerns to Final FA | Avoid mechanical pipeline kills on partial disclosure |
| Final FA = reconciliation not averaging | No stage votes/weights | Prevent false GREEN from “all PROCEED” or false RED from count(RR) |
| Soft-missing S4/S5/S7 → ORANGE max | Completeness U2 tighten | Soft gaps must not allow GREEN |
| FACT breaker → REVIEW not auto-RED | Prefer REVIEW over casual RED | Thesis falsify needs evidence + often human confirm |
| ORANGE never TA/watchlist | technical_eligible false | Soft residual ≠ technical-universe ready |
| Registry artifacts-as-truth | SQLite index only | Auditability + $0 storage; avoid JSON duplication drift |
| Plan wins over companions | Single contract | Prevent stale Decision Pass language (e.g. U2) from overriding freeze |
| No TA/watchlist under FA closure | Sequencing | Final System Audit next; capacity/ADHD |

---

## 5. Accepted UAT map (company × component)

| Component | Full UAT pair / primary | Status |
|-----------|-------------------------|--------|
| Stage 1 | KO | DONE |
| Stage 2 | KO | DONE |
| Stage 3 | KO | DONE |
| Stage 4 | KO + ROP | DONE / UAT_ACCEPTED |
| Stage 5 | KO + V | DONE / UAT_ACCEPTED |
| Stage 6 | ROP + V | DONE / UAT_ACCEPTED |
| Stage 7 | ROP + META | DONE / UAT_ACCEPTED |
| Stage 8 | ROP + NVDA | DONE / UAT_ACCEPTED |
| Stage 9 | V + RIO | DONE / UAT_ACCEPTED |
| Final FA | ROP + V (v2) | DONE / UAT_ACCEPTED |
| Registry | Registry UAT ACCEPTED | DONE / UAT_ACCEPTED |

---

## 6. Open / TBD (not invented)

- ACTIVE WATCHLIST selection method  
- Rulebook numeric/color **rule register** still largely empty (architecture + Gate 0–2 locked; stage operating rules live in Plans)  
- Ownership §11.4 (capital-intensive subtype; thesis language; Stage 2 timing)  
- FA “current” / freshness policy days-quarters definition  
- Dragonomi adapter  
- Jev / TypeSafe assessment = EXPERIMENT ONLY (`JEV_ARCHITECTURE_ASSESSMENT_v1.md`) — no integration  
- RI: automated recurring harvest; full deep-read bodies; live LLM semantic (heuristic used)  

---

## 7. Doc discipline (standing)

- `PROJECT_STATUS` = current truth only  
- `CHANGELOG` = append-only; mark superseded; do not rewrite history  
- Link evidence; do not duplicate full specs/UAT bodies into status  
- `DONE` only on explicit user acceptance
