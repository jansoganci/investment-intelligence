# 01 — Investment Philosophy (documented only)

**Handoff pack doc** | Evidence-only from locked System / Rulebook / Ownership Philosophy Research  
**As of:** 2026-10-01 (Europe/Istanbul)  
**Rule:** Extract only what is already documented. Do not invent personal preferences. Mark gaps under **MISSING**.

---

## Documented operating context

**Scope:** Already-established project/user context from durable project memory and Architecture/STATUS operating constraints.  
**Not** personal risk, sizing, tax, or override rules — those stay under **MISSING** below.

| Item | Documented context |
|------|--------------------|
| Age | 33 (as of 2026) |
| Horizon | ~12 years toward financial freedom / independence while continuing to work long-term |
| Investing cadence | Regular monthly investing |
| Equity sleeve | Separate from BES and physical gold (those sleeves stay outside this equity system) |
| Primary universe | US equities are the primary active equity universe (China/HK/commodities/FX = research/intelligence only in v1; Turkish equities not designed yet) |
| Style | Quality / durable business / moat / compounding (aligned with locked v1 path) |
| Fundamentals role | Fundamentals decide **WHAT** is eligible |
| Technical role | Daily technical layer **later** decides **WHEN** (enter / remain / exit) |
| GREEN | **GREEN ≠ BUY** — fundamental eligibility for timing consideration only |
| Authority | Human makes the final portfolio decision |
| Brokerage | No live brokerage execution in v1 |
| Human attention | ~10 hours/week approximate budget |
| AI/API spend | ~USD 25–30/month initially (excluding broader subscriptions) |

**How to read this pack:**
1. **Documented personal/operating context** — this section (facts of use, not invented risk limits).  
2. **Locked system philosophy** — §§1–6 below (Plans / Rulebook / Ownership Research).  
3. **Still-missing personal decisions** — §7 MISSING (do not invent).

---

## 1. Locked v1 equity path

**Source:** `OWNERSHIP_PHILOSOPHY_RESEARCH_v1.md` §11.2; `FUNDAMENTAL_FILTER_RULEBOOK_v0.md` §4; Architecture §E/J.

Primary long-term equity sleeve uses:

> **quality / durable-business / moat / compounding**

**Out of primary v1 framework (do not mix in):** Graham-style cigar-butt / deep-value / mediocre-business-at-extreme-discount.

Those may later become a separately labeled `SPECIAL SITUATION / DEEP VALUE` path. Until then: **outside** primary FA.

Gate 2 expects a hypothesized durable advantage (G2-M2). Absence of moat is **not** “cheap enough” rescue inside v1 FA.

---

## 2. Owner mindset (Stage 1 spine)

**Source:** Ownership Philosophy Research + `STAGE_1_GATES_v1.md`.

| Idea | Status |
|------|--------|
| Understand before ratio theatre (Gate 1) | LOCKED |
| Durable ownership thesis before financial depth (Gate 2) — not “buy” | LOCKED |
| Gate 0 unit of analysis: operating vs FI vs commodity | LOCKED |
| Valuation deferred to Stage 8 | LOCKED |
| Macro/cycle deferred to Stage 9 (context/risk, not thesis core) | LOCKED |
| TOO HARD ≠ RED/ORANGE/GREEN | LOCKED (§11.1) |
| Survival before poetry → Stage 2 after Gates 1–2 | SYNTHESIS locked into stage order |

**v1 OpCo path:** only `operating` takes full Stage 1→2+. `financial_institution` / `commodity` → **TOO_HARD / OOS** for v1 OpCo path.

---

## 3. Attention & universe philosophy

**Source:** Rulebook §2–3; Architecture; Ownership §11.3.

- Market intelligence is **broad**; company-specific analytical attention is **whitelist-driven**.  
- No auto-promotion: MI → Coverage → FA List → Color Universe requires **explicit user approval**.  
- **No fixed hours-per-company rule.** Listed → follow per list. Not listed → no automatic company FA.  
- **GREEN ≠ BUY.** GREEN = fundamentally eligible for technical-universe consideration.  
- **ACTIVE WATCHLIST ≠ GREEN.** Cap **15** LOCKED; selection method **TBD**.  
- FA **color** states **normally remain stable** until new evidence (earnings, guidance, material events). News may flag research ideas without churning R/O/G.

---

