# Technical Audit Report — investment-intelligence

**Date:** 2026-10-02
**Scope:** Whole repository at `31b689a` (`main`): `fa/` (~37k LOC across modules), `ri/`, `tests/` (420 tests), fixtures, docs.
**Mode:** Read-only. No code was changed. The only file this audit adds is this report.

---

## 0. Executive summary

The FA spine is **unusually disciplined about honesty**. It tracks lineage for every field, gives typed null reasons, never coerces null to zero, keeps immutable versioned periods, never averages terminal values, and has explicit REVIEW/TOO_HARD outcomes. The architecture is sound.

The main risks sit at the **data edge (XBRL selection) and in cross-stage consistency**, not in the stage logic:

1. **Restatements are effectively invisible.** Period docs are pinned to the *original* filing's values, the SEC cache never expires, and existing periods are skipped on re-ingest.
2. **Two different gross-debt definitions** are in use. Stage 2 uses ST + CPLTD + LTD + secured. Stage 8's EV bridge uses `total_debt`, otherwise LTD + ST. As a result, leverage and IV are computed on different debt numbers.
3. **"FCFF" is actually levered FCF.** The value is OCF − CapEx, which is already after interest under US GAAP. The bridge then subtracts full gross debt, so debt is counted against the equity value twice.
4. **The quarter flow-basis arithmetic fallback is wrong for growing companies.** Discrete quarters 100/110/120 with FY 460 are classified as YTD, which derives Q4 = 340 instead of 130. The fallback only runs when duration/hint metadata is missing, so the bug is latent today.
5. **The SEC client can substitute synthetic fixture data for a real ticker.** In online mode, any network error makes `get_companyfacts`/`get_submissions` return the synthetic stub regardless of CIK (§3.4).
6. **The test suite is not portable.** 26 test files hardcode `/workspace/investment_intelligence`. Off the original box, 16 tests fail and about 45 "boundary" tests **pass vacuously** because they scan an empty source string.

---

## 1. Architecture

### 1.1 Pipeline stages

| Layer | Module | Role | Entry point |
|---|---|---|---|
| Universe gate | `fa/lists.py` | FA List gate. The production list starts empty and the demo list lives in `fa_fixtures/` | `require_on_fa_list` |
| SEC acquisition | `fa/sec_client.py` | ticker→CIK, submissions, companyfacts, primary HTML. Disk cache, offline by default (`FA_OFFLINE=1`) | `get_companyfacts`, `get_submissions`, `get_filing_document` |
| Source ingest | `fa/ingest.py`, `fa/filing_coverage.py` | Idempotent Source manifest (SEC accession / IR hash / notes) | `ingest_sec_filing`, `ensure_recent_sec_filings` |
| Period discovery | `fa/history_coverage.py` | Finds FY and Q periods from the revenue series and picks contiguous quarters | `discover_periods_from_companyfacts` |
| XBRL → contract | `fa/map_companyfacts.py` + `fa/contract.py` + `fa/lineage.py` | Tag-priority mapping, duration/YTD tagging, null reasons, lineage | `map_companyfacts_to_period` |
| Q4 derivation | `fa/quarter_derivation.py` | Q4 = FY − Q3YTD or FY − ΣQ1..Q3. Never derives balance-sheet fields | `derive_q4_period_document` |
| Normalized store | `fa/versioning.py`, `fa/storage.py` | Immutable `vNNN` JSON per period plus a CURRENT pointer and index | `create_initial_version`, `create_superseding_version` |
| Stage 1 | `fa/stage1/` | Gates 0–2 (business understanding / thesis spine) → `PROCEED`… | `run_stage1` |
| Stage 2 | `fa/stage2/` | Financial fragility: debt, liquidity, WC, growth basis | `analyze_company` (`fa/pipeline.py`) |
| Stage 3 | `fa/stage3/` | Cash truth: OCF vs NI bridge, FCF | `run_stage3` |
| Stage 4 | `fa/stage4/` | Growth / archetype / per-share | `run_stage4` |
| Stage 5 | `fa/stage5/` | Pricing power / margins | `run_stage5` |
| Stage 6 | `fa/stage6/` | Capital allocation / ROIC / IC | `run_stage6` |
| Stage 7 | `fa/stage7/` | Moat / competitive pressure | `run_stage7` |
| Stage 8 | `fa/stage8/` + `fa/market_price/` | Valuation: normalized base, FCFF DCF (dual terminal), reverse DCF, EV bridge, price freshness | `run_stage8` |
| Stage 9 | `fa/stage9/` | External risk / thesis breakers | `run_stage9` |
| Final FA | `fa/final_fa/` | Reads Stage 1–9 CURRENT → `GREEN/ORANGE/RED/REVIEW_REQUIRED/TOO_HARD/INCOMPLETE` + `technical_eligible` | `run_final_fa` |
| Registry | `fa/registry/` | SQLite run registry, hooks on every stage save, drift, backfill, backup | `registry_session`, hooks |
| RI (separate) | `ri/` | Research intelligence: source adapters → normalize → dedup → cluster → ideas | `ri/pipeline.py` |

