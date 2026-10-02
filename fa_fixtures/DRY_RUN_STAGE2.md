# FA Stage 2 dry-run

```bash
cd /workspace/investment_intelligence
python3 -m venv .venv && .venv/bin/pip install pytest   # once
FA_OFFLINE=1 .venv/bin/python -c "from fa.pipeline import dry_run_synth_opco; r=dry_run_synth_opco(); print(r.markdown); print(r.stage2.process_outcome)"
.venv/bin/python -m pytest tests/fa -q
```

Synthetic only: `SYNTH_OPCO`. Production `fa_data/data/fundamental_analysis_list.json` starts empty.