## 4. Evidence & automation philosophy (operating)

Documented across Stage Plans §0 and Data Architecture:

| Principle | Meaning |
|-----------|---------|
| Automate research first; escalate uncertainty second | Human = exception queue, not default path |
| Code does math; LLM does semantic; human reviews ambiguity | No LLM arithmetic; no vibe color |
| Official filings = SoR; aggregators never sole evidence | Hybrid Source + Normalized |
| Missing ≠ poor fundamentals / Missing ≠ RED | Explicit UNKNOWN / NOT_DISCLOSED states |
| Benchmark ≠ hard gate | Labels are evidence, not decisions (Stages 4–8) |
| NON-TERMINATING by default (Stages 3–9) | Concerns carry to Final FA; stage alone does not kill pipeline |
| Final FA = reconciliation, not averaging | No stage voting / scorecards / weights |
| Prefer REVIEW over casual RED | FACT breaker → REVIEW until cleared; RED only if thesis falsified with evidence |
| `technical_eligible` | true iff GREEN and no open `blocks_color` queue items |
| ORANGE never TA / never watchlist | Inside color; soft residual; not unevaluable dump |

---

## 5. Investor map (documented contribution lanes)

**Source:** Ownership Philosophy Research §2–3, §8 (SOURCE-DERIVED / SYNTHESIS labeled there).

| Lane | Voices (as documented) |
|------|------------------------|
| Competence / owner mindset / moat | Buffett, Munger, Lynch, Pabrai |
| Quality = cash ROCE + reinvestment | Terry Smith |
| Customer value / scale shared / margin optics | Nick Sleep |
| Runway / integrity | Fisher |
| Downside / checklist | Pabrai |
| Valuation / MoS (Stage 8) | Graham, Klarman, Greenblatt, Buffett, Marks |
| Risk / expectations / cycle (Stage 9) | Marks; Dalio weak for “why own this one business” |

**Do not average disagreements** (quality-first vs cheapness-first; Sleep low-margin vs high-margin screens). System chose quality-first + valuation later.

---

## 6. False-positive patterns (catalogue philosophy)

**Source:** Ownership Philosophy §7 (and stage FP catalogues). Examples documented: high margins/no moat; high ROIC/shrinking market; growth via dilution; FCF from underinvestment; CAPEX without incremental returns; commodity windfall; acquisitive EPS compounding; “cheap” with leverage; fake network effects.

These are **tagging / monitoring philosophies**, not automatic hard fails in stage specs.

---

## 7. MISSING / insufficient personal philosophy (explicit)

The corpus locks **system** philosophy (quality path, gates, whitelist, GREEN≠BUY). The **Documented operating context** section above does **not** fill personal risk/sizing/tax/override decisions. The following remain **not** sufficiently documented — do **not** invent:

1. **Personal risk tolerance / max drawdown / ruin rules** for the equity sleeve.  
2. **Position sizing / concentration / number of holdings** policy (ACTIVE WATCHLIST selection method remains **TBD**; portfolio layer `PLANNED`).  
3. **Entry/exit rules beyond** “FA then TA” and “respect technical SAT; re-enter next AL if still GREEN, FA current, no material new event” (Architecture) — no detailed personal playbook.  
4. **Tax / domicile / currency of account** constraints.  
5. **Time-budget operating ritual** beyond ~10 h/week target and “no fixed hours-per-company.”  
6. **When Can personally overrides** machine ORANGE/REVIEW/GREEN (HITL judgment criteria beyond Final FA queue design).  
7. **RED / ORANGE / GREEN entry criteria** as filled numeric/rule statements — Rulebook §5 still **TBD** at rule-register level (Final FA Plan §0 now defines operating color semantics for synthesis; Rulebook register still sparse).  
8. **§11.4 unresolved:** (a) capital-intensive Gate 2 subtype? (b) thesis card always TR vs TR+EN? (c) Stage 2 same-session vs batch after Gate 2?  
9. **FA review freshness / “FA current” definition** (days/quarters) — Rulebook TBD.  
10. **Special-situation / deep-value path** — explicitly out of scope; no personal criteria written.  
11. **Commodity / FI investing philosophy** — OOS for v1 OpCo; no personal module locked.

If a future workspace needs personal philosophy beyond the above locks, obtain explicit user decisions — do not infer from ticker UAT outcomes.
