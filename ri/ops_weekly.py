"""Weekly ops rollup from runs.jsonl — deterministic."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from . import config

def rollup(runs_path: Path | None = None, out_dir: Path | None = None) -> Path:
    runs_path = runs_path or (config.DRIVE_OPS_LOGS / "runs.jsonl")
    out_dir = out_dir or config.DRIVE_OPS_WEEKLY
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    if runs_path.exists():
        for line in runs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    now = datetime.now(timezone.utc)
    week = now.strftime("%Y-W%W")
    by_comp = defaultdict(lambda: {"cost": 0.0, "runs": 0, "fail": 0, "tokens_in": 0, "tokens_out": 0, "tools": 0, "retries": 0})
    for r in rows:
        c = r.get("component") or "unknown"
        by_comp[c]["cost"] += float(r.get("estimated_cost") or 0)
        by_comp[c]["runs"] += 1
        by_comp[c]["fail"] += 1 if r.get("status") == "fail" else 0
        by_comp[c]["tokens_in"] += int(r.get("input_tokens") or 0)
        by_comp[c]["tokens_out"] += int(r.get("output_tokens") or 0)
        by_comp[c]["tools"] += int(r.get("tool_calls") or 0)
        by_comp[c]["retries"] += int(r.get("retry_count") or 0)
    lines = [f"# Ops haftalık özet {week}", "", f"Toplam koşu: {len(rows)}", ""]
    for comp, s in sorted(by_comp.items()):
        fr = (s["fail"] / s["runs"]) if s["runs"] else 0
        lines.append(f"## {comp}")
        lines.append(f"- runs: {s['runs']}")
        lines.append(f"- estimated_cost: ${s['cost']:.4f}")
        lines.append(f"- tokens in/out: {s['tokens_in']}/{s['tokens_out']}")
        lines.append(f"- tool_calls: {s['tools']}")
        lines.append(f"- failure_rate: {fr:.2%}")
        lines.append(f"- retries: {s['retries']}")
        lines.append("")
    lines.append("_Kaynak tazeliği / dedup oranı bir sonraki canlı ingest ölçümünde doldurulacak._")
    out = out_dir / f"{week}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
