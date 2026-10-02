"""run_stage8(ticker) — independent of Stage 9; not wired into fa.pipeline.analyze_company."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config, storage
from ..contract import validate_gate0_operating
from ..history_coverage import ensure_normalized_history
from ..ids import normalize_ticker
from ..lists import NotOnFAListError, ensure_empty_production_list, require_on_fa_list
from ..models import AnalyzeResult
from ..stage1.storage import load_stage1_current
from ..stage4.storage import load_stage4_current
from ..stage6.storage import load_stage6_current
from ..stage7.storage import load_stage7_current
from .evaluate import evaluate_stage8
from .report import render_stage8_markdown
from .semantic import load_stage8_semantic_from_fixture
from .storage import save_stage8_report


def run_stage8(
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
    market_price: float | None = None,
    price_currency: str | None = "USD",
    price_as_of: str | None = None,
    price_source: str | None = None,
    price_delay_note: str | None = None,
    post_period_events: list[str] | None = None,
    selective_extend: bool = False,
) -> AnalyzeResult:
    """
    Run Stage 8 Valuation / IV / MoS only.
    Refuses FI / non-operating Gate 0. Does not call or implement Stage 9.
    Does not recompute ROIC/ROIIC/WACC. Consumes Stages 4/6/7 CURRENT artifacts.
    Does not mechanically terminate later stages.
    Independent like run_stage7 — not wired into analyze_company.

    Optional market_price / price_as_of / price_source for UAT with explicit provenance.
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

    semantic = None
    notes_path = semantic_notes_path
    if notes_path is None:
        notes_dir = cdir / "Source" / "notes"
        if notes_dir.exists():
            preferred = [
                notes_dir / "stage8_semantic_review.json",
                *sorted(notes_dir.glob("*stage8*semantic*")),
            ]
            for cand in preferred:
                if cand.exists() and cand.is_file():
                    notes_path = cand
                    break
    if notes_path and Path(notes_path).exists():
        semantic = load_stage8_semantic_from_fixture(Path(notes_path))

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
                    th.get("capital_intensity"),
                    th.get("capital_destination"),
                )
                if x
            )

    # Prefer Stage 7 archetype, else Stage 6, else Stage 4
    prior_archetype = None
    s7 = load_stage7_current(ticker, root)
    s6 = load_stage6_current(ticker, root)
    s4 = load_stage4_current(ticker, root)
    if s7 and isinstance(s7.get("archetype"), dict) and s7["archetype"].get(
        "primary_archetype"
    ):
        prior_archetype = dict(s7["archetype"])
        prior_archetype["provenance"] = s7["archetype"].get("provenance") or "stage7_reuse"
    elif s6 and isinstance(s6.get("archetype"), dict) and s6["archetype"].get(
        "primary_archetype"
    ):
        prior_archetype = dict(s6["archetype"])
        prior_archetype["provenance"] = s6["archetype"].get("provenance") or "stage6_reuse"
    elif s4 and isinstance(s4.get("archetype"), dict):
        prior_archetype = s4["archetype"]

    unresolved_conflict = False
    idx = storage.load_index(ticker, root)
    for p in idx.get("periods", []):
        for h in p.get("history", []):
            if h.get("status") == "conflict":
                unresolved_conflict = True

    report = evaluate_stage8(
        ticker,
        periods,
        gate0_class=gate0,
        sources=sources,
        semantic=semantic,
        market_price=market_price,
        price_currency=price_currency,
        price_as_of=price_as_of,
        price_source=price_source,
        price_delay_note=price_delay_note,
        post_period_events=post_period_events,
        thesis_summary=thesis_summary,
        business_notes=business_notes,
        prior_archetype=prior_archetype,
        stage4_artifact=s4,
        stage6_artifact=s6,
        stage7_artifact=s7,
        unresolved_major_conflict=unresolved_conflict,
        force_primary=force_primary,
        selective_extend=selective_extend,
    )

    if not ok_gate:
        report.refuse_reason = report.refuse_reason or gate_msg

    md = render_stage8_markdown(report)
    save_stage8_report(ticker, report, root=root, markdown=md)

    meta = storage.load_meta(ticker, root)
    meta["stage8_process_outcome"] = report.process_outcome
    meta["stage8_terminates_later_stages"] = False
    meta["stage8_staleness_class"] = report.staleness_class
    meta["stage8_expectations_label"] = report.expectations_label
    meta["stage8_uncertainty_label"] = report.uncertainty_label
    if history_report is not None:
        meta["stage8_history_coverage"] = {
            "created": history_report.get("created"),
            "updated_shares": history_report.get("updated_shares"),
            "discovery": history_report.get("discovery"),
            "failed": history_report.get("failed"),
        }
    storage.save_meta(ticker, meta, root)

    return AnalyzeResult(
        ticker=ticker,
        ok=True,
        refused=bool(report.refuse_reason) and gate0 != "operating",
        refuse_reason=report.refuse_reason if gate0 != "operating" else None,
        stage8=report,
        markdown=md,
        company_dir=str(cdir),
    )
