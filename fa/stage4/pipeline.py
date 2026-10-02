"""run_stage4(ticker) — independent of Stage 5; not wired into fa.pipeline.analyze_company."""
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
from ..stage3.storage import load_stage3_current
from .evaluate import evaluate_stage4
from .report import render_stage4_markdown
from .semantic import (
    load_stage4_semantic_from_fixture,
    run_stage4_semantic_from_filings,
)
from .storage import save_stage4_report


def run_stage4(
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
    prefer_fy: int = 6,  # persist ≥6 FY when available so 5Y CAGR exhibit can form
    prefer_q: int = 8,
) -> AnalyzeResult:
    """
    Run Stage 4 Growth Quality / Runway only.
    Refuses FI / non-operating Gate 0. Does not call or implement Stage 5.
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

    history_report = None
    if ensure_history and gate0 == "operating":
        # Generic companyfacts backfill (~5 FY + ~8Q) + diluted WAD shares when available.
        # Does not invent figures; failures recorded as UNKNOWN reasons in report.
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
            # Prefer explicit Stage 4 pack only — never silently reuse Stage 2/3 semantic JSON
            preferred = [
                notes_dir / "stage4_semantic_review.json",
                *sorted(notes_dir.glob("*stage4*semantic*")),
                *sorted(notes_dir.glob("*stage4*")),
            ]
            for cand in preferred:
                if cand.exists() and cand.is_file():
                    notes_path = cand
                    break

    filing_report = None
    if ensure_history and gate0 == "operating":
        # Ticker-scoped 10-K/10-Q for semantic — never reuse another issuer's cache HTML
        try:
            filing_report = ensure_recent_sec_filings(ticker, root=root, max_filings=6)
        except Exception as e:  # noqa: BLE001
            filing_report = {
                "failed": [{"reason_code": "AUTOMATION_GAP", "detail": str(e)}]
            }

    semantic = None
    if notes_path and Path(notes_path).exists():
        semantic = load_stage4_semantic_from_fixture(Path(notes_path))
    if semantic is None or not semantic.filled:
        semantic = run_stage4_semantic_from_filings(ticker, root=root, persist=True)

    thesis_summary = None
    thesis_runway = None
    business_notes = None
    s1 = load_stage1_current(ticker, root)
    if s1:
        th = s1.get("thesis") or {}
        if isinstance(th, dict):
            thesis_summary = th.get("one_sentence") or th.get("customer_value_job")
            thesis_runway = th.get("runway_what")
            business_notes = " ".join(
                str(x)
                for x in (
                    th.get("customer_value_job"),
                    th.get("advantage_type"),
                    th.get("advantage_evidence"),
                    th.get("one_sentence"),
                )
                if x
            )

    # Optional Stage 3 FCF for per-share exhibit
    stage3_fcf: dict[str, float] = {}
    s3 = load_stage3_current(ticker, root)
    if s3:
        calc = (s3.get("calc") or {}).get("metrics") or {}
        for row in calc.get("per_period") or []:
            pk = row.get("period_key")
            fcf = row.get("fcf")
            if pk and fcf is not None:
                try:
                    stage3_fcf[pk] = float(fcf)
                except (TypeError, ValueError):
                    pass
        # Also from ocf_vs_ni / fcf series if present
        for row in calc.get("fcf_series") or []:
            pk = row.get("period_key")
            fcf = row.get("fcf") or row.get("value")
            if pk and fcf is not None and pk not in stage3_fcf:
                try:
                    stage3_fcf[pk] = float(fcf)
                except (TypeError, ValueError):
                    pass

    unresolved_conflict = False
    idx = storage.load_index(ticker, root)
    for p in idx.get("periods", []):
        for h in p.get("history", []):
            if h.get("status") == "conflict":
                unresolved_conflict = True

    report = evaluate_stage4(
        ticker,
        periods,
        gate0_class=gate0,
        sources=sources,
        semantic=semantic,
        thesis_summary=thesis_summary,
        thesis_runway=thesis_runway,
        business_notes=business_notes,
        unresolved_major_conflict=unresolved_conflict,
        extend_full_cycle=extend_full_cycle,
        stage3_fcf_by_period=stage3_fcf or None,
        peer_notes=peer_notes,
        force_primary=force_primary,
    )

    if not ok_gate:
        report.refuse_reason = report.refuse_reason or gate_msg

    md = render_stage4_markdown(report)
    save_stage4_report(ticker, report, root=root, markdown=md)

    meta = storage.load_meta(ticker, root)
    meta["stage4_process_outcome"] = report.process_outcome
    meta["stage4_terminates_later_stages"] = False
    if history_report is not None:
        meta["stage4_history_coverage"] = {
            "created": history_report.get("created"),
            "updated_shares": history_report.get("updated_shares"),
            "discovery": history_report.get("discovery"),
            "failed": history_report.get("failed"),
        }
    if filing_report is not None:
        meta["stage4_filing_coverage"] = {
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
        stage4=report,
        markdown=md,
        company_dir=str(cdir),
    )
