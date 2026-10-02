"""Persist Final FA artifacts (CURRENT + versions) + registry hook after write."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import storage as fa_storage
from ..ids import normalize_ticker, utc_now


def thesis_dir(ticker: str, root: Path | None = None) -> Path:
    return fa_storage.company_dir(ticker, root) / "Thesis"


def final_fa_current_path(ticker: str, root: Path | None = None) -> Path:
    return thesis_dir(ticker, root) / "final_fa_CURRENT.json"


def final_fa_versions_dir(ticker: str, root: Path | None = None) -> Path:
    return thesis_dir(ticker, root) / "final_fa_versions"


def save_final_fa_report(
    ticker: str,
    doc: dict[str, Any],
    *,
    root: Path | None = None,
    markdown: str | None = None,
    register: bool = True,
    raise_on_registry_error: bool = False,
    uat_status: str | None = None,
    skip_registry: bool = False,
    stage_result_ids_consumed: list[str] | None = None,
) -> dict[str, Any]:
    """
    Write Thesis/final_fa_CURRENT.json + versioned copy (+ optional md).

    ``doc`` must already contain synthesis scalars (final_state, etc.).
    This function does **not** compute Final FA outcomes.
    """
    ticker = normalize_ticker(ticker)
    fa_storage.ensure_company_layout(ticker, root)
    tdir = thesis_dir(ticker, root)
    tdir.mkdir(parents=True, exist_ok=True)
    vdir = final_fa_versions_dir(ticker, root)
    vdir.mkdir(parents=True, exist_ok=True)

    existing = sorted(vdir.glob("final_fa_v*.json"))
    n = len(existing) + 1
    version_id = f"v{n:03d}"
    version_name = f"final_fa_{version_id}.json"

    payload = dict(doc)
    payload["ticker"] = ticker
    payload["version_id"] = version_id
    payload["saved_at"] = utc_now()
    prov = payload.get("provenance")
    if isinstance(prov, dict):
        prov = dict(prov)
        prov["final_fa_version"] = version_id
        payload["provenance"] = prov

    version_json = vdir / version_name
    fa_storage.write_json(version_json, payload)
    fa_storage.write_json(final_fa_current_path(ticker, root), payload)

    md_abs: Path | None = None
    if markdown is not None:
        md_abs = tdir / "final_fa_CURRENT.md"
        md_abs.write_text(markdown, encoding="utf-8")
        (vdir / f"final_fa_{version_id}.md").write_text(markdown, encoding="utf-8")

    from ..registry.hooks import hook_final_fa_after_artifact

    hook_final_fa_after_artifact(
        ticker=ticker,
        version_id=version_id,
        artifact_json_abs=version_json,
        artifact_md_abs=md_abs,
        root=root,
        register=register,
        skip_registry=skip_registry,
        raise_on_error=raise_on_registry_error,
        uat_status=uat_status,
        stage_result_ids_consumed=stage_result_ids_consumed,
        doc=payload,
    )

    return {"version_id": version_id, "path": str(final_fa_current_path(ticker, root))}


def load_final_fa_current(ticker: str, root: Path | None = None) -> dict[str, Any] | None:
    p = final_fa_current_path(ticker, root)
    if not p.exists():
        return None
    return fa_storage.read_json(p)