### 1.2 Data flow: SEC XBRL to Final FA

```
SEC company_tickers.json ─► resolve_cik ─┐
SEC submissions/CIK.json ───────────────┼─► filing_coverage ─► Source manifest + cached 10-K/10-Q HTML
SEC companyfacts/CIK.json ──────────────┘
          │  (disk cache under FA_ROOT/cache/sec — no TTL)
          ▼
discover_periods_from_companyfacts (revenue series → FY keys + ≤8 contiguous Q keys)
          ▼
map_companyfacts_to_period   ── per field: TAG_MAP priority → _pick_fact_value
          │                     (filter fy==FY-of-filing, fp; score exact_end/end_year/duration/accn/form)
          │                     → value + lineage + null_reason + flow_basis/duration_days
          ▼
quarter_derivation (Q4 from FY & Q1–Q3; YTD-aware; blocks on ambiguity)
          ▼
versioning: companies/<T>/Normalized/<period>/vNNN.json + CURRENT  (accept=True when called from stage pipelines)
          ▼
Stage 1 ─► Stage 2 ─► Stage 3 ─► Stage 4 ─► Stage 5 ─► Stage 6 ─► Stage 7 ─► Stage 8 ─► Stage 9
 (each run_stageN re-calls ensure_normalized_history, then reads prior-stage CURRENT JSON)
          ▼
Final FA (reads S1–S9 CURRENT only) ─► final_fa CURRENT + markdown ─► registry row
```

Only Stages 1–2 are orchestrated by `fa/pipeline.py::analyze_company`. Stages 3–9 and Final FA are deliberately independent entry points; the boundary tests enforce this. **C-8: No orchestrator runs 1→9→Final on one consistent data snapshot.** Each `run_stageN` re-runs `ensure_normalized_history`. Final FA reads whatever CURRENT each stage last wrote, with no check that all stages consumed the same Normalized period set.

### 1.3 Module dependencies (intra-package imports)

```
registry      → ids
stage1        → ids, lists, models, registry
stage2        → ids, models, registry
stage3        → contract, ids, lists, models, registry, sec_client, stage1
stage4        → comparability, contract, filing_coverage, history_coverage, quarter_derivation, sec_client, stage1, stage3, …
stage5        → … history_coverage, quarter_derivation, stage1, stage4
stage6        → … comparability, history_coverage, quarter_derivation, stage1, stage4, stage5
stage7        → … history_coverage, stage1, stage4, stage5, stage6
stage8        → … history_coverage, stage1, stage4, stage6, stage7
stage9        → … history_coverage, stage1, stage4, stage5, stage6, stage7, stage8
final_fa      → stage1..stage9, registry
market_price  → models, stage8
```

The graph is a clean DAG with strictly backward stage dependencies and no cycles. Two modules are hubs. `fa/models.py` (1,205 LOC) holds every stage's dataclasses, and `fa/history_coverage.py` is called by every stage pipeline from 4 to 9.

---

## 2. Financial correctness risks

Severity: **H** = can silently produce wrong numbers in normal use · **M** = wrong in specific but realistic cases · **L** = edge case / cosmetic.

### 2.1 Restated filings

