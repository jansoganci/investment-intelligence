# 03 — FA Stages 1–9 (handoff)

**Evidence-only.** Each stage: purpose, core questions, methodology, outcomes, handoffs, UAT companies, final status, known non-blocking limitations.  
**Lifecycle terms preserved.** No BUY/SELL. Spec status on Plans may still say SPEC_LOCKED for design freeze even when component is DONE / UAT_ACCEPTED.

**Canonical Plans:** butterbear `03_Fundamental/STAGE_*_PLAN_v1.md` (or `STAGE_1_GATES_v1.md`). **Plan §0 wins** where companions conflict.  
**Code:** `/workspace/investment_intelligence/fa/stage{N}/`  
**UAT:** `/workspace/investment_intelligence/fa_data/uat/`

---

## Stage 1 — Gates 0–2 (Understand + Ownership Thesis)

| Field | Content |
|-------|---------|
| **Final status** | **DONE** (KO Stage 1 UAT accepted 2026-09-14) |
| **Canonical** | `STAGE_1_GATES_v1.md`; Rulebook §13; `FA_STAGE_1_IMPLEMENTATION_STATUS_v1.md` |
| **Purpose** | Qualitative spine **before** financial Stage 2+: Gate 0 unit of analysis; Gate 1 circle of competence; Gate 2 durable ownership thesis (**not** buy; valuation = Stage 8). |
| **Core questions** | **G0-M1** operating \| FI \| commodity. **G1-M1–M8** sell/whom, job-to-be-done, revenue mix, economic engine, industry drivers, competitors, falsifiers, monitor willingness. **G2-M1–M8** customer value, durable advantage, persistence, runway, incremental capital use, capital intensity consistency, thesis failure modes, what statements must later show. SHOULD: G1-S*, G2-S*. |
| **Methodology** | Deterministic MUST/SHOULD evaluation from ownership-philosophy question set only; **no** numeric thresholds; **no** R/O/G. v1 OpCo = `operating` only; FI/commodity → TOO_HARD OOS. Thesis template + ban-list for one-liner. |
| **Possible outcomes** | `PROCEED` \| `TOO_HARD` \| `REVIEW_REQUIRED` \| `STOP_NO_THESIS`. **Not used:** RED/ORANGE/GREEN. |
| **Important handoffs** | Stage 2 **refuses** unless `process_outcome == PROCEED`. Thesis / falsifiers / monitoring vars feed Stages 4–9 + Final FA. |
| **UAT companies** | **KO** (evidence notes + payload; accepted 2026-09-14). |
| **Known non-blocking limitations** | §11.4 TBD: capital-intensive Gate 2 subtype; thesis TR vs TR+EN; Stage 2 same-session vs batch. |

---

## Stage 2 — Balance Sheet / Survival

| Field | Content |
|-------|---------|
| **Final status** | **DONE** (KO Stage 2 UAT accepted near-term fix v2, 2026-09-14) |
| **Canonical** | `STAGE_2_BALANCE_SHEET_PLAN_v1.md`; FA data architecture |
| **Purpose** | After Gate 0–2 clarity: can the **balance sheet survive adversity** without permanently impairing the franchise — *survival before poetry*. |
| **Core questions** | **S2-M1–M10:** cash+near-cash vs near-term obligations; debt+leases shape (optional vs required leverage); maturities; liquidity headroom; going-concern/covenant flags; WC stress; goodwill/intangibles footprint; restricted cash; bad-case franchise vs refinancing/dilution; proceed vs REVIEW/TOO_HARD. SHOULD S2-S1–S5 (off-BS, pension, concentration, FX trap, controllable levers). |
| **Methodology** | Hybrid Normalized + Source notes; lease-honest leverage; no live price/EV; no cigar-butt buy rules; FI OOS. |
| **Possible outcomes** | Process outcomes including proceed / review / fragility-stop language per plan & UAT (KO accepted with **PROCEED**). No R/O/G at Stage 2. |
| **Important handoffs** | Unlocks later financial stages when clean enough; WC/liquidity context to Stage 3; leverage story to Stages 6–7. |
| **UAT companies** | **KO** (`KO_stage2_uat_accepted_v2.md`). |
| **Known non-blocking limitations** | Marketable securities outside Normalized STI; SHOULD S2-S2–S5 / S2-M9 partial by design (see Stage 2 UAT pack v2). |

---

## Stage 3 — Cash Generation

