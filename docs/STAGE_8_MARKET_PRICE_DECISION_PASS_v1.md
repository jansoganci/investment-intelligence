# Stage 8 — Market Price Decision Pass — v1

**Folder:** `03_Fundamental`  
**Date:** 2026-10-02 (Europe/Istanbul)  
**Status:** **SPEC_LOCKED companion** (2026-10-02) — user-authorized lock of Stage 8 Market Price v1 contract only  
**Lifecycle:** design freeze for **market-price ingest contract** — **not** IMPLEMENTED / TESTED / UAT_ACCEPTED / DONE  
**Canonical operating home:** `STAGE_8_VALUATION_PLAN_v1.md` **§0.T** (Plan wins on conflict)  
**Companions:** `STAGE_8_VALUATION_PLAN_v1.md` §0.H (session-aware freshness — preserved); `STAGE_8_VALUATION_DECISION_PASS_v1.md` D2 (freshness classes — preserved)  
**Does not authorize:** implementation; adapter code; `yfinance`/Stooq wiring; Stage 8 analytical logic changes; mapping fixes; held-out re-runs; overall audit PASS/FAIL  
**Scope:** US OpCo equities v1. **USD only.** Financial Institutions OUT OF SCOPE (unchanged).

---

## 1. Banner

| Rule | Posture |
|------|---------|
| Document type | **Market-price DECISION PASS** — contract lock only |
| Spec lock | **SPEC_LOCKED** into Plan §0.T |
| Implementation | **Forbidden** until separate impl authorization |
| Stage 8 analytical logic | **Untouched** — adapters replaceable without reopening VA/DCF/reverse-DCF/MoS rules |
| Stages 1–7 / Stage 9 | **Untouched** |
| BUY/SELL / colors / scores | **Forbidden** |
| Audit findings A1–A7 / B1–B4 / C1–C3 | **Not fixed** by this lock |

---

## 2. Locked decisions (APPROVED)

### MP-D1 — Price type
**APPROVED:** Use **RAW regular-session close** only.  
**Forbidden:** adjusted close; VWAP; last trade; bid/ask mid; synthetic marks.

### MP-D2 — Session
**APPROVED:** Price must be the **latest completed US regular trading session** close.  
**Forbidden:** intraday; pre-market; after-hours; “live last” while the session is open.

### MP-D3 — Currency
**APPROVED:** **USD only** for Stage 8 v1 market-price ingest. Unresolved non-USD → do not silently convert; follow existing currency-reconcile / exception posture.

### MP-D4 — Primary / secondary sources
**APPROVED:**
| Role | Source | Access |
|------|--------|--------|
| **Primary** | Yahoo Finance | via `yfinance` (or equivalent Yahoo daily OHLC adapter) |
| **Secondary / cross-check** | Stooq | free daily close adapter |

Adapters are **replaceable** without reopening Stage 8 analytical Plan §0 (VA/DCF/etc.). Changing vendors later is a **market-data adapter** change, not a Stage 8 valuation redesign — but **this v1 pair is LOCKED** until a separate Decision Pass updates §0.T.

### MP-D5 — Fetch / retry / fallback
**APPROVED:**
1. Cache key = `ticker` + `session_date` (completed US session date).
2. Per source: **1 initial attempt + 1 retry** on transient failure only.
3. If primary fails after retry → **fallback** to secondary.
4. If only one source returns a valid same-session raw close → **accept** with `crosscheck_status=SINGLE_SOURCE` warning.
5. If both valid → compare same-session **raw** closes.
6. Conflict threshold = **`max($0.02, 0.05% of primary close)`** (absolute dollars vs relative; use the larger of the two).
7. Above threshold → `crosscheck_status=PRICE_SOURCE_CONFLICT` → **no price-sensitive valuation**; outcome lean **`REVIEW_REQUIRED`** (existing safe missing/conflict posture).
8. Neither available → `PRICE_UNAVAILABLE` → existing safe missing-price behavior (`UNKNOWN` freshness / no price-sensitive IV/MoS; `REVIEW_REQUIRED` / `TOO_HARD` by severity per §0.H).

### MP-D6 — Persistence fields (LOCKED)
Each accepted or attempted price record MUST persist:

| Field | Meaning |
|-------|---------|
| `ticker` | Symbol |
| `raw_close` | RAW regular-session close (USD) |
| `session_date` | Completed US session calendar date |
| `price_as_of` | Session-close timestamp representation Stage 8 freshness expects (ET close) |
| `source` | Provider id that supplied the accepted (or attempted) quote |
| `currency` | `USD` |
| `fetched_at` | Wall-clock fetch timestamp |
| `crosscheck_status` | e.g. `MATCHED` / `SINGLE_SOURCE` / `PRICE_SOURCE_CONFLICT` / `PRICE_UNAVAILABLE` |
| `raw_response_hash` | Hash of provider raw payload(s) used |

Optional companion fields (allowed, not required for lock): primary/secondary closes, absolute/relative delta, retry counts.

### MP-D7 — Hand-off into Stage 8
**APPROVED:** Stage 8 continues to consume injected:
- `market_price` = accepted `raw_close`
- `price_as_of` = session close as_of
- `price_source` = durable label including provider + `independent` provenance pattern as implemented later

Provider adapters MUST remain **outside** Stage 8 analytical modules so valuation logic does not import Yahoo/Stooq SDKs directly.

### MP-D8 — Relationship to prior D2 / §0.H
**APPROVED / CLARIFIED:**
- Session-aware freshness classes (`CURRENT` / `RECENT` / `STALE` / `UNKNOWN`) in §0.H remain **LOCKED**.
- Exact hour/day cutover numerics for CURRENT/RECENT/STALE remain **NOT_LOCKED** (calibration).
- Prior note “vendor = NOT_LOCKED” is **superseded for the daily close ingest path only** by this Market Price v1 lock (Yahoo primary + Stooq secondary). Other quote styles (NBBO, options) remain OUT of v1.

---

## 3. Explicitly NOT locked / NOT authorized

- Implementation of adapters, cache store, or wiring into `run_stage8`
- Changing Stage 8 IV / reverse DCF / MoS / VA analytical rules
- Fixing audit findings (debt, cash mapping, OE mix, FTC semantic, etc.)
- Using adjusted close for valuation bridge
- Non-USD automatic FX conversion as a silent price
- Overall Final System Audit PASS/FAIL

---

## 4. Freeze verification

| # | Check | Result |
|---|--------|--------|
| 1 | RAW close only | **PASS** — MP-D1 |
| 2 | Latest completed US session; no intraday/pre/AH | **PASS** — MP-D2 |
| 3 | Yahoo primary + Stooq secondary | **PASS** — MP-D4 |
| 4 | Retry + fallback + conflict threshold | **PASS** — MP-D5 |
| 5 | Persistence fields named | **PASS** — MP-D6 |
| 6 | Adapters replaceable without Stage 8 analytical reopen | **PASS** — MP-D7 |
| 7 | Implementation authorized | **FAIL by design** — not authorized |

---

## 5. Authority line

**FA Stage 8 — Market Price v1 — SPEC_LOCKED (contract only; not implemented).**  
Authority: explicit user lock 2026-10-02 (Europe/Istanbul). Plan §0.T is canonical; this Decision Pass is companion.

**STOP — no implementation under this authorization.**
