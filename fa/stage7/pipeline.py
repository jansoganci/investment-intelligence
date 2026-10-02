"""run_stage7(ticker) — independent of Stage 8; not wired into fa.pipeline.analyze_company."""
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
from .evaluate import evaluate_stage7
from .report import render_stage7_markdown
from .semantic import (
    load_stage7_semantic_from_fixture,
    run_stage7_semantic_from_filings,
)
from .storage import save_stage7_report


def run_stage7(
    ticker: str,
    *,
    root: Path | None = None,
    fa_list_path: Path | None = None,
    semantic_notes_path: Path | None = None,
    require_fa_list: bool = True,
    peer_notes: str | None = None,
    force_primary: str | None = None,
    ensure_history: bool = True,
    prefer_fy: int = 5,
    prefer_q: int = 8,
) -> AnalyzeResult:
    """
    Run Stage 7 Management / Capital Allocation only.
    Refuses FI / non-operating Gate 0. Does not call or implement Stage 8.
    Does not recompute ROIC/ROIIC/WACC. Consumes Stage 6 S6_H7_* factually only.
    Does not mechanically terminate later stages.
    Independent like run_stage6 — not wired into analyze_company.
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

    # Explicit fixture path only — do NOT treat a prior persist as authoritative when
    # ensure_history=True (stale notes can freeze opaque MG1 after DEF 14A becomes cached).
    explicit_semantic_fixture = semantic_notes_path is not None
    notes_path = semantic_notes_path
    if notes_path is None and not ensure_history:
        notes_dir = cdir / "Source" / "notes"
        if notes_dir.exists():
            preferred = [
                notes_dir / "stage7_semantic_review.json",
                *sorted(notes_dir.glob("*stage7*semantic*")),
                *sorted(notes_dir.glob("*stage7*")),
            ]
            for cand in preferred:
                if cand.exists() and cand.is_file():
                    notes_path = cand
                    break

    filing_report = None
    if ensure_history and gate0 == "operating":
        try:
            # Prefer including DEF 14A when coverage helper supports broader forms;
            # fall back to recent filings (10-K/Q) like Stage 6.
            filing_report = ensure_recent_sec_filings(
                ticker,
                root=root,
                max_filings=10,
                forms=("10-K", "10-Q", "20-F", "DEF 14A", "DEFA14A", "8-K"),
            )
        except Exception as e:  # noqa: BLE001
            filing_report = {
                "failed": [{"reason_code": "AUTOMATION_GAP", "detail": str(e)}]
            }

    semantic = None
    if notes_path and Path(notes_path).exists():
        semantic = load_stage7_semantic_from_fixture(Path(notes_path))
    # Production-like (ensure_history): always re-scan filings so newly cached DEF 14A /
    # pattern fixes refresh stated_hierarchy — unless caller passed an explicit fixture.
    if (
        semantic is None
        or not semantic.filled
        or (ensure_history and not explicit_semantic_fixture)
    ):
        semantic = run_stage7_semantic_from_filings(ticker, root=root, persist=True)

    thesis_summary = None
    thesis_capital = None
    business_notes = None
    s1 = load_stage1_current(ticker, root)
    if s1:
        th = s1.get("thesis") or {}
        if isinstance(th, dict):
            thesis_summary = th.get("one_sentence") or th.get("customer_value_job")
            thesis_capital = (
                th.get("capital_destination")
                or th.get("capital_intensity")
                or th.get("reinvestment_note")
            )
            business_notes = " ".join(
                str(x)
                for x in (
                    th.get("customer_value_job"),
                    th.get("advantage_type"),
                    th.get("advantage_evidence"),
                    th.get("one_sentence"),
                    th.get("capital_intensity"),
                    th.get("capital_destination"),
                )
                if x
            )

    # Prefer Stage 6 archetype, else Stage 5, else Stage 4
    prior_archetype = None
    s6 = load_stage6_current(ticker, root)
    if s6 and isinstance(s6.get("archetype"), dict) and s6["archetype"].get(
        "primary_archetype"
    ):
        prior_archetype = dict(s6["archetype"])
        prior_archetype["provenance"] = s6["archetype"].get("provenance") or "stage6_reuse"
    else:
        s5 = load_stage5_current(ticker, root)
        if s5 and isinstance(s5.get("archetype"), dict) and s5["archetype"].get(
            "primary_archetype"
        ):
            prior_archetype = dict(s5["archetype"])
            prior_archetype["provenance"] = "stage5_reuse"
        else:
            s4 = load_stage4_current(ticker, root)
            if s4 and isinstance(s4.get("archetype"), dict):
                prior_archetype = s4["archetype"]

    unresolved_conflict = False
    idx = storage.load_index(ticker, root)
    for p in idx.get("periods", []):
        for h in p.get("history", []):
            if h.get("status") == "conflict":
                unresolved_conflict = True

    report = evaluate_stage7(
        ticker,
        periods,
        gate0_class=gate0,
        sources=sources,
        semantic=semantic,
        thesis_summary=thesis_summary,
        thesis_capital=thesis_capital,
        business_notes=business_notes,
        prior_archetype=prior_archetype,
        stage6_artifact=s6,
        unresolved_major_conflict=unresolved_conflict,
        peer_notes=peer_notes,
        force_primary=force_primary,
    )

    if not ok_gate:
        report.refuse_reason = report.refuse_reason or gate_msg

    md = render_stage7_markdown(report)
    save_stage7_report(ticker, report, root=root, markdown=md)

    meta = storage.load_meta(ticker, root)
    meta["stage7_process_outcome"] = report.process_outcome
    meta["stage7_terminates_later_stages"] = False
    if history_report is not None:
        meta["stage7_history_coverage"] = {
            "created": history_report.get("created"),
            "updated_shares": history_report.get("updated_shares"),
            "discovery": history_report.get("discovery"),
            "failed": history_report.get("failed"),
        }
    if filing_report is not None:
        meta["stage7_filing_coverage"] = {
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
        stage7=report,
        markdown=md,
        company_dir=str(cdir),
    )
