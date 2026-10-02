"""Read-only Thesis walk → idempotent registry backfill (Plan §0.M)."""
from __future__ import annotations

import json
import re
import uuid as uuid_mod
from pathlib import Path
from typing import Any

from ..ids import normalize_ticker, sha256_hex
from . import paths
from .db import open_registry
from .writers import (
    complete_run,
    ensure_company,
    make_run_id,
    record_final_fa_result,
    record_stage_result,
    start_run,
)

_VERSION_RE = re.compile(r"^stage(\d+)_v(\d+)\.json$", re.IGNORECASE)
_FINAL_RE = re.compile(r"^final_fa_v(\d+)\.json$", re.IGNORECASE)
_UAT_STAGE_RE = re.compile(
    r"^([A-Z0-9._-]+)_stage(\d+)_uat_(accepted|rejected|report)",
    re.IGNORECASE,
)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _meta_scalars(company_dir: Path) -> dict[str, Any]:
    meta_path = company_dir / "meta.json"
    meta = _load_json(meta_path) or {}
    return {
        "entity_name": meta.get("entity_name"),
        "cik": meta.get("cik"),
        "gate0_class": meta.get("gate0_class"),
        "stale": bool(meta.get("stale", False)),
        "stale_reason": meta.get("stale_reason"),
        "notes": None,
    }


def _fa_list_membership(root: Path) -> tuple[set[str], str | None]:
    list_path = root / "data" / "fundamental_analysis_list.json"
    if not list_path.is_file():
        return set(), None
    raw = _load_json(list_path) or {}
    tickers = {
        normalize_ticker(c.get("ticker", ""))
        for c in raw.get("companies", [])
        if c.get("ticker")
    }
    return tickers, raw.get("updated_at")


def _uat_index(root: Path) -> dict[tuple[str, int], tuple[str, str]]:
    """Map (ticker, stage) → (uat_status, relative pack path) when matchable."""
    out: dict[tuple[str, int], tuple[str, str]] = {}
    udir = root / "uat"
    if not udir.is_dir():
        return out
    for f in udir.iterdir():
        if not f.is_file():
            continue
        m = _UAT_STAGE_RE.match(f.name)
        if not m:
            continue
        ticker = normalize_ticker(m.group(1))
        stage = int(m.group(2))
        kind = m.group(3).lower()
        status = "accepted" if kind == "accepted" else ("rejected" if kind == "rejected" else "pending")
        # Prefer accepted over report
        key = (ticker, stage)
        prev = out.get(key)
        if prev and prev[0] == "accepted" and status != "accepted":
            continue
        out[key] = (status, f"uat/{f.name}")
    return out


def _current_version_id(thesis: Path, stage: int) -> str | None:
    cur = thesis / f"stage{stage}_CURRENT.json"
    doc = _load_json(cur)
    if not doc:
        return None
    vid = doc.get("version_id")
    return str(vid) if vid else None


def _final_current_version_id(thesis: Path) -> str | None:
    cur = thesis / "final_fa_CURRENT.json"
    doc = _load_json(cur)
    if not doc:
        return None
    vid = doc.get("version_id")
    return str(vid) if vid else None


