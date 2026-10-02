"""run_stage3(ticker) — independent of Stage 4; not wired into fa.pipeline.analyze_company."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config, storage
from ..contract import validate_gate0_operating
from ..ids import normalize_ticker
from ..lists import NotOnFAListError, ensure_empty_production_list, require_on_fa_list
from ..models import AnalyzeResult
from ..stage1.storage import load_stage1_current
from .evaluate import evaluate_stage3
from .report import render_stage3_markdown
from .semantic import (
    load_stage3_semantic_from_fixture,
    run_stage3_semantic_from_filings,
)
from .storage import save_stage3_report


def run_stage3(
    ticker: str,
    *,
    root: Path | None = None,
    fa_list_path: Path | None = None,
    semantic_notes_path: Path | None = None,
    require_fa_list: bool = True,
) -> AnalyzeResult:
    """
    Run Stage 3 Cash Generation only.
    Refuses FI / non-operating Gate 0. Does not call or implement Stage 4.
    Does not mechanically terminate later stages.
    """
    ticker = normalize_ticker(ticker)
    root = root or config.FA_ROOT

    if require_fa_list:
        ensure_empty_production_list()
        try:
            entry = require_on_fa_list(ticker, path=fa_list_path)
        except NotOnFAListError as e:
            return AnalyzeResult(
                ticker=ticker,
                ok=False,
                refused=True,
                refuse_reason=str(e),
            )
    else:
        entry = None

    storage.ensure_company_layout(
        ticker, root, entity_name=(entry.name if entry else None)
    )
    meta = storage.load_meta(ticker, root)
    gate0 = meta.get("gate0_class") or (entry.gate0_class if entry else None) or "operating"
    cdir = storage.company_dir(ticker, root)

    ok_gate, gate_msg = validate_gate0_operating({"gate0_class": gate0})
    periods = storage.load_all_current_periods(ticker, root)

    man = storage.load_source_manifest(ticker, root)
    sources = [s.get("source_id") or s.get("path") or "" for s in man.get("sources", [])]

    notes_path = semantic_notes_path
    if notes_path is None:
        notes_dir = cdir / "Source" / "notes"
        if notes_dir.exists():
            for cand in list(notes_dir.glob("*stage3*")) + list(notes_dir.glob("*semantic*")):
                notes_path = cand
                break

    semantic = None
    if notes_path and Path(notes_path).exists():
        semantic = load_stage3_semantic_from_fixture(Path(notes_path))
    # Replace placeholder / empty stub with real filing-backed semantic pass
    if semantic is None or not semantic.filled:
        semantic = run_stage3_semantic_from_filings(ticker, root=root, persist=True)

    thesis_summary = None
    s1 = load_stage1_current(ticker, root)
    if s1:
        th = s1.get("thesis") or {}
        if isinstance(th, dict):
            thesis_summary = th.get("one_sentence") or th.get("customer_value_job")

    unresolved_conflict = False
    idx = storage.load_index(ticker, root)
    for p in idx.get("periods", []):
        for h in p.get("history", []):
            if h.get("status") == "conflict":
                unresolved_conflict = True

    report = evaluate_stage3(
        ticker,
        periods,
        gate0_class=gate0,
        sources=sources,
        semantic=semantic,
        thesis_summary=thesis_summary,
        unresolved_major_conflict=unresolved_conflict,
    )

    if not ok_gate:
        # evaluate_stage3 already TOO_HARD for non-operating; keep refuse_reason
        report.refuse_reason = report.refuse_reason or gate_msg

    md = render_stage3_markdown(report)
    save_stage3_report(ticker, report, root=root, markdown=md)

    meta = storage.load_meta(ticker, root)
    meta["stage3_process_outcome"] = report.process_outcome
    meta["stage3_terminates_later_stages"] = False
    storage.save_meta(ticker, meta, root)

    return AnalyzeResult(
        ticker=ticker,
        ok=True,
        refused=bool(report.refuse_reason) and gate0 != "operating",
        refuse_reason=report.refuse_reason if gate0 != "operating" else None,
        stage3=report,
        markdown=md,
        company_dir=str(cdir),
    )