| # | Sev | Finding | Evidence |
|---|---|---|---|
| R-1 | **H** | **Values are pinned to the original filing.** `_pick_fact_value` keeps only rows where `row["fy"] == fiscal_year`. In companyfacts, `fy` is the fiscal year of the *filing*, so restated comparatives in later 10-Ks (`fy = year+1`, same `end`) are always discarded. | `fa/map_companyfacts.py` `_pick_fact_value` (`if fy is not None and row.get("fy") != fy: continue`) |
| R-2 | **H** | **Amendments are deprioritized.** `form_prefer` defaults to `("10-K","10-Q","20-F","20-F/A")`, so `10-K/A` and `10-Q/A` rows score `form_ok=0` and lose to the original. Period discovery also scores non-amended forms higher on purpose (`2 if form in ("10-K","20-F")`). | `map_companyfacts.py` `_pick_fact_value`; `history_coverage.py` `discover_periods_from_companyfacts` |
| R-3 | **H** | **Existing periods are never re-mapped.** `_ensure_mapped_period` only creates new periods or back-fills missing share fields. Any other existing period goes to `report["skipped"]`, so a restatement never produces a superseding version automatically. | `fa/history_coverage.py` `_ensure_mapped_period` |
| R-4 | **H** | **The SEC cache has no TTL.** `get_companyfacts`, `get_submissions` and `resolve_cik` return the disk cache whenever it exists. New 10-K/10-Q filings and restatements never arrive until someone deletes the cache by hand. | `fa/sec_client.py` |
| R-5 | M | The restatement guard in derivation (`_version_conflict`) only fires on `change_reason == "restatement"`, which no automated path ever sets. | `fa/quarter_derivation.py` |

**Net effect:** the system is consistently "as originally reported". That is a defensible choice for point-in-time research, but it is not documented as a choice, and it is applied inconsistently. For example, a Q4 can be derived from an original FY minus a Q3 that was itself restated in a later 10-Q. Pick one policy (`as_reported` vs `latest_restated`), record it per period, and detect the delta.

### 2.2 Fiscal period alignment

| # | Sev | Finding | Evidence |
|---|---|---|---|
| P-1 | **H** | **FY discovery drops issuers whose FYE falls in the next calendar year.** It requires `int(end[:4]) == fy`. Retailers with a late-Jan/early-Feb FYE that label the year by its start (e.g. FYE 2025-02-01 reported as `fy=2024`) lose every FY period. | `history_coverage.py` `discover_periods_from_companyfacts` |
| P-2 | M | `map_companyfacts_to_period` defaults `period_end = f"{fiscal_year}-12-31"` for FY when the caller passes none. That is wrong for any non-December FYE. The only production caller passes `period_end`, so the risk is latent. Any new caller inherits the bug. | `fa/map_companyfacts.py:694` |
| P-3 | M | `_row_score.end_year_match` uses `end[:4] == fy`. For Q1–Q3 of a non-Dec FYE, that is the *prior* calendar year, so the correct rows lose this score component. Only `exact_end` rescues them, which requires `period_end`. | `map_companyfacts.py` `_row_score` |
| P-4 | M | **Off-by-one duration.** Doc-level `duration_days` uses `(end − start) + 1`, while the field/derivation durations use `(end − start)`. Two definitions of the same quantity are fragile, and the window boundaries (70/110/300/400) are applied to both. | `map_companyfacts.py` vs `quarter_derivation._duration_days`, `history_coverage._duration_days` |
| P-5 | M | **CAGR assumes contiguous FY keys.** `n_years = len(fy) − 1` and `revenue_cagr_5y` uses `rev_all[-6]` by index. A missing FY (dropped by P-1, or a null revenue) silently stretches the real horizon, so CAGR is overstated. | `fa/stage4/calc.py` L446–462 |
| P-6 | L | `period_start`/`period_end` are taken from the *first mapped field's* chosen row when the doc lacks them. If that row is a comparative column, the whole doc's dates are wrong. | `map_companyfacts.py` "Persist period_start/end" block |

### 2.3 Quarter (Q4) derivation

