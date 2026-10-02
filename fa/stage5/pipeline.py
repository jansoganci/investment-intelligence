"""run_stage5(ticker) — independent of Stage 6; not wired into fa.pipeline.analyze_company."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config, storage
from ..contract import validate_gate0_operating
from ..filing_coverage import ensure_recent_sec_filings
from ..history_coverage import ensure_normalized_history
from ..ids import normalize_ticker
from ..lists import NotOnFAListError, ensure_empty_production_list, require_on_fa_list
from ..models import AnalyzeResult
from ..stage1.storage import load_stage1_current
from ..stage4.storage import load_stage4_current
from .evaluate import evaluate_stage5
from .report import render_stage5_markdown
from .semantic import (
    load_stage5_semantic_from_fixture,
    run_stage5_semantic_from_filings,
)
from .storage import save_stage5_report


def run_stage5(
    ticker: str,
    *,
    root: Path | None = None,
    fa_list_path: Path | None = None,
    semantic_notes_path: Path | None = None,
    require_fa_list: bool = True,
    extend_full_cycle: bool = False,
    peer_notes: str | None = None,
    force_primary: str | None = None,
    ensure_history: bool = True,
    prefer_fy: int = 5,
    prefer_q: int = 8,
) -> AnalyzeResult:
    """
    Run Stage 5 Margins / Business Economics only.
    Refuses FI / non-operating Gate 0. Does not call or implement Stage 6.
    Does not mechanically terminate later stages.
    Reuses Stage 4 archetype when present. No numeric bands. No BE9.
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

    history_report = None
    if ensure_history and gate0 == "operating":
        try:
            history_report = ensure_normalized_history(
                ticker,
                root=root,
                prefer_fy=prefer_fy,
                prefer_q=prefer_q,
                accept=True,
            )
        except Exception as e:  # noqa: BLE001
            history_report = {
                "failed": [{"reason_code": "AUTOMATION_GAP", "detail": str(e)}]
            }

    periods = storage.load_all_current_periods(ticker, root)

    man = storage.load_source_manifest(ticker, root)
    sources = [s.get("source_id") or s.get("path") or "" for s in man.get("sources", [])]

    notes_path = semantic_notes_path
    if notes_path is None:
        notes_dir = cdir / "Source" / "notes"
        if notes_dir.exists():
            preferred = [
                notes_dir / "stage5_semantic_review.json",
                *sorted(notes_dir.glob("*stage5*semantic*")),
                *sorted(notes_dir.glob("*stage5*")),
            ]
            for cand in preferred:
                if cand.exists() and cand.is_file():
                    notes_path = cand
                    break

    filing_report = None
    if ensure_history and gate0 == "operating":
        try:
            filing_report = ensure_recent_sec_filings(ticker, root=root, max_filings=6)
        except Exception as e:  # noqa: BLE001
            filing_report = {
                "failed": [{"reason_code": "AUTOMATION_GAP", "detail": str(e)}]
            }

    semantic = None
    if notes_path and Path(notes_path).exists():
        semantic = load_stage5_semantic_from_fixture(Path(notes_path))
    if semantic is None or not semantic.filled:
        semantic = run_stage5_semantic_from_filings(ticker, root=root, persist=True)

    thesis_summary = None
    thesis_margins = None
    business_notes = None
    s1 = load_stage1_current(ticker, root)
    if s1:
        th = s1.get("thesis") or {}
        if isinstance(th, dict):
            thesis_summary = th.get("one_sentence") or th.get("customer_value_job")
            thesis_margins = th.get("margins_note") or th.get("advantage_evidence")
            business_notes = " ".join(
                str(x)
                for x in (
                    th.get("customer_value_job"),
                    th.get("advantage_type"),
                    th.get("advantage_evidence"),
                    th.get("one_sentence"),
                    th.get("margins_note"),
                )
                if x
            )

    stage4_archetype = None
    s4 = load_stage4_current(ticker, root)
    if s4 and isinstance(s4.get("archetype"), dict):
        stage4_archetype = s4["archetype"]

    unresolved_conflict = False
    idx = storage.load_index(ticker, root)
    for p in idx.get("periods", []):
        for h in p.get("history", []):
            if h.get("status") == "conflict":
                unresolved_conflict = True

    report = evaluate_stage5(
        ticker,
        periods,
        gate0_class=gate0,
        sources=sources,
        semantic=semantic,
        thesis_summary=thesis_summary,
        thesis_margins=thesis_margins,
        business_notes=business_notes,
        stage4_archetype=stage4_archetype,
        unresolved_major_conflict=unresolved_conflict,
        extend_full_cycle=extend_full_cycle,
        peer_notes=peer_notes,
        force_primary=force_primary,
    )

    if not ok_gate:
        report.refuse_reason = report.refuse_reason or gate_msg

    md = render_stage5_markdown(report)
    save_stage5_report(ticker, report, root=root, markdown=md)

    meta = storage.load_meta(ticker, root)
    meta["stage5_process_outcome"] = report.process_outcome
    meta["stage5_terminates_later_stages"] = False
    if history_report is not None:
        meta["stage5_history_coverage"] = {
            "created": history_report.get("created"),
            "updated_shares": history_report.get("updated_shares"),
            "discovery": history_report.get("discovery"),
            "failed": history_report.get("failed"),
        }
    if filing_report is not None:
        meta["stage5_filing_coverage"] = {
            "created": filing_report.get("created"),
            "existing": filing_report.get("existing"),
            "downloaded": filing_report.get("downloaded"),
            "failed": filing_report.get("failed"),
            "cik": filing_report.get("cik"),
        }
    storage.save_meta(ticker, meta, root)

    return AnalyzeResult(
        ticker=ticker,
        ok=True,
        refused=bool(report.refuse_reason) and gate0 != "operating",
        refuse_reason=report.refuse_reason if gate0 != "operating" else None,
        stage5=report,
        markdown=md,
        company_dir=str(cdir),
    )
