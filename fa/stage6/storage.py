"""Persist Stage 6 reports under company Thesis/ + Generated/."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import storage as fa_storage
from ..ids import normalize_ticker, utc_now
from ..models import Stage6Report


def thesis_dir(ticker: str, root: Path | None = None) -> Path:
    return fa_storage.company_dir(ticker, root) / "Thesis"


def stage6_current_path(ticker: str, root: Path | None = None) -> Path:
    return thesis_dir(ticker, root) / "stage6_CURRENT.json"


def stage6_versions_dir(ticker: str, root: Path | None = None) -> Path:
    return thesis_dir(ticker, root) / "stage6_versions"


def save_stage6_report(
    ticker: str,
    report: Stage6Report,
    *,
    root: Path | None = None,
    markdown: str | None = None,
    register: bool = True,
    raise_on_registry_error: bool = False,
    uat_status: str | None = None,
    skip_registry: bool = False,
) -> dict[str, Any]:
    """Write Thesis/stage6_CURRENT.json + versioned copy + Generated mirror."""
    ticker = normalize_ticker(ticker)
    fa_storage.ensure_company_layout(ticker, root)
    tdir = thesis_dir(ticker, root)
    tdir.mkdir(parents=True, exist_ok=True)
    vdir = stage6_versions_dir(ticker, root)
    vdir.mkdir(parents=True, exist_ok=True)

    existing = sorted(vdir.glob("stage6_v*.json"))
    n = len(existing) + 1
    version_id = f"v{n:03d}"
    version_name = f"stage6_{version_id}.json"

    doc = report.to_dict()
    doc["version_id"] = version_id
    doc["saved_at"] = utc_now()

    version_json = vdir / version_name
    fa_storage.write_json(version_json, doc)
    fa_storage.write_json(stage6_current_path(ticker, root), doc)

    md_abs: Path | None = None
    if markdown is not None:
        md_abs = tdir / "stage6_CURRENT.md"
        md_abs.write_text(markdown, encoding="utf-8")
        (vdir / f"stage6_{version_id}.md").write_text(markdown, encoding="utf-8")
        cdir = fa_storage.company_dir(ticker, root)
        gen = cdir / "Generated"
        gen.mkdir(parents=True, exist_ok=True)
        (gen / "stage6_report.md").write_text(markdown, encoding="utf-8")
        fa_storage.write_json(gen / "stage6_report.json", doc)

    from ..registry.hooks import hook_stage_after_save

    hook_stage_after_save(
        ticker=ticker,
        stage=6,
        version_id=version_id,
        artifact_json_abs=version_json,
        artifact_md_abs=md_abs,
        root=root,
        register=register,
        skip_registry=skip_registry,
        raise_on_error=raise_on_registry_error,
        uat_status=uat_status,
        doc=doc,
    )

    return {"version_id": version_id, "path": str(stage6_current_path(ticker, root))}


def load_stage6_current(ticker: str, root: Path | None = None) -> dict[str, Any] | None:
    p = stage6_current_path(ticker, root)
    if not p.exists():
        return None
    return fa_storage.read_json(p)