| Field | Content |
|-------|---------|
| **Final status** | **SPEC_LOCKED + UAT_ACCEPTED + DONE** (2026-09-18; KO UAT v3) |
| **Canonical** | `STAGE_3_CASH_GENERATION_PLAN_v1.md` §0 |
| **Purpose** | Does the business **convert accounting earnings into real, sustainable cash**, consistent with the ownership thesis? |
| **Core questions** | **S3-M1–M8:** OCF vs NI multi-period; FCF=`OCF−CapEx` + CapEx clarity; owner-earnings / maint CapEx UNKNOWN honesty; WC converter vs sponge vs trap; distortions (factoring/SCF/M&A/asset sales/…); thesis coherence; sustainability vs CapEx holiday/one-timers; process outcome + carries. SHOULD S3-S1–S5. |
| **Methodology** | Official CFS primary; deterministic CFS→OCF recon; provenance; aggregate WC OK; states RECONCILED \| PARTIALLY_RECONCILED \| UNRESOLVED; mapping gap ≠ auto cash-quality fail; OCF\<NI alone ≠ poor cash; factoring/SCF = evidence/review not auto-fail; **no LLM arithmetic**; HITL = genuine exceptions. |
| **Possible outcomes** | `PROCEED` \| `CONDITIONAL` \| `REVIEW_REQUIRED` \| `TOO_HARD`. Evidence/review stage; **`REVIEW_REQUIRED` does not alone terminate later stages.** No R/O/G. |
| **Important handoffs** | Cash-quality concerns visible to Final FA; Stage 6 owns ROIC/reinvestment (not Stage 3). |
| **UAT companies** | **KO** (`KO_stage3_uat_accepted_v3.md`) — CFS RECONCILED residual 0; outcome REVIEW_REQUIRED non-terminating. |
| **Known non-blocking limitations** | Maint CapEx UNKNOWN without disclosure; mixed payables CF / deferred revenue may stay null when aggregate WC reconciles; REVIEW_REQUIRED exception queue (factoring/SCF/contingent consideration materiality) by design. |

---

## Stage 4 — Growth Quality / Runway

| Field | Content |
|-------|---------|
| **Final status** | **DONE / UAT_ACCEPTED** (component 2026-09-29); Plan §0 SPEC_LOCKED design freeze |
| **Canonical** | `STAGE_4_GROWTH_QUALITY_PLAN_v1.md` §0; Research + Benchmark companions |
| **Purpose** | Is growth **real, economically valuable, and capable of continuing** — and does evidence support Gate 2 / G2-M4 runway? |
| **Core questions** | MUST spine **S4-M*** (incl. decomposition, runway confidence, thesis coherence, process outcome S4-M8). Drivers BD*; archetypes **A1–A11** (ONE PRIMARY + SECONDARY_TRAITS). Benchmark labels with WHY. |
| **Methodology** | Deterministic exhibits + semantic Notes/MD&A; decomposition tags FACT \| COMPANY_EXPLANATION \| MODEL_INFERENCE; runway confidence HIGH\|MEDIUM\|LOW\|UNKNOWN (**not a score**); **Benchmark ≠ hard gate**; NC* bands **RESEARCH CANDIDATE / NOT LOCKED**; FP catalogue = tags not auto-fails; NON-TERMINATING default; FI OOS. |
| **Possible outcomes** | `PROCEED` \| `CONDITIONAL` \| `REVIEW_REQUIRED` \| `TOO_HARD`. Context tags e.g. `MATURE_FRANCHISE_OK` ≠ process outcome. |
| **Important handoffs** | Archetype/traits reused by Stages 5–8; growth concerns carry to Final FA; ROIC owned by Stage 6 (BD9 observational only). |
| **UAT companies** | **KO** (mature franchise) + **ROP** (acquisitive compounder). Component accept `STAGE4_component_uat_accepted.md`. |
| **Known non-blocking limitations** | NC* NOT LOCKED; organic/acquired/CC/volume may stay NOT_DISCLOSED; BD6 UNKNOWN without Stage 1; CapEx Normalized may be null; cosmetic contiguous display-label nuance. |

---

## Stage 5 — Margins / Business Economics

