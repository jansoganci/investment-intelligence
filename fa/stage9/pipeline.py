"""run_stage9(ticker) — independent of final FA; not wired into fa.pipeline.analyze_company."""
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
from ..stage5.storage import load_stage5_current
from ..stage6.storage import load_stage6_current
from ..stage7.storage import load_stage7_current
from ..stage8.storage import load_stage8_current
from .evaluate import evaluate_stage9
from .report import render_stage9_markdown
from .semantic import (
    load_stage9_semantic_from_fixture,
    run_stage9_semantic_from_filings,
)
from .storage import save_stage9_report


def run_stage9(
    ticker: str,
    *,
    root: Path | None = None,
    fa_list_path: Path | None = None,
    semantic_notes_path: Path | None = None,
    require_fa_list: bool = True,
    force_primary: str | None = None,
    ensure_history: bool = True,
    prefer_fy: int = 5,
    prefer_q: int = 8,
) -> AnalyzeResult:
    """
    Run Stage 9 Industry / Competition / Macro / External Risk only.
    Refuses FI / non-operating Gate 0. Does not call or implement final FA synthesis.
    Does not redo Stage 5 pricing power / Stage 1 thesis / Stage 8 valuation.
    Consumes Stages 1–8 CURRENT artifacts as hypotheses / soft context.
    Does not mechanically terminate later stages.
    Independent like run_stage7/run_stage8 — not wired into analyze_company.
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

    explicit_semantic_fixture = semantic_notes_path is not None
    notes_path = semantic_notes_path
    if notes_path is None and not ensure_history:
        notes_dir = cdir / "Source" / "notes"
        if notes_dir.exists():
            preferred = [
                notes_dir / "stage9_semantic_review.json",
                *sorted(notes_dir.glob("*stage9*semantic*")),
            ]
            for cand in preferred:
                if cand.exists() and cand.is_file():
                    notes_path = cand
                    break

    filing_report = None
    if ensure_history and gate0 == "operating":
        try:
            filing_report = ensure_recent_sec_filings(
                ticker,
                root=root,
                max_filings=8,
                forms=("10-K", "10-Q", "20-F", "8-K"),
            )
        except Exception as e:  # noqa: BLE001
            filing_report = {
                "failed": [{"reason_code": "AUTOMATION_GAP", "detail": str(e)}]
            }

    semantic = None
    if notes_path and Path(notes_path).exists():
        semantic = load_stage9_semantic_from_fixture(Path(notes_path))
    if (
        semantic is None
        or not semantic.filled
        or (ensure_history and not explicit_semantic_fixture)
    ):
        semantic = run_stage9_semantic_from_filings(ticker, root=root, persist=True)

    thesis_summary = None
    business_notes = None
    s1 = load_stage1_current(ticker, root)
    if s1:
        th = s1.get("thesis") or {}
        if isinstance(th, dict):
            thesis_summary = th.get("one_sentence") or th.get("customer_value_job")
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

    s8 = load_stage8_current(ticker, root)
    s7 = load_stage7_current(ticker, root)
    s6 = load_stage6_current(ticker, root)
    s5 = load_stage5_current(ticker, root)
    s4 = load_stage4_current(ticker, root)

    prior_archetype = None
    for art, tag in (
        (s8, "stage8_reuse"),
        (s7, "stage7_reuse"),
        (s6, "stage6_reuse"),
        (s5, "stage5_reuse"),
        (s4, "stage4_reuse"),
    ):
        if art and isinstance(art.get("archetype"), dict) and art["archetype"].get(
            "primary_archetype"
        ):
            prior_archetype = dict(art["archetype"])
            prior_archetype["provenance"] = art["archetype"].get("provenance") or tag
            break

    unresolved_conflict = False
    idx = storage.load_index(ticker, root)
    for p in idx.get("periods", []):
        for h in p.get("history", []):
            if h.get("status") == "conflict":
                unresolved_conflict = True

    report = evaluate_stage9(
        ticker,
        periods,
        gate0_class=gate0,
        sources=sources,
        semantic=semantic,
        thesis_summary=thesis_summary,
        business_notes=business_notes,
        prior_archetype=prior_archetype,
        stage1_artifact=s1,
        stage4_artifact=s4,
        stage5_artifact=s5,
        stage6_artifact=s6,
        stage7_artifact=s7,
        stage8_artifact=s8,
        unresolved_major_conflict=unresolved_conflict,
        force_primary=force_primary,
    )

    if not ok_gate:
        report.refuse_reason = report.refuse_reason or gate_msg

    md = render_stage9_markdown(report)
    save_stage9_report(ticker, report, root=root, markdown=md)

    meta = storage.load_meta(ticker, root)
    meta["stage9_process_outcome"] = report.process_outcome
    meta["stage9_terminates_later_stages"] = False
    meta["stage9_no_final_fa_synthesis"] = True
    meta["stage9_s9_hfa_carries"] = report.s9_hfa_carries
    if history_report is not None:
        meta["stage9_history_coverage"] = {
            "created": history_report.get("created"),
            "updated_shares": history_report.get("updated_shares"),
            "discovery": history_report.get("discovery"),
            "failed": history_report.get("failed"),
        }
    if filing_report is not None:
        meta["stage9_filing_coverage"] = {
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
        stage9=report,
        markdown=md,
        company_dir=str(cdir),
    )