| # | Sev | Finding | Evidence |
|---|---|---|---|
| Q-1 | **H (latent)** | **The arithmetic fallback misclassifies discrete quarters.** `nested_up = q1<q2<q3<FY` is true for *any* growing company with positive discrete quarters, because FY is always larger than one quarter, so it returns `YTD`. Reproduced: `classify_quarterly_flow_basis(100,110,120,460)` → `YTD`, which derives Q4 = 460−120 = **340** instead of 130. The additive check `|Q1+Q2+Q3−FY|≤tol → DISCRETE` is also inverted: it implies Q4 = 0. Mapped docs always carry `field_flow_basis` hints, so this only runs for legacy, manual or fixture docs. | `fa/quarter_derivation.py` `classify_quarterly_flow_basis` |
| Q-2 | M | Flow basis, unit and duration are carried as **free text in lineage `notes`** and recovered by regex (`duration_days\s*=`, `unit[=:\s]+`). A wording change in a note silently changes the derivation path. | `quarter_derivation._field_duration_days`, `_field_unit` |
| Q-3 | M | Side-channel lookups (mixed AP fallback, mixed payables CF, `company_specific_cfs_adjustments` harvest) call `_pick_fact_value` **without `prefer_duration`**, so for quarters they can pick YTD rows. | `map_companyfacts.py` post-map blocks |

### 2.4 Unit and scale

| # | Sev | Finding | Evidence |
|---|---|---|---|
| U-1 | M | **The chosen XBRL unit is never persisted.** `_pick_fact_value` falls back to `next(iter(units.values()))` when USD is absent (IFRS 20-F filers in EUR/JPY, etc.). `reporting_currency` defaults to `"USD"` in `contract.py`, `models.py` and `stage8/calc.py`. A JPY filer's values would be treated as USD in the EV bridge against a USD price, with no flag. | `map_companyfacts.py`; `contract.py:215`; `stage8/calc.py:66` |
| U-2 | L | `_field_unit` returns `"USD"` by default for any field without explicit unit metadata. | `quarter_derivation.py` |
| U-3 | L | XBRL values are full units, so there is no thousands/millions scale bug in the companyfacts path. Manually entered or IR periods have no scale field, so any future non-XBRL ingest has no guard. | `contract.py` |

### 2.5 Missing-tag fallbacks and tag-priority risks

| # | Sev | Finding | Evidence |
|---|---|---|---|
| T-1 | **H** | **Possible LTD double-count.** `long_term_debt` falls back to `LongTermDebt`, which by us-gaap definition *includes* the current portion. Stage 2 then adds `current_portion_ltd` (`LongTermDebtCurrent`) on top, so gross debt and near-term obligations are overstated whenever `LongTermDebtNoncurrent` is absent. | `TAG_MAP["long_term_debt"]`; `stage2/calc.py` gross debt |
| T-2 | **H** | **Debt definition differs across stages.** Stage 2 gross debt is ST + CPLTD + LTD + secured, with components preferred. The Stage 8 bridge uses `total_debt` first, otherwise **LTD + ST only**, with no CPLTD and no secured debt. `total_debt` can map to `LongTermDebtAndCapitalLeaseObligations`, which is typically the *noncurrent* line. EV, equity IV and MoS can therefore rest on a smaller debt number than the Stage 2 fragility verdict. | `stage8/calc.py` L128–137 vs `stage2/calc.py` L80–120 |
| T-3 | M | **Leases are first-match, not summed.** `lease_liability_current/noncurrent` take Operating OR Finance. When both exist, the field is flagged SOURCE_CONFLICT but only the operating lease is kept. Finance leases are often already inside `LongTermDebt*`. There is no explicit policy here. | `TAG_MAP` lease entries |
| T-4 | M | **Ambiguity flag is noisy.** Any field where two or more preferred tags have a value is flagged `SOURCE_CONFLICT`, even when the values are identical. That pushes uncertain flags (and REVIEW pressure) onto many healthy issuers and dilutes the real conflicts. | `_pick_fact_value` `ambiguous = len(best_by_tag) > 1` |
| T-5 | M | `net_income_attributable` prefers `NetIncomeLossAvailableToCommonStockholdersBasic`, which is after preferred dividends, over `NetIncomeLoss`. The two concepts are not interchangeable across issuers. | `TAG_MAP` |
| T-6 | M | `cash_and_equivalents` can fall back to the combined cash + restricted tag. It is flagged uncertain, but Stage 8 still subtracts it fully in EV. | `TAG_MAP`; `stage8/calc.py` |
| T-7 | L | `capex` falls back to `PaymentsToAcquireProductiveAssets`, which can include intangibles and software. This is not flagged. | `TAG_MAP["capex"]` |