def scan_company_thesis(company_dir: Path, root: Path) -> dict[str, Any]:
    """Read-only inventory of stage / Final FA version files for one company."""
    ticker = normalize_ticker(company_dir.name)
    thesis = company_dir / "Thesis"
    stages: list[dict[str, Any]] = []
    finals: list[dict[str, Any]] = []
    if not thesis.is_dir():
        return {"ticker": ticker, "stages": stages, "finals": finals}

    for stage in range(1, 10):
        vdir = thesis / f"stage{stage}_versions"
        current_vid = _current_version_id(thesis, stage)
        if not vdir.is_dir():
            # CURRENT without versions dir — still index CURRENT if present
            cur = thesis / f"stage{stage}_CURRENT.json"
            if cur.is_file():
                doc = _load_json(cur) or {}
                vid = str(doc.get("version_id") or "v001")
                md = thesis / f"stage{stage}_CURRENT.md"
                stages.append(
                    {
                        "stage": stage,
                        "version_id": vid,
                        "doc": doc,
                        "json_path": cur,
                        "md_path": md if md.is_file() else None,
                        "is_current": True,
                    }
                )
            continue
        for jf in sorted(vdir.glob("stage*_v*.json")):
            m = _VERSION_RE.match(jf.name)
            if not m:
                continue
            st = int(m.group(1))
            if st != stage:
                continue
            vid = f"v{int(m.group(2)):03d}"
            doc = _load_json(jf) or {}
            # Prefer embedded version_id
            if doc.get("version_id"):
                vid = str(doc["version_id"])
            md = jf.with_suffix(".md")
            is_cur = bool(current_vid and vid == current_vid)
            stages.append(
                {
                    "stage": stage,
                    "version_id": vid,
                    "doc": doc,
                    "json_path": jf,
                    "md_path": md if md.is_file() else None,
                    "is_current": is_cur,
                }
            )
        # If CURRENT exists but no version matched, mark latest by name as current fallback
        if current_vid and not any(s["is_current"] and s["stage"] == stage for s in stages):
            for s in stages:
                if s["stage"] == stage and s["version_id"] == current_vid:
                    s["is_current"] = True

    fdir = thesis / "final_fa_versions"
    current_fvid = _final_current_version_id(thesis)
    if fdir.is_dir():
        for jf in sorted(fdir.glob("final_fa_v*.json")):
            m = _FINAL_RE.match(jf.name)
            if not m:
                continue
            vid = f"v{int(m.group(1)):03d}"
            doc = _load_json(jf) or {}
            if doc.get("version_id"):
                vid = str(doc["version_id"])
            md = jf.with_suffix(".md")
            finals.append(
                {
                    "version_id": vid,
                    "doc": doc,
                    "json_path": jf,
                    "md_path": md if md.is_file() else None,
                    "is_current": bool(current_fvid and vid == current_fvid),
                }
            )
    else:
        cur = thesis / "final_fa_CURRENT.json"
        if cur.is_file():
            doc = _load_json(cur) or {}
            vid = str(doc.get("version_id") or "v001")
            md = thesis / "final_fa_CURRENT.md"
            finals.append(
                {
                    "version_id": vid,
                    "doc": doc,
                    "json_path": cur,
                    "md_path": md if md.is_file() else None,
                    "is_current": True,
                }
            )

    return {"ticker": ticker, "stages": stages, "finals": finals}


