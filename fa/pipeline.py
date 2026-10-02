"""analyze_company(ticker) orchestration: Stage 1 gate → Stage 2. No Stage 3+."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config, storage, versioning
from .contract import blank_period_document, validate_gate0_operating
from .ids import normalize_ticker, utc_now
from .ingest import ingest_ir_doc, ingest_note, ingest_sec_filing
from .lists import NotOnFAListError, ensure_empty_production_list, require_on_fa_list
from .models import AnalyzeResult
from .stage1.evaluate import evaluate_stage1
from .stage1.pipeline import happy_path_payload_synth_opco, run_stage1
from .stage1.report import render_stage1_markdown
from .stage1.storage import load_stage1_current, save_stage1_report, stage1_process_outcome
from .stage2.storage import save_stage2_report
from .stage2.evaluate import evaluate_stage2
from .stage2.report import render_stage2_markdown
from .stage2.semantic import load_semantic_from_fixture_notes


def _load_fixture_periods(ticker: str) -> tuple[list[dict], list[str], Path | None]:
    """Load synthetic Normalized periods + sources from fa_fixtures."""
    base = config.SYNTH_COMPANY_DIR
    periods_dir = base / "expected_periods"
    periods: list[dict] = []
    sources: list[str] = []
    if periods_dir.exists():
        for p in sorted(periods_dir.glob("*.json")):
            doc = json.loads(p.read_text(encoding="utf-8"))
            periods.append(doc)
    # Source stubs
    filings = base / "Source" / "filings"
    if filings.exists():
        for f in sorted(filings.iterdir()):
            sources.append(f.name)
    notes_path = base / "Source" / "notes" / "semantic_review.json"
    return periods, sources, notes_path if notes_path.exists() else None


def seed_from_fixtures(ticker: str, root: Path | None = None) -> Path:
    """Copy/seed fixture company into FA_ROOT companies layout (for dry-run)."""
    ticker = normalize_ticker(ticker)
    root = root or config.FA_ROOT
    cdir = storage.ensure_company_layout(ticker, root, entity_name="Synthetic Operating Co")

    meta = storage.load_meta(ticker, root)
    meta["gate0_class"] = "operating"
    meta["entity_name"] = "Synthetic Operating Co"
    meta["synthetic_demo"] = True
    storage.save_meta(ticker, meta, root)

    periods, _sources, notes_path = _load_fixture_periods(ticker)
    for doc in periods:
        pk = doc["period_key"]
        # write via versioning if not present
        existing = storage.load_current_period(ticker, pk, root)
        if existing is None:
            versioning.create_initial_version(ticker, pk, doc, accept=True, root=root)

    # Ingest fixture source stubs idempotently
    filings = config.SYNTH_COMPANY_DIR / "Source" / "filings"
    if filings.exists():
        for fpath in sorted(filings.glob("*")):
            raw = fpath.read_text(encoding="utf-8")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"raw": raw}
            acc = payload.get("accession") or f"FIX-{fpath.stem}"
            form = payload.get("form") or "10-K"
            ingest_sec_filing(
                ticker,
                accession=acc,
                form=form,
                filed_at=payload.get("filed_at"),
                content=raw,
                content_filename=fpath.name,
                root=root,
            )

    ir_dir = config.SYNTH_COMPANY_DIR / "Source" / "ir"
    if ir_dir.exists():
        for fpath in sorted(ir_dir.glob("*")):
            content = fpath.read_text(encoding="utf-8")
            ingest_ir_doc(
                ticker,
                logical_name=fpath.stem,
                as_of_date="2025-12-31",
                content=content,
                filename=fpath.name,
                root=root,
            )

    if notes_path and notes_path.exists():
        ingest_note(
            ticker,
            logical_name="semantic_review",
            content=notes_path.read_text(encoding="utf-8"),
            root=root,
        )

    # Seed Stage 1 PROCEED for synthetic dry-run so Stage 2 gate can open
    if load_stage1_current(ticker, root) is None:
        s1 = evaluate_stage1(ticker, happy_path_payload_synth_opco())
        md1 = render_stage1_markdown(s1)
        save_stage1_report(ticker, s1, root=root, markdown=md1)
        meta = storage.load_meta(ticker, root)
        meta["stage1_process_outcome"] = s1.process_outcome
        meta["gate0_class"] = s1.gate0_class
        storage.save_meta(ticker, meta, root)

    return cdir


def analyze_company(
    ticker: str,
    *,
    root: Path | None = None,
    use_fixtures: bool | None = None,
    fa_list_path: Path | None = None,
    seed: bool = True,
) -> AnalyzeResult:
    """
    Orchestrate FA analyze for a ticker through Stage 2 only.
    Refuses if not on FA List.
    If Stage 2 outcome blocks → do not proceed to Stage 3+ (no stage3 exists).
    """
    ticker = normalize_ticker(ticker)
    root = root or config.FA_ROOT
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

    if use_fixtures is None:
        use_fixtures = bool(entry.synthetic_demo) or ticker.startswith("SYNTH")

    if use_fixtures and seed:
        seed_from_fixtures(ticker, root=root)
    else:
        storage.ensure_company_layout(ticker, root, entity_name=entry.name)

    meta = storage.load_meta(ticker, root)
    gate0 = meta.get("gate0_class") or entry.gate0_class or "operating"
    cdir = storage.company_dir(ticker, root)

    # --- Stage 1 gate: Stage 2 calc refused unless Stage 1 PROCEED ---
    s1_outcome = stage1_process_outcome(ticker, root)
    if s1_outcome != "PROCEED":
        reason = (
            "Stage 1 missing — run Stage 1 (Gates 0–2) and obtain PROCEED before Stage 2"
            if s1_outcome is None
            else (
                f"Stage 2 blocked: Stage 1 process_outcome={s1_outcome} "
                "(requires PROCEED)"
            )
        )
        # Rebuild Stage1Report-ish markdown if present
        md_block = (
            f"# Stage 2 blocked for {ticker}\n\n"
            f"{reason}\n\n"
            f"Stage 1 outcome: {s1_outcome or '(missing)'}\n"
        )
        return AnalyzeResult(
            ticker=ticker,
            ok=True,
            refused=False,
            stage1=None,
            stage2=None,
            markdown=md_block,
            company_dir=str(cdir),
            stage2_blocked=True,
            stage2_block_reason=reason,
        )

    ok_gate, gate_msg = validate_gate0_operating({"gate0_class": gate0})
    periods = storage.load_all_current_periods(ticker, root)

    # Sources from manifest
    man = storage.load_source_manifest(ticker, root)
    sources = [s.get("source_id") or s.get("path") or "" for s in man.get("sources", [])]

    notes_path = storage.company_dir(ticker, root) / "Source" / "notes"
    semantic_file = None
    if notes_path.exists():
        for cand in notes_path.glob("*semantic*"):
            semantic_file = cand
            break
    if semantic_file is None and use_fixtures:
        fix_notes = config.SYNTH_COMPANY_DIR / "Source" / "notes" / "semantic_review.json"
        if fix_notes.exists():
            semantic_file = fix_notes

    semantic = None
    if semantic_file:
        semantic = load_semantic_from_fixture_notes(semantic_file)

    unresolved_conflict = False
    # detect conflict status in index
    idx = storage.load_index(ticker, root)
    for p in idx.get("periods", []):
        for h in p.get("history", []):
            if h.get("status") == "conflict":
                unresolved_conflict = True

    missing_critical = not ok_gate or not periods

    report = evaluate_stage2(
        ticker,
        periods,
        gate0_class=gate0,
        sources=sources,
        semantic=semantic,
        unresolved_major_conflict=unresolved_conflict,
        missing_critical_evidence=missing_critical and gate0 == "operating" and not periods,
    )

    # If wrong gate0, force TOO_HARD (evaluate also handles)
    if not ok_gate:
        report.process_outcome = "TOO_HARD"
        report.block_next = True
        report.block_reasons.append(gate_msg or "non-operating")
        report.enough_to_proceed = "No"
        report.enough_why = gate_msg or "non-operating"
        report.narrative_verdict = "Not enough evidence to proceed (REVIEW / TOO HARD)"

    md = render_stage2_markdown(report)

    # Persist Thesis CURRENT + versions + Generated mirror (registry hook inside storage)
    save_stage2_report(ticker, report, root=root, markdown=md)

    # Explicit: no Stage 3 call — assert absence by not importing/calling any stage3
    assert not hasattr(analyze_company, "stage3")  # belt-and-suspenders

    if report.block_next or report.process_outcome in {
        "TOO_HARD",
        "BLOCKED_BY_MATERIAL_FINANCIAL_FRAGILITY",
        "REVIEW_REQUIRED",
    }:
        # REVIEW_REQUIRED only stops Stage 3+ when block_next True
        if report.process_outcome == "REVIEW_REQUIRED" and not report.block_next:
            pass
        else:
            # stop — no further stages
            pass

    return AnalyzeResult(
        ticker=ticker,
        ok=True,
        refused=False,
        stage2=report,
        markdown=md,
        company_dir=str(cdir),
        stage2_blocked=False,
        stage2_block_reason=None,
    )


def dry_run_synth_opco(root: Path | None = None) -> AnalyzeResult:
    """Convenience dry-run for SYNTH_OPCO using fixture FA list."""
    return analyze_company(
        "SYNTH_OPCO",
        root=root,
        use_fixtures=True,
        fa_list_path=config.DEMO_FA_LIST,
        seed=True,
    )


def dry_run_stage1_synth_opco(root: Path | None = None) -> AnalyzeResult:
    """Convenience Stage 1 dry-run for SYNTH_OPCO using fixture FA list."""
    return run_stage1(
        "SYNTH_OPCO",
        happy_path_payload_synth_opco(),
        root=root,
        fa_list_path=config.DEMO_FA_LIST,
    )