### 2.6 Valuation math (Stage 8)

| # | Sev | Finding | Evidence |
|---|---|---|---|
| V-1 | **H** | **"FCFF" is levered.** The base is OCF − CapEx, and US GAAP OCF is after cash interest. `equity_iv_from_enterprise` then subtracts full gross debt, so the debt burden is counted twice and equity IV is biased low for indebted companies. Fix by adding back after-tax interest (`interest_expense × (1−t)`), or by relabelling the method as FCFE and dropping the debt subtraction. | `stage8/normalization.py`, `stage8/dcf.py`, `stage8/calc.py::equity_iv_from_enterprise` |
| V-2 | M | **Wrong share basis for the bridge.** It uses the FY **diluted weighted-average** share count against a *current* price. For heavy buyback or issuance names, the period-end diluted count differs materially from the WAD. | `stage8/calc.py::prefer_diluted_shares` |
| V-3 | M | **Mixed FCF methods in one median.** `fcf_like` mixes `disclosed_fcf` with computed OCF − CapEx inside the same 3-year median. | `stage8/normalization.py` |
| V-4 | L | NCI and preferred stock are always `None` in the bridge ("not invent"), so equity IV is overstated for issuers with material NCI. A flag exists but no data path does. | `stage8/calc.py` |
| V-5 | L | The exit multiple is a hardcoded FCFF multiple (10/12/14×) that does not depend on the discount rate. At r = 8% with g = 3%, the perpetuity-implied multiple is about 20.6×, so the two terminals diverge by construction. The "large disagreement" signal is partly an artefact of this. | `stage8/dcf.py` |

### 2.7 Other calculation inconsistencies

| # | Sev | Finding | Evidence |
|---|---|---|---|
| X-1 | M | **YoY uses inconsistent denominators.** Stage 2 divides by `abs(prev)`; Stage 4 `yoy_change` divides by `prev`, so the sign flips for negative bases. | `stage2/calc.py:320,350` vs `stage4/calc.py:82` |
| X-2 | M | **Lease-only leverage.** `lease_adjusted_contractual_debt = (gross_debt or 0) + leases`. When gross debt is null, D/E and D/A are computed on **leases only**, without a null reason. In addition, `debt_for_ratio = lease_adj or gross_debt` treats 0.0 as missing. | `stage2/calc.py` L160–240 |

---

## 3. Code health

### 3.1 Duplication

- **`fa/stage{2..9}/storage.py` are 99% identical** (8 × 90 LOC, measured with difflib). One generic `StageStore(stage_n, report_cls)` would replace about 650 LOC.
- `fa/stage5/pipeline.py` and `stage6/pipeline.py` are 90% similar. Stage 3/5/8 and 7/9 pipelines are about 60% similar. All of them share the same scaffold: FA-list gate → layout → gate0 → `ensure_normalized_history` → load CURRENT → semantic → evaluate → save.
- **11 separate `_num()` helpers** and 3 separate `_duration_days()` implementations (one of them off by one; see P-4).
- 15 redundant expressions of the form `doc.get("x") or doc.get("x")`, e.g. `quarter_derivation.py:166,183,187,198,203,208`.
- `RESEARCH_CANDIDATE_EXIT_EBITDA_MULTIPLE` is a legacy alias that the code itself flags as a defect.

### 3.2 Dead or unused code (pyflakes + vulture; some items are used only by tests)

