"""run_final_fa(ticker) — consume Stage 1–9 CURRENT only; emit Final FA artifact.

Does not redesign or rewrite Stages 1–9. Does not run UAT.
Stops at eligibility packet (no watchlist / TA / portfolio).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config, storage
from ..ids import normalize_ticker
from ..stage1.storage import load_stage1_current, stage1_current_path
from ..stage2.storage import load_stage2_current, stage2_current_path
from ..stage3.storage import load_stage3_current, stage3_current_path
from ..stage4.storage import load_stage4_current, stage4_current_path
from ..stage5.storage import load_stage5_current, stage5_current_path
from ..stage6.storage import load_stage6_current, stage6_current_path
from ..stage7.storage import load_stage7_current, stage7_current_path
from ..stage8.storage import load_stage8_current, stage8_current_path
from ..stage9.storage import load_stage9_current, stage9_current_path
from .evaluate import evaluate_final_fa
from .models import FinalFaSynthesis
from .report import render_final_fa_markdown
from .storage import final_fa_current_path, save_final_fa_report


def load_stage_currents(
    ticker: str,
    root: Path | None = None,
) -> tuple[dict[int, dict[str, Any] | None], dict[str, str | None]]:
    """Load Stage 1–9 CURRENT artifacts only (None if missing). Never invent."""
    loaders = {
        1: (load_stage1_current, stage1_current_path),
        2: (load_stage2_current, stage2_current_path),
        3: (load_stage3_current, stage3_current_path),
        4: (load_stage4_current, stage4_current_path),
        5: (load_stage5_current, stage5_current_path),
        6: (load_stage6_current, stage6_current_path),
        7: (load_stage7_current, stage7_current_path),
        8: (load_stage8_current, stage8_current_path),
        9: (load_stage9_current, stage9_current_path),
    }
    stages: dict[int, dict[str, Any] | None] = {}
    paths: dict[str, str | None] = {}
    for n, (load_fn, path_fn) in loaders.items():
        p = path_fn(ticker, root)
        paths[f"s{n}"] = str(p) if p.exists() else None
        stages[n] = load_fn(ticker, root)
    return stages, paths


def run_final_fa(
    ticker: str,
    *,
    root: Path | None = None,
    as_of: str | None = None,
    persist: bool = True,
    register: bool = True,
    skip_registry: bool = False,
    raise_on_registry_error: bool = False,
    uat_status: str | None = None,
    stage_result_ids_consumed: list[str] | None = None,
) -> dict[str, Any]:
    """
    Synthesize Final FA from Stage CURRENT artifacts.

    Returns dict with keys: ok, ticker, synthesis (dict), markdown, save (optional).
    """
    ticker = normalize_ticker(ticker)
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)

    stages, paths = load_stage_currents(ticker, root)
    synthesis: FinalFaSynthesis = evaluate_final_fa(
        ticker,
        stages,
        as_of=as_of,
        stage_paths=paths,
    )
    markdown = render_final_fa_markdown(synthesis)
    doc = synthesis.to_dict()

    result: dict[str, Any] = {
        "ok": True,
        "ticker": ticker,
        "synthesis": doc,
        "markdown": markdown,
        "final_state": synthesis.final_state,
        "technical_eligible": synthesis.technical_eligible,
        "path": str(final_fa_current_path(ticker, root)),
    }

    if persist:
        save_info = save_final_fa_report(
            ticker,
            doc,
            root=root,
            markdown=markdown,
            register=register,
            skip_registry=skip_registry,
            raise_on_registry_error=raise_on_registry_error,
            uat_status=uat_status,
            stage_result_ids_consumed=stage_result_ids_consumed,
        )
        # Stamp version into provenance on the in-memory copy
        doc.setdefault("provenance", {})["final_fa_version"] = save_info.get("version_id")
        result["save"] = save_info
        result["synthesis"] = doc

    return result
