"""Drift detection: artifact file wins; report registry vs disk mismatches (Plan §0.E)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ids import normalize_ticker, sha256_hex
from . import paths
from .backfill import scan_company_thesis
from .db import open_registry
from .writers import ensure_company, record_final_fa_result, record_stage_result


def detect_drift(root: Path | None = None, *, db_path: Path | None = None) -> dict[str, Any]:
    """
    Compare registry stage/final CURRENT rows to on-disk Thesis artifacts.
    File wins on disagreement — this function only REPORTS (use repair_drift to fix).
    """
    root_p = paths.fa_root(root)
    companies_path = root_p / "companies"
    report: dict[str, Any] = {
        "mismatches": [],
        "missing_on_disk": [],
        "missing_in_registry": [],
        "hash_mismatches": [],
        "ok_count": 0,
    }
    conn = open_registry(root_p, db_path=db_path)
    try:
        if not companies_path.is_dir():
            return report

        disk_index: dict[tuple[str, str, str], dict[str, Any]] = {}
        # key: (ticker, 'stage'| 'final', version_or_stagekey)
        for company_dir in sorted(companies_path.iterdir()):
            if not company_dir.is_dir() or company_dir.name.startswith("."):
                continue
            inv = scan_company_thesis(company_dir, root_p)
            ticker = inv["ticker"]
            for s in inv["stages"]:
                key = (ticker, "stage", f"{s['stage']}:{s['version_id']}")
                disk_index[key] = s
                # Also track CURRENT pointer separately
                if s["is_current"]:
                    disk_index[(ticker, "stage_current", str(s["stage"]))] = s
            for f in inv["finals"]:
                key = (ticker, "final", f["version_id"])
                disk_index[key] = f
                if f["is_current"]:
                    disk_index[(ticker, "final_current", "")] = f

        # Registry stage rows
        for row in conn.execute("SELECT * FROM stage_results").fetchall():
            ticker = row["ticker"]
            key = (ticker, "stage", f"{row['stage']}:{row['version_id']}")
            disk = disk_index.get(key)
            if disk is None:
                # Check if path exists anyway
                if row["artifact_json_path"]:
                    abs_p = root_p / row["artifact_json_path"]
                    if not abs_p.is_file():
                        report["missing_on_disk"].append(
                            {
                                "kind": "stage",
                                "ticker": ticker,
                                "stage": row["stage"],
                                "version_id": row["version_id"],
                                "path": row["artifact_json_path"],
                            }
                        )
                        continue
                report["missing_on_disk"].append(
                    {
                        "kind": "stage",
                        "ticker": ticker,
                        "stage": row["stage"],
                        "version_id": row["version_id"],
                        "path": row["artifact_json_path"],
                    }
                )
                continue

            doc = disk["doc"] or {}
            issues = []
            if (doc.get("process_outcome") or None) != (row["process_outcome"] or None):
                issues.append(
                    {
                        "field": "process_outcome",
                        "registry": row["process_outcome"],
                        "disk": doc.get("process_outcome"),
                    }
                )
            if bool(row["is_current"]) != bool(disk["is_current"]):
                issues.append(
                    {
                        "field": "is_current",
                        "registry": bool(row["is_current"]),
                        "disk": bool(disk["is_current"]),
                    }
                )
            if row["content_sha256"] and disk["json_path"].is_file():
                disk_sha = sha256_hex(disk["json_path"].read_bytes())
                if disk_sha != row["content_sha256"]:
                    report["hash_mismatches"].append(
                        {
                            "kind": "stage",
                            "ticker": ticker,
                            "stage": row["stage"],
                            "version_id": row["version_id"],
                            "registry_sha": row["content_sha256"],
                            "disk_sha": disk_sha,
                        }
                    )
            if issues:
                report["mismatches"].append(
                    {
                        "kind": "stage",
                        "ticker": ticker,
                        "stage": row["stage"],
                        "version_id": row["version_id"],
                        "issues": issues,
                    }
                )
            else:
                report["ok_count"] += 1

        for row in conn.execute("SELECT * FROM final_fa_results").fetchall():
            ticker = row["ticker"]
            key = (ticker, "final", row["version_id"])
            disk = disk_index.get(key)
            if disk is None:
                report["missing_on_disk"].append(
                    {
                        "kind": "final_fa",
                        "ticker": ticker,
                        "version_id": row["version_id"],
                        "path": row["artifact_json_path"],
                    }
                )
                continue
            doc = disk["doc"] or {}
            issues = []
            if (doc.get("final_state") or None) != (row["final_state"] or None):
                issues.append(
                    {
                        "field": "final_state",
                        "registry": row["final_state"],
                        "disk": doc.get("final_state"),
                    }
                )
            if bool(row["is_current"]) != bool(disk["is_current"]):
                issues.append(
                    {
                        "field": "is_current",
                        "registry": bool(row["is_current"]),
                        "disk": bool(disk["is_current"]),
                    }
                )
            if issues:
                report["mismatches"].append(
                    {
                        "kind": "final_fa",
                        "ticker": ticker,
                        "version_id": row["version_id"],
                        "issues": issues,
                    }
                )
            else:
                report["ok_count"] += 1

        # Disk versions missing from registry
        for key, disk in disk_index.items():
            kind = key[1]
            if kind in ("stage_current", "final_current"):
                continue
            ticker = key[0]
            if kind == "stage":
                stage_s, vid = key[2].split(":", 1)
                stage = int(stage_s)
                row = conn.execute(
                    """
                    SELECT 1 FROM stage_results
                    WHERE ticker = ? AND stage = ? AND version_id = ?
                    """,
                    (ticker, stage, vid),
                ).fetchone()
                if row is None:
                    report["missing_in_registry"].append(
                        {
                            "kind": "stage",
                            "ticker": ticker,
                            "stage": stage,
                            "version_id": vid,
                            "path": str(disk["json_path"]),
                        }
                    )
            elif kind == "final":
                vid = key[2]
                row = conn.execute(
                    """
                    SELECT 1 FROM final_fa_results
                    WHERE ticker = ? AND version_id = ?
                    """,
                    (ticker, vid),
                ).fetchone()
                if row is None:
                    report["missing_in_registry"].append(
                        {
                            "kind": "final_fa",
                            "ticker": ticker,
                            "version_id": vid,
                            "path": str(disk["json_path"]),
                        }
                    )
    finally:
        conn.close()
    return report


def repair_drift_from_disk(
    root: Path | None = None,
    *,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """
    Repair registry from disk scan (file wins).

    Strategy: re-run idempotent backfill for missing rows; for CURRENT flag /
    outcome mismatches on existing keys — insert is idempotent so outcome scalars
    stay frozen; CURRENT flag repaired by demoting all and re-applying disk CURRENT.
    Never silently overwrite historical outcome scalars for an existing
    (ticker, stage, version_id) key — those require a new version on disk.
    """
    from .backfill import backfill_registry

    root_p = paths.fa_root(root)
    # First insert any missing
    bf = backfill_registry(root_p, db_path=db_path)
    # Then fix CURRENT flags from disk (allowed UPDATE)
    conn = open_registry(root_p, db_path=db_path)
    repaired_current = 0
    try:
        companies_path = root_p / "companies"
        if companies_path.is_dir():
            for company_dir in sorted(companies_path.iterdir()):
                if not company_dir.is_dir() or company_dir.name.startswith("."):
                    continue
                inv = scan_company_thesis(company_dir, root_p)
                ticker = inv["ticker"]
                ensure_company(conn, ticker)
                for stage in range(1, 10):
                    disk_cur = next(
                        (s for s in inv["stages"] if s["stage"] == stage and s["is_current"]),
                        None,
                    )
                    if disk_cur is None:
                        continue
                    # demote all, promote disk current
                    conn.execute(
                        """
                        UPDATE stage_results SET is_current = 0
                        WHERE ticker = ? AND stage = ? AND is_current = 1
                        """,
                        (ticker, stage),
                    )
                    cur = conn.execute(
                        """
                        UPDATE stage_results SET is_current = 1
                        WHERE ticker = ? AND stage = ? AND version_id = ?
                        """,
                        (ticker, stage, disk_cur["version_id"]),
                    )
                    if cur.rowcount:
                        repaired_current += 1
                disk_f = next((f for f in inv["finals"] if f["is_current"]), None)
                if disk_f is not None:
                    conn.execute(
                        "UPDATE final_fa_results SET is_current = 0 WHERE ticker = ? AND is_current = 1",
                        (ticker,),
                    )
                    cur = conn.execute(
                        """
                        UPDATE final_fa_results SET is_current = 1
                        WHERE ticker = ? AND version_id = ?
                        """,
                        (ticker, disk_f["version_id"]),
                    )
                    if cur.rowcount:
                        repaired_current += 1
        conn.commit()
    finally:
        conn.close()
    after = detect_drift(root_p, db_path=db_path)
    return {
        "backfill": bf,
        "repaired_current_flags": repaired_current,
        "drift_after": {
            "mismatches": len(after["mismatches"]),
            "missing_on_disk": len(after["missing_on_disk"]),
            "missing_in_registry": len(after["missing_in_registry"]),
            "hash_mismatches": len(after["hash_mismatches"]),
        },
    }