- 34 unused imports, 9 f-strings without placeholders, and 5 unused locals: `stage9/evaluate.py:534 best_ex`, `stage4/evaluate.py:409 must_missing`, `stage4/archetype.py:201 slot`, `stage8/normalization.py:48 fcf_disclosed`, `ri/cluster.py:56 base`.
- `fa/pipeline.py::analyze_company` has a no-op tail: an `if/else` where both branches are `pass`, plus `assert not hasattr(analyze_company, "stage3")`. `_load_fixture_periods` returns `sources`, which no caller uses.
- `map_companyfacts._facts_us_gaap`, `quarter_derivation.index_to_fy_q` / `step_quarter_forward`, and `stage8/semantic.placeholder_stage8_semantic` are unused in production. In `_row_score`, the `elif dur is None …: dur_ok = 0` branch does nothing. `_field_duration_days` computes a `flow_basis` regex match and discards it.
- `_pick_fact_value`'s docstring says it returns a 4-tuple; it returns 5 values.

### 3.3 Missing tests and test-design gaps

| Gap | Detail |
|---|---|
| **Path portability** | 26 test files plus `tests/fa/conftest.py` hardcode `/workspace/investment_intelligence/...` (e.g. `ROOT`, `demo_list_path`, `STAGE8 = Path(...)`). |
| **Vacuous boundary tests** | `_all_source()` globs a directory that does not exist off-box → `""` → assertions like `"run_stage5" not in src` pass. Measured: **45 boundary/architecture tests pass with no source loaded.** These are the project's architectural guardrails, and outside the original box they enforce nothing. |
| **Clock-dependent tests** | The 3 "known Stage 8 freshness fails" are not flakes. The tests hardcode `price_as_of="2026-09-29…"`, and `evaluate_stage8` reads `datetime.now()` instead of taking an injectable `now`. They started failing as wall time moved on and will keep failing. 48 `now()`/`today()`/`utc_now()` call sites exist in `fa/`. |
| **Missing fixture data** | `tests/ri/test_emtia_adapter.py` reads `ri_data/harvests/…json`, which is excluded by `.gitignore`. |
| **Undeclared deps** | There is no `requirements.txt` or `pyproject.toml`. `pytest`, `pandas` and `yfinance` are needed but undeclared, and `test_yahoo_adapter_with_fake_yf` fails on `import pandas`. |
| **No CI** | There is no `.github/workflows`, so none of the above is caught automatically. |
| **Coverage holes (correctness)** | No tests for: restated or amended filings (R-1..R-4), non-December FYE (P-1/P-3), non-USD units (U-1), the `LongTermDebt` + CPLTD double count (T-1), Stage 2 vs Stage 8 debt parity (T-2), the FCFF interest treatment (V-1), or the growing-discrete-quarter fallback (Q-1). |

### 3.4 Error-handling gaps

- **22 `except Exception` sites.** Most are in stage pipelines around `ensure_normalized_history`; they convert the error to `{"failed": [...AUTOMATION_GAP]}` and **continue on whatever periods are already on disk**. A network or mapping failure therefore produces a stage verdict on stale data, with the failure buried in `history_report`.
- **HIGH: real tickers can silently get synthetic data.** In online mode, when the HTTP call fails (`URLError`/`OSError`/timeout), `get_submissions` and `get_companyfacts` return `fa_fixtures/synthetic_operating_company/*_stub.json` **for any CIK**. The offline branch guards with `cik.endswith("9999991")`; the online `except` branch has no such guard. A transient SEC outage would therefore map the synthetic company's facts under a real ticker. See `fa/sec_client.py:101` and `fa/sec_client.py:127`. There is also no retry or backoff on 429/5xx, and a flat `sleep(0.1)` sits close to SEC's 10 req/s limit.
- **Non-atomic writes.** `storage.write_json` uses a plain `write_text`. A crash mid-write can corrupt a CURRENT pointer or a `vNNN.json` that is meant to be immutable. Use temp-file + `os.replace`.
- **TOCTOU on immutability.** `versioning` checks `path.exists()` and then writes. This is fine for a single user, but nothing serializes concurrent stage runs.
- **Auto-accept.** Stage pipelines call `ensure_normalized_history(..., accept=True)`, which stamps machine-mapped periods `status="accepted"` and `review_status="accepted"`. This overwrites the mapper's `review_status="pending"` and pending human-review notes.

### 3.5 Hardcoded values

