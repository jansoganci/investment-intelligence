# FA Stage 1 — Implementation Status v1

**Date:** 2026-09-14 (Europe/Istanbul)  
**Scope:** Stage 1 Gates 0–2 (A rulebook lock → B `fa/stage1/` → C tests)  
**STOP:** After tests + this report. **No UAT. No Stage 3. No philosophy redesign. No Stage 2 calc redesign** (minimal PROCEED gate only).

---

## A — Rulebook lock

| Artifact | Path | Status |
|----------|------|--------|
| Stage 1 gates detail | `03_Fundamental/STAGE_1_GATES_v1.md` | **LOCKED** |
| Rulebook pointer | `FUNDAMENTAL_FILTER_RULEBOOK_v0.md` §13 | **LOCKED** |
| §8 register | Gate 0–2 acceptance wording removed from “topics later”; marked LOCKED | Done |
| §11.4 items | Capital-intensive subtype; thesis TR/EN; Stage 2 same-session | **Still TBD** — not invented |

Content folded from `OWNERSHIP_PHILOSOPHY_RESEARCH_v1.md` only: Gate 0 OpCo/FI/commodity; G1-M*/S*/L*; G2-M*/S*; thesis template; ban list; process outcomes `PROCEED | TOO_HARD | REVIEW_REQUIRED | STOP_NO_THESIS`; no colors; no valuation; no numeric thresholds; Stage 2 blocked unless Stage 1 PROCEED.

---

## B — Package `fa/stage1/`

| Module | Role |
|--------|------|
| `questions.py` | Gate 0/1/2 IDs + text + ban list constants |
| `evaluate.py` | Deterministic answers → `process_outcome` (no LLM) |
| `report.py` | ADHD markdown (mirrors Stage 2 style) |
| `storage.py` | `Thesis/stage1_CURRENT.json` + `stage1_versions/` + Generated mirror |
| `pipeline.py` | `run_stage1(ticker, payload)`; `happy_path_payload_synth_opco()` |

**Pipeline gate:** `fa/pipeline.analyze_company` refuses Stage 2 calc unless `Thesis/stage1_CURRENT.json` has `process_outcome == PROCEED`. Synthetic fixture seed writes a PROCEED Stage 1 for `SYNTH_OPCO` dry-run.

**Models:** `Stage1Report`, `Stage1Thesis`, `STOP_NO_THESIS` on `ProcessOutcome`; `AnalyzeResult.stage2_blocked`.

---

## C — Tests

`tests/fa/test_stage1_evaluate.py`, `tests/fa/test_stage1_pipeline.py`:

1. Happy path → PROCEED  
2. Missing G1-M1–M4 → TOO_HARD  
3. No falsifiers G1-M7 → TOO_HARD  
4. Ban-list one-liner → REVIEW_REQUIRED  
5. FI Gate 0 → TOO_HARD / OOS  
6. Unlisted ticker refused  
7. Stage 2 blocked when Stage 1 not PROCEED; allowed when PROCEED (SYNTH dry-run)

---

## How to dry-run Stage 1

```bash
cd /workspace/investment_intelligence
.venv/bin/python -c "
from fa.pipeline import dry_run_stage1_synth_opco
r = dry_run_stage1_synth_opco()
print(r.markdown)
print('outcome=', r.stage1.process_outcome)
"
```

Or:

```python
from fa.stage1.pipeline import run_stage1, happy_path_payload_synth_opco
from fa import config
run_stage1("SYNTH_OPCO", happy_path_payload_synth_opco(), fa_list_path=config.DEMO_FA_LIST)
```

Pytest:

```bash
cd /workspace/investment_intelligence && .venv/bin/python -m pytest tests/fa -q
```

---

## D — Remains for user UAT (parent / user)

- Live (non-SYNTH) company on FA List with real Gate 0–2 answers  
- Thesis language TR vs EN (§11.4)  
- Capital-intensive Gate 2 subtype (§11.4)  
- Same-session vs batch Stage 2 after PROCEED (§11.4)  
- Optional Drive upload of status beyond transition copy  

---

## Confirmations

- **Stage 3 not started**  
- **No color scoring / Dragonomi / new philosophy / numeric thresholds**  
- **Stage 2 calc/report unchanged** except PROCEED gate

## D — Stage 1 UAT — ACCEPTED (2026-09-14)

- **Ticker:** KO (The Coca-Cola Company) — first real production FA List name  
- **Primary evidence:** Form 10-K FY2025, filed 2026-02-20, accession `0001628280-26-010047`  
- **Process outcome:** PROCEED (Stage 2 eligible; **not run** in this UAT)  
- **Artifacts:** `fa_data/companies/KO/Thesis/stage1_CURRENT.json`, `fa_data/uat/KO_stage1_payload_v1.json`, `fa_data/uat/KO_stage1_evidence_notes.md`  
- **User:** Stage 1 UAT accepted for KO  
