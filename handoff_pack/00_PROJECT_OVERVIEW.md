# 00 — Investment Intelligence: Project Overview

**Handoff pack doc** | Evidence-only | As of: 2026-10-01 (Europe/Istanbul)  
**Audience:** Fresh AI workspace / independent reviewer  
**Constraint:** No BUY/SELL. Do not invent decisions. Uncertainty marked.

---

## 1. What this system is

**Investment Intelligence** is a personal long-term **US equity** decision system for ~12-year capital accumulation (equity sleeve only; BES / physical gold outside).

**Style (LOCKED):** Fundamental analysis selects businesses → daily technical timing controls exposure (later). Human in the loop. No live brokerage in v1.

**Identity:** Not ButterBear. Not 1-minute trading. Not live brokerage (v1). Özekşi Classic = technical module only (later).

**Workspace layout:**
| Path | Role |
|------|------|
| `/workspace/investment_intelligence/` | Production code + `fa_data/` + tests (FA/RI implementation) |
| `/workspace/butterbear/drive/transition/` | Canonical Drive docs: `00_System/`, `01_Research/`, `03_Fundamental/`, `07_Operations/` |

---

## 2. Pipeline (LOCKED)

```
Dragonomi + Emtia Defteri
  → Research Intelligence (broad ingest; flag NEW RESEARCH IDEA only)
  → STOP — no auto-promotion
Explicit Research Coverage List  [user whitelist]
  → STOP — no auto-promotion
Explicit Fundamental Analysis List  [user whitelist]
  → Gate 0–2 + Stages 2–9
     ├── TOO HARD / REVIEW REQUIRED  (outside Color Universe)
     └── RED / ORANGE / GREEN        (Fundamental Color Universe)
  → GREEN universe (uncapped)
  → ACTIVE WATCHLIST (cap 15; selection method TBD)
  → Daily Technical (later) → AL / WAIT / SAT
  → Human portfolio decision
```

**Key locks:** GREEN ≠ BUY. Market intelligence is broad; company-specific attention is whitelist-driven. Color states normally stable until new evidence.

---

## 3. Major components

| Component | Lifecycle (as of 2026-10-01) | Notes |
|-----------|------------------------------|-------|
| Research Intelligence (core + Emtia) | `UAT_ACCEPTED` | Dragonomi adapter = `PLANNED` / deferred |
| FA Data Backend (hybrid SEC + Normalized) | `UAT_ACCEPTED` | Ships with Stage 2 path |
| FA Stages 1–9 | **DONE / UAT_ACCEPTED** | Spec Plan §0 = design freeze (Plan wins) |
| Final FA Synthesis | **DONE / UAT_ACCEPTED** | First authorized color emitter |
| Company FA History / Run Registry | **DONE / UAT_ACCEPTED** | SQLite index; artifacts = analytical truth |
| Technical (daily TA) | `PLANNED` | After FA path |
| Portfolio / Verification / Messenger | `PLANNED` / modes | Architecture |
| Operations | `IN_PROGRESS` | Tracking + service log |
| **Final System Audit** | **PLANNED** (next) | Not started |

---

## 4. Lifecycle vocabulary (preserve exactly)

```
PLANNED → SPEC_LOCKED → IN_PROGRESS → IMPLEMENTED → TESTED → UAT_ACCEPTED → DONE
```

Also: `BLOCKED`, `REVIEW_REQUIRED`, `SUPERSEDED`.

**`DONE` requires explicit user final acceptance/closure.** Tests or implementation alone never auto-mark `DONE`.

**Plan wins:** For each locked stage/component, Plan §0 is the authoritative operating contract; Research / Decision Pass companions lose on conflict.

---

## 5. Standing non-goals (v1)

- Broker API / live orders  
- Auto FA on non–FA-List names; auto-promotion across whitelist layers  
- Invented numeric thresholds / scores / weights / averaged stage votes as color  
- Cigar-butt / deep-value mixed into primary quality path  
- TA / watchlist ranking / portfolio under current FA closure  
- BUY/SELL recommendations from FA stages or Final FA  

---

## 6. Where truth lives

| Kind | Canonical |
|------|-----------|
| Current board | `00_System/PROJECT_STATUS.md` (+ II `PROJECT_STATUS.md` mirror) |
| History | `CHANGELOG.md` (append-only; both trees) |
| Architecture charter | `00_System/PROJECT_TRANSITION_ARCHITECTURE_v1.md` |
| Stage / Final FA / Registry specs | butterbear `03_Fundamental/` + `00_System/COMPANY_FA_HISTORY_REGISTRY_*` |
| Code | `/workspace/investment_intelligence/{fa,ri}/` |
| UAT packs | `fa_data/uat/` |
| Registry DB | `fa_data/registry/fa_run_registry.sqlite` |

---

## 7. Current stop point (summary)

Stages 1–9 + Final FA + Registry = **DONE / UAT_ACCEPTED**.  
Known non-blocking: **3 Stage 8 freshness/clock pytest fails**.  
**Next = Final System Audit** (separate auth; not started).  
Do **not** start TA / watchlist / portfolio under this closure.

See `05_CURRENT_STATUS_AND_DECISIONS.md` and `06_FINAL_SYSTEM_AUDIT_PLAN.md`.