- **Absolute paths:** `ri/config.py` (`ROOT`, `DRIVE_*` under `/workspace/...`), `fa/config.py::DRIVE_FA_CONCEPTUAL`, and the test paths above.
- **SEC identity:** `SEC_USER_AGENT` uses `research@example.com`. SEC fair-access policy requires a real contact; read it from env.
- **Valuation constants:** discount classes (8/10/12/13%), terminal g, exit multiples, growth paths, ±200 bps spread, and the 25% disagreement threshold are module constants in `stage8/dcf.py`. They are honestly labelled `RESEARCH_CANDIDATE`, but they are not configurable per run and not recorded as a config hash in artifacts.
- **Duration windows** (70/110, 150/210, 230/300, 300/400) are duplicated in `map_companyfacts.py`, `quarter_derivation.py` and `history_coverage.py`.
- **Good:** no ticker hardcodes in production code (verified), which matches the repo's own guardrail.

### 3.6 Repo hygiene

- `fa/IMPLEMENTATION_STATUS_v1.md` and `fa/STAGE_1_IMPLEMENTATION_STATUS_v1.md` sit inside the Python package. They belong in `docs/`.
- `README.md` references `CHANGELOG.md`, which does not exist in the repo.
- `fa/models.py` is 1,205 LOC holding every stage's dataclasses. Split it per stage, next to the stage code.

---

## 4. Test run results

**Environment:** Python 3.11.15, pytest 8.x (installed for this audit; not declared by the repo), no pandas or yfinance.

### 4.1 As checked out (`python -m pytest -q`)

```
21 failed, 397 passed, 2 skipped in 2.95s
```

| Failure group | Count | Root cause |
|---|---|---|
| Hardcoded `/workspace/investment_intelligence` paths (conftest `demo_list_path`, boundary source reads, fixture reads) | 15 | Environment / test design |
| Stage 8 price freshness (`test_stage8_calc` ×2, `test_stage8_architecture_pressure` ×1) | 3 | Wall-clock time bomb: hardcoded `price_as_of` 2026-09-29 vs today |
| `test_market_price_v1::test_yahoo_adapter_with_fake_yf` | 1 | `pandas` not installed / undeclared |
| `tests/ri/test_emtia_adapter.py` | 1 | Fixture lives in git-ignored `ri_data/` |
| `test_wave1_…::test_w1_no_ticker_hardcodes_in_quarter_derivation` | 1 | Reads source via hardcoded path |

Skipped: the KO companyfacts cache is not present, and the live network smoke test is opt-in.

### 4.2 With a temporary `/workspace/investment_intelligence → repo` symlink (reproducing the original box; removed afterwards)

```
5 failed, 413 passed, 2 skipped in 2.48s
```

The 5 remaining failures are the 3 clock-dependent Stage 8 tests, the 1 pandas import and the 1 missing RI fixture. None of them points to a logic regression in the FA code. This differs from `PROJECT_STATUS.md` ("417 passed / 1 skipped") only by the environment-specific pandas and RI fixture failures.

### 4.3 Vacuous-pass measurement

With the symlink removed, the 12 path-dependent test files ran **12 failed / 89 passed**, and **45 of the 89 passes are `*_boundaries` / `*_architecture_pressure` tests** whose source-scan assertions run against empty strings.

---

## 5. Prioritized roadmap: top 10 by impact vs effort

Impact: correctness or trust risk removed. Effort: S ≈ ≤ ½ day, M ≈ 1–3 days, L ≈ 1 week+.