def backfill_registry(
    root: Path | None = None,
    *,
    db_path: Path | None = None,
    tickers: list[str] | None = None,
) -> dict[str, Any]:
    """
    Idempotent backfill from companies/*/Thesis/. Does not rewrite Thesis files.
    """
    root_p = paths.fa_root(root)
    companies_path = root_p / "companies"
    fa_members, fa_as_of = _fa_list_membership(root_p)
    uat_map = _uat_index(root_p)

    stats = {
        "companies_seen": 0,
        "companies_upserted": 0,
        "stage_rows_inserted": 0,
        "stage_rows_idempotent": 0,
        "final_rows_inserted": 0,
        "final_rows_idempotent": 0,
        "runs_created": 0,
        "tickers": [],
        "errors": [],
    }

    conn = open_registry(root_p, db_path=db_path)
    try:
        if not companies_path.is_dir():
            return stats

        dirs = sorted(
            [
                d
                for d in companies_path.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
        )
        if tickers:
            want = {normalize_ticker(t) for t in tickers}
            dirs = [d for d in dirs if normalize_ticker(d.name) in want]

        for company_dir in dirs:
            ticker = normalize_ticker(company_dir.name)
            stats["companies_seen"] += 1
            stats["tickers"].append(ticker)
            try:
                meta = _meta_scalars(company_dir)
                ensure_company(
                    conn,
                    ticker,
                    entity_name=meta["entity_name"],
                    cik=meta["cik"],
                    gate0_class=meta["gate0_class"],
                    fa_list_member=1 if ticker in fa_members else 0,
                    fa_list_as_of=fa_as_of,
                )
                stats["companies_upserted"] += 1
                if meta["stale"]:
                    from .writers import mark_company_stale

                    mark_company_stale(conn, ticker, stale=True, reason=meta.get("stale_reason"))

                inv = scan_company_thesis(company_dir, root_p)
                # One backfill run per company (cluster)
                run_id = None
                if inv["stages"] or inv["finals"]:
                    run_id = start_run(
                        conn,
                        ticker,
                        actor="script",
                        trigger="manual_backfill",
                        intent="backfill_thesis_scan",
                        # unique each backfill pass (idempotent stage rows; runs are append-only)
                        run_id=make_run_id(ticker, salt=f"backfill:{ticker}:{uuid_mod.uuid4().hex}"),
                        status="in_progress",
                    )
                    stats["runs_created"] += 1

                # Insert non-current first, then current — but writer handles demotion;
                # insert all with correct is_current flag. Process historical then current.
                hist = [s for s in inv["stages"] if not s["is_current"]]
                curs = [s for s in inv["stages"] if s["is_current"]]
                for item in hist + curs:
                    json_rel = paths.rel_under_fa_data(item["json_path"], root_p)
                    md_rel = (
                        paths.rel_under_fa_data(item["md_path"], root_p)
                        if item["md_path"]
                        else None
                    )
                    doc = item["doc"] or {}
                    uat_status, uat_pack = "none", None
                    ukey = (ticker, item["stage"])
                    if ukey in uat_map and item["is_current"]:
                        uat_status, uat_pack = uat_map[ukey]
                    row = record_stage_result(
                        conn,
                        ticker=ticker,
                        stage=item["stage"],
                        version_id=item["version_id"],
                        process_outcome=doc.get("process_outcome"),
                        terminates_later_stages=doc.get("terminates_later_stages"),
                        artifact_json_path=json_rel,
                        artifact_md_path=md_rel,
                        saved_at=doc.get("saved_at") or doc.get("date"),
                        is_current=bool(item["is_current"]),
                        content_sha256=sha256_hex(item["json_path"].read_bytes())
                        if item["json_path"].is_file()
                        else None,
                        run_id=run_id,
                        uat_status=uat_status,
                        uat_pack_path=uat_pack,
                        root=root_p,
                    )
                    if row.get("_idempotent"):
                        stats["stage_rows_idempotent"] += 1
                    else:
                        stats["stage_rows_inserted"] += 1

                fhist = [f for f in inv["finals"] if not f["is_current"]]
                fcurs = [f for f in inv["finals"] if f["is_current"]]
                for item in fhist + fcurs:
                    json_rel = paths.rel_under_fa_data(item["json_path"], root_p)
                    md_rel = (
                        paths.rel_under_fa_data(item["md_path"], root_p)
                        if item["md_path"]
                        else None
                    )
                    doc = item["doc"] or {}
                    row = record_final_fa_result(
                        conn,
                        ticker=ticker,
                        version_id=item["version_id"],
                        final_state=doc.get("final_state"),
                        technical_eligible=doc.get("technical_eligible"),
                        artifact_json_path=json_rel,
                        artifact_md_path=md_rel,
                        saved_at=doc.get("saved_at") or doc.get("date"),
                        is_current=bool(item["is_current"]),
                        content_sha256=sha256_hex(item["json_path"].read_bytes())
                        if item["json_path"].is_file()
                        else None,
                        run_id=run_id,
                        root=root_p,
                    )
                    if row.get("_idempotent"):
                        stats["final_rows_idempotent"] += 1
                    else:
                        stats["final_rows_inserted"] += 1

                if run_id:
                    complete_run(conn, run_id, status="completed", notes="backfill_thesis_scan")
                conn.commit()
            except Exception as e:  # noqa: BLE001 — collect per-ticker errors
                conn.rollback()
                stats["errors"].append({"ticker": ticker, "error": str(e)})

        conn.commit()
    finally:
        conn.close()
    return stats