| Field | Content |
|-------|---------|
| **Final status** | **DONE / UAT_ACCEPTED** (2026-09-29); Plan §0 SPEC_LOCKED |
| **Canonical** | `STAGE_5_BUSINESS_ECONOMICS_PLAN_v1.md` §0 |
| **Purpose** | Understand **cause + durability** of economics — not “are margins high?” High ≠ pass; thin ≠ fail. |
| **Core questions** | **BE1–BE8** (no BE9 ROIC); pricing posture STRONG\|MODERATE\|WEAK\|MIXED\|UNKNOWN\|N/A (**evidence-of-claim only**; STRONG≠PROCEED; WEAK≠fail); incremental OM descriptive ≠ ROIIC; durability confidence; thesis coherence; process outcome. |
| **Methodology** | Reuse Stage 4 archetype; Benchmark ≠ hard gate; closed context tags incl. `SCALE_ECONOMIES_SHARED_OK` (evidence bar; not free excuse / not skip Stage 6); GM/OP/IM bands NOT LOCKED; NON-TERMINATING. |
| **Possible outcomes** | `PROCEED` \| `CONDITIONAL` \| `REVIEW_REQUIRED` \| `TOO_HARD`. |
| **Important handoffs** | Economics concerns → Stage 6 / Final FA; SES does not replace ROIC analysis. |
| **UAT companies** | **KO** + **V (Visa)**. `STAGE5_component_uat_accepted.md`. |
| **Known non-blocking limitations** | BE8 UNKNOWN without Stage 1; GM/COGS NOT_DISCLOSED for payments; take-rate may stay null; numeric bands NOT LOCKED. |

---

## Stage 6 — ROIC / Reinvestment

| Field | Content |
|-------|---------|
| **Final status** | **DONE / UAT_ACCEPTED** (2026-09-29); Plan §0 SPEC_LOCKED |
| **Canonical** | `STAGE_6_ROIC_REINVESTMENT_PLAN_v1.md` §0; Capital Treatment Decision Pass companion |
| **Purpose** | How effectively does the company convert invested capital and **incremental** reinvestment into durable operating returns? Can it keep reinvesting meaningful capital attractively? **Not** “is ROIC high?” |
| **Core questions** | NOPAT/IC/ROIC/incremental exhibits; dual ROIC when required (acquisition-inclusive PRIMARY + tangible companion); reinvestment composition + runway; CapEx productivity; FP-R catalogue; RC1–RC8 benchmark labels; thesis capital-destination coherence; **`S6_H7_*` factual handoff flags** to Stage 7. |
| **Methodology** | IOM (Stage 5) ≠ ROIIC; Benchmark ≠ hard gate; numeric ROIC/ROIIC/WACC bands NOT LOCKED; no forced maint CapEx invention; NON-TERMINATING + REVIEW_REQUIRED + Stage 7 flag pattern; FI OOS. |
| **Possible outcomes** | `PROCEED` \| `CONDITIONAL` \| `REVIEW_REQUIRED` \| `TOO_HARD`. |
| **Important handoffs** | `S6_H7_*` → Stage 7 (evidence only, no management grade); capital quality → Final FA. |
| **UAT companies** | **ROP** + **V**. `STAGE6_component_uat_accepted.md`. |
| **Known non-blocking limitations** | CapEx/AP/NIBOL gaps; maint/growth CapEx NOT_DISCLOSED; runway may stay UNCLEAR capital-light; thesis absence → coherence/RC8 UNKNOWN. |

---

## Stage 7 — Management / Capital Allocation

| Field | Content |
|-------|---------|
| **Final status** | **DONE / UAT_ACCEPTED** (2026-09-29); Plan §0 SPEC_LOCKED |
| **Canonical** | `STAGE_7_MANAGEMENT_ALLOCATION_PLAN_v1.md` §0; Decision Pass + Research |
| **Purpose** | Does management allocate capital, design incentives, communicate, and execute in a way that supports long-term owner value? |
| **Core questions / lenses** | **MG1** Capital Allocation Coherence; **MG2** Opportunity recognition & response; **MG3** Acquisition discipline; **MG4** Shareholder distributions (buybacks+dividends as one system); **MG5** Debt as allocation tool (not Stage 2 solvency retest); **MG6** Incentive alignment (CD&A MVP); **MG7** Ownership/governance context (neutral factual); **MG8** Communication & execution credibility; **MG9** Succession / key-person. |
| **Methodology** | Consume Stage 6 economics/flags; semantic-first proxy/CD&A; typed FACT/GUIDANCE/CLAIM/INFERENCE; NON-TERMINATING; no scores/colors; numeric pay/buyback/ownership bands NOT LOCKED; dual-class/founder neutrality by design. |
| **Possible outcomes** | `PROCEED` \| `CONDITIONAL` \| `REVIEW_REQUIRED` \| `TOO_HARD`. |
| **Important handoffs** | `S7_H8_*` vocabulary deferred to Stage 8; carries to Final FA; provenance audit example: META. |
| **UAT companies** | **ROP** + **META**. `STAGE7_component_uat_accepted.md`. |
| **Known non-blocking limitations** | Shallow CD&A/TOC → MIXED; MG8 execution thin → MIXED; A11 LOW = monitor only; empty `S6_H7_*` ≠ clean bill; S7-S4 prior-proxy SHOULD partial; entity_name null cosmetic. |