| Rank | Item | Fixes | Impact | Effort |
|---|---|---|---|---|
| **1** | **Make tests portable and non-vacuous.** Replace every `/workspace/...` with `Path(__file__).parents[n]` or `config.PACKAGE_ROOT`. In `_all_source()`, `assert` that ≥1 file was read. Add an injectable `now=` to `evaluate_stage8`/`classify_staleness` and pin it in tests. Move the RI fixture under `fixtures/`. | §3.3, §4 | High: guardrails become real | **S** |
| **2** | **Add `pyproject.toml`** (deps + optional `[market]` extra for pandas/yfinance) and **a GitHub Actions CI** running `pytest -m "not network"` + pyflakes. In the same PR, apply the one-line guard so the online `except` branches in `sec_client` never return the synthetic stub for a non-synthetic CIK. | §3.3, §3.4 | High: prevents regressions and wrong-company data | **S** |
| **3** | **Unify the gross-debt definition.** Extract one `compute_gross_debt(fields) -> (value, components, flags)` used by Stage 2 *and* the Stage 8 bridge. Drop `LongTermDebt` as an LTD fallback, or subtract CPLTD when it is used. Add a parity test. | T-1, T-2, X-2 | High: leverage and IV agree | **S–M** |
| **4** | **Fix the FCFF definition.** Add back after-tax interest (`interest_expense`, effective tax from `income_tax/pretax_income`), or explicitly relabel the method FCFE and value equity directly. Add a test with a levered fixture. | V-1 | High: IV bias on levered names | **S** |
| **5** | **Fix the Q4 flow-basis fallback.** Delete the `nested_up/down` and additive-identity rules. Without duration/hint evidence return `UNKNOWN`, which matches the module's own "refuse fabrication" principle. Add a growing-company regression test. | Q-1 | High (latent) | **S** |
| **6** | **Restatement policy and refresh.** Add a TTL/`force_refresh` to `sec_client` (e.g. re-pull companyfacts when `submissions.filings.recent` has a newer accession). Choose `as_reported` vs `latest_restated` per period. On re-ingest, diff mapped values against CURRENT and emit `create_superseding_version(change_reason="restatement")` when they change. Accept `/A` forms. | R-1..R-5 | High: data freshness and truth | **M** |
| **7** | **Fiscal calendar correctness.** Derive the FY label from DEI `DocumentFiscalYearFocus` / `CurrentFiscalYearEndDate` (or match on `end` within ±7 days of the FYE) instead of `end_year == fy`. Remove the `-12-31` default. Compute CAGR from actual period dates. | P-1..P-5 | High for non-Dec FYE issuers | **M** |
| **8** | **Persist units and currency.** Store `unit` per field from the chosen XBRL unit key. Set `reporting_currency` from it, and block the Stage 8 bridge when price currency ≠ reporting currency (or FX-convert with provenance). | U-1..U-3 | Medium–High (FPI / IFRS names) | **S–M** |
| **9** | **Snapshot consistency for Final FA.** Have each stage stamp a `normalized_snapshot_id` (hash of the CURRENT period pointers it consumed). Final FA should return `REVIEW_REQUIRED` when stages disagree. Stop continuing on stale periods when `ensure_normalized_history` fails, or surface the failure as a carry. | C-8 (§1.2), §3.4 | Medium–High: auditability | **M** |
| **10** | **De-duplicate the scaffolding.** Use a generic `StageStore` for `stage{2..9}/storage.py`, a `run_stage_scaffold()` for the shared pipeline prologue, and shared `_num`/`_duration_days`/duration-window constants. Make `write_json` atomic. Move structured metadata (flow_basis, duration, unit) out of free-text lineage notes into typed fields. | §3.1, §3.4, Q-2 | Medium: velocity and lower defect rate | **M–L** |

**Suggested sequencing:** do 1 → 2 first (one PR, under a day) so that every later fix lands behind real CI. Then 3 + 4 + 5 together as a "valuation & derivation correctness" wave; all three are small and test-driven. Do 6 + 7 + 8 as the "XBRL edge" wave, then 9 and 10.

---

## Appendix A: Method

- Static read of the core path: `sec_client`, `history_coverage`, `map_companyfacts`, `quarter_derivation`, `versioning`, `storage`, `stage2/calc`, `stage4/calc`, `stage8/{calc,dcf,normalization,pipeline,market_data}`, `final_fa/{pipeline,evaluate}`, `pipeline.py`.
- Import graph extracted with grep over `from ..` imports.
- Duplication measured with `difflib.SequenceMatcher` (ratio > 0.6 reported).
- Dead code: `pyflakes` and `vulture --min-confidence 60`. Vulture does not see test-only usage.
- Q-1 was reproduced by calling `classify_quarterly_flow_basis` directly. No repository files were modified.
- Stages 3, 5, 6, 7 and 9 evaluate/semantic logic and the `ri/` package were reviewed only at structural level (imports, error handling, duplication), not line by line for domain logic.
