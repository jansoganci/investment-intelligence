"""Service log per SERVICE_LOG_SPEC_v1 — no separate Ops agent."""
from __future__ import annotations
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from . import config
from .ids import new_id, utc_now

@dataclass
class RunLog:
    timestamp: str
    component: str = "Research Intelligence"
    run_id: str = ""
    job_type: str = ""
    status: str = "success"
    source_items: int = 0
    LLM_calls: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    estimated_cost: float = 0.0
    duration: float = 0.0
    errors: str = ""
    retry_count: int = 0
    notes: str = ""

    def estimate_cost(self) -> float:
        return round(
            (self.input_tokens / 1_000_000) * config.PRICE_IN_PER_M
            + (self.output_tokens / 1_000_000) * config.PRICE_OUT_PER_M,
            6,
        )

def append_run(log: RunLog, path: Path | None = None) -> None:
    p = path or (config.DRIVE_OPS_LOGS / "runs.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    if not log.run_id:
        log.run_id = new_id("run_")
    if not log.timestamp:
        log.timestamp = utc_now()
    if log.estimated_cost == 0.0 and (log.input_tokens or log.output_tokens):
        log.estimated_cost = log.estimate_cost()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(log), ensure_ascii=False) + "\n")

@contextmanager
def tracked_run(job_type: str, model: str = "", notes: str = ""):
    t0 = time.time()
    log = RunLog(timestamp=utc_now(), run_id=new_id("run_"), job_type=job_type, model=model, notes=notes)
    try:
        yield log
        if log.status == "success" and log.errors:
            log.status = "partial"
    except Exception as e:
        log.status = "fail"
        log.errors = str(e)
        raise
    finally:
        log.duration = round(time.time() - t0, 3)
        if log.estimated_cost == 0.0:
            log.estimated_cost = log.estimate_cost()
        append_run(log)