---

## Stage 8 — Valuation / IV / Margin of Safety

| Field | Content |
|-------|---------|
| **Final status** | **DONE / UAT_ACCEPTED** (2026-09-29); Plan §0 SPEC_LOCKED |
| **Canonical** | `STAGE_8_VALUATION_PLAN_v1.md` §0; Decision Pass + Research |
| **Purpose** | What expectations are embedded in price; what **IV range** is defensible; how much valuation risk / MoS **evidence** exists — **not** P/E-cheap / one fair value / BUY-SELL. |
| **Core lenses** | **VA1** Market-value bridge & freshness; **VA2** Normalized base honesty; **VA3** IV range; **VA4** Reverse DCF / embedded expectations; **VA5** Multiples & historical context; **VA6** Capital structure / dilution bridge; **VA7** MoS evidence (no universal % gate); **VA8** Uncertainty & method disagreement. |
| **Methodology** | Session-aware freshness; FCFF + dual-terminal CROSS-CHECKS (**never averaged**); reverse DCF first-class; Method E hierarchy; RESEARCH_CANDIDATE paths for some growth/discount numerics; NON-TERMINATING; independent `run_stage8` (not in `analyze_company`). |
| **Possible outcomes** | `PROCEED` \| `CONDITIONAL` \| `REVIEW_REQUIRED` \| `TOO_HARD`. Price≫envelope = descriptive — **not** SELL. |
| **Important handoffs** | `S8_H9_*` → Stage 9 / Final FA; valuation packet consumed by Final FA (not redone). |
| **UAT companies** | **ROP** + **NVDA**. `STAGE8_component_uat_accepted.md`. |
| **Known non-blocking limitations** | Forward DCF RESEARCH_CANDIDATE / regime-mismatch → VA3/VA7 MIXED; reverse-DCF ceiling may be lower_bound_only; A4 mid-cycle residual vs A8/A9 mid_cycle_mandatory; acquisitive dual exhibits; dilution/split mix; CapEx nulls on older FYs; selective peers N/A; heuristic MVP; **`run_stage8` not in `analyze_company`**. **Also:** **3 known Stage 8 freshness/clock pytest failures** (non-blocking; not fixed under current auth) — see Status docs. |

---

## Stage 9 — Industry / Competition / Macro / External Risk

| Field | Content |
|-------|---------|
| **Final status** | **DONE / UAT_ACCEPTED** (2026-09-29); Plan §0 SPEC_LOCKED |
| **Canonical** | `STAGE_9_EXTERNAL_RISK_PLAN_v1.md` §0; Decision Pass + Research |
| **Purpose** | Industry structure; moat durability under external pressure; disruption / concentration / regulatory / geopolitical / macro context; compact thesis breakers — prepare ≠ predict. |
| **Core lenses** | **ER1** Industry structure; **ER2** Moat durability stress (Gate2/S1/S5 as hypotheses only — no S5 redo / no S1 restatement); **ER3** Disruption mechanism; **ER4** Concentration map; **ER5** Regulatory/policy envelope; **ER6** Geopolitical exposure; **ER7** Macro/cycle context; **ER8** Thesis breakers & monitoring (3–7, not giant register). ER9 dropped/merged. |
| **Methodology** | Evidence labels; HFA packaging for Final FA; NON-TERMINATING; no averaged external-risk score; independent `run_stage9`. |
| **Possible outcomes** | `PROCEED` \| `CONDITIONAL` \| `REVIEW_REQUIRED` \| `TOO_HARD`. |
| **Important handoffs** | `S9_HFA_*` (incl. thesis-breaker FACT) → Final FA; FACT breaker → Final FA REVIEW (not auto-RED). |
| **UAT companies** | **V (Visa)** + **RIO**. `STAGE9_component_uat_accepted.md`. |
| **Known non-blocking limitations** | Thin prior-stage CURRENT on some UAT names (honest gaps); IFRS mapping sparse; Baowu share undisclosed ≠ clean diversification bill; product/distribution unknown; heuristic MVP; ER4 `geo=high` = demand concentration ≠ GEO_MATERIAL; **`run_stage9` not in `analyze_company`**. |

---

## Cross-stage standing rules (documented)

1. Stages 1–9 analytical logic preserved when later components ship (Final FA / Registry auth: **untouched**).  
2. No scores / weights / R-O-G inside Stages 1–9 (color emission authorized at Final FA only).  
3. FI HARD OOS on OpCo stage contracts.  
4. Human-in-the-loop = exception / judgment queue, not routine arithmetic.
