"""run_stage1(ticker, payload) — FA List gate + evaluate + persist."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config, storage
from ..ids import normalize_ticker
from ..lists import NotOnFAListError, ensure_empty_production_list, require_on_fa_list
from ..models import AnalyzeResult, Stage1Report
from .evaluate import evaluate_stage1
from .report import render_stage1_markdown
from .storage import save_stage1_report


def run_stage1(
    ticker: str,
    payload: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    fa_list_path: Path | None = None,
) -> AnalyzeResult:
    """
    Run Stage 1 Gates 0–2 for a ticker.
    Refuses if not on FA List. Persists Thesis/stage1_CURRENT.json.
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

    storage.ensure_company_layout(ticker, root, entity_name=entry.name)
    payload = dict(payload or {})
    # Default gate0 from list/meta if not in payload
    if not payload.get("gate0_class") and "G0-M1" not in (payload.get("answers") or {}):
        meta = storage.load_meta(ticker, root)
        payload.setdefault(
            "gate0_class",
            meta.get("gate0_class") or entry.gate0_class or "operating",
        )

    report = evaluate_stage1(ticker, payload)
    md = render_stage1_markdown(report)
    save_stage1_report(ticker, report, root=root, markdown=md)
    cdir = storage.company_dir(ticker, root)

    # Sync meta gate0
    meta = storage.load_meta(ticker, root)
    meta["gate0_class"] = report.gate0_class
    meta["stage1_process_outcome"] = report.process_outcome
    storage.save_meta(ticker, meta, root)

    return AnalyzeResult(
        ticker=ticker,
        ok=True,
        refused=False,
        stage1=report,
        markdown=md,
        company_dir=str(cdir),
        stage2_blocked=report.block_stage2,
        stage2_block_reason=None
        if report.process_outcome == "PROCEED"
        else f"Stage 1 process_outcome={report.process_outcome}",
    )


def happy_path_payload_synth_opco() -> dict[str, Any]:
    """Synthetic fixture answers that evaluate to PROCEED (for dry-run / tests)."""
    return {
        "gate0_class": "operating",
        "answers": {
            "G1-M1": "Sells industrial fasteners and related kits to OEMs and distributors in NA/EU.",
            "G1-M2": "Customers pay for reliable on-time supply and application engineering that reduces line downtime.",
            "G1-M3": "Revenue mostly from fasteners (~70%) plus kits/tools (~20%) and services (~10%); NA primary, EU secondary.",
            "G1-M4": "Buys steel inputs, manufactures/specs fasteners at scale, sells sticky OEM programs with recurring replenishment cash.",
            "G1-M5": "OEM production volumes; steel input costs; distributor inventory cycles; share of wallet on platforms.",
            "G1-M6": "Category competitors: large fastener majors and regional specialists; substitutes include redesign to adhesives/clips.",
            "G1-M7": [
                "Major OEM dual-sources away >20% of program revenue",
                "Gross margin compression without volume offset for 4+ quarters",
                "Loss of engineering-spec position on next platform generation",
            ],
            "G1-M8": "Yes — willing to track OEM volumes, margins, and program wins/losses within weekly research budget.",
            "G1-S1": "Volume from OEM builds; price/mix from specialty kits; geography from EU expansion.",
            "G2-M1": "Keeps OEM lines running with qualified parts and engineering support competitors struggle to match at same lead time.",
            "G2-M2": "Switching costs + scale/cost in qualified OEM programs; process know-how on specs.",
            "G2-M3": "Requalification cost and dual-source friction sustain advantage over 5–15 years absent platform redesign.",
            "G2-M4": "More content per platform, adjacent kits, selective EU OEM wins; multi-year runway medium confidence.",
            "G2-M5": "Reinvest in capacity and engineering; modest dividends; bolt-ons rare and small.",
            "G2-M6": "Hybrid — manufacturing CapEx needed but programs are sticky; not pure capital-light software.",
            "G2-M7": [
                "OEM vertical integration or mega-distributor squeeze",
                "Material substitution obsolete core SKUs",
            ],
            "G2-M8": "Stable/improving gross margin with volume; healthy WC; CapEx consistent with capacity narrative — no thresholds yet.",
        },
        "thesis": {
            "one_sentence": (
                "I want to own this business because it creates durable customer value by keeping OEM lines "
                "running via qualified supply and engineering, defended by switching costs and scale."
            ),
            "customer_value_job": "Reliable qualified fasteners that prevent downtime",
            "customer_value_why": "Spec position + lead time + engineering support",
            "advantage_type": "Switching costs and scale/cost on qualified OEM programs",
            "advantage_persist": "Requalification friction over multi-year platforms",
            "advantage_evidence": "Long program tenures (qualitative fixture)",
            "runway_what": "Content per platform + selective geography",
            "runway_confidence": "medium",
            "reinvestment_where": "Capacity and application engineering",
            "capital_intensity": "hybrid",
            "kill_shot_primary": "OEM dual-source or vertical integration",
            "kill_shot_secondary": "Material substitution wave",
            "monitors": [
                "OEM program win/loss",
                "Gross margin vs steel",
                "WC turns",
            ],
            "financial_validation_later": [
                "Margins consistent with sticky programs",
                "CapEx matches capacity story",
            ],
            "language": "EN",
        },
    }
