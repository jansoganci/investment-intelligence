"""Regenerate company_stage_matrix CSV/MD from SQL views (Plan §0.I)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from . import paths
from .db import open_registry


MATRIX_COLUMNS = [
    "ticker",
    "gate0_class",
    "s1_process_outcome",
    "s1_version_id",
    "s1_saved_at",
    "s2_process_outcome",
    "s2_version_id",
    "s2_saved_at",
    "s3_process_outcome",
    "s3_version_id",
    "s3_saved_at",
    "s4_process_outcome",
    "s4_version_id",
    "s4_saved_at",
    "s5_process_outcome",
    "s5_version_id",
    "s5_saved_at",
    "s6_process_outcome",
    "s6_version_id",
    "s6_saved_at",
    "s7_process_outcome",
    "s7_version_id",
    "s7_saved_at",
    "s8_process_outcome",
    "s8_version_id",
    "s8_saved_at",
    "s9_process_outcome",
    "s9_version_id",
    "s9_saved_at",
    "final_fa_final_state",
    "final_fa_technical_eligible",
    "final_fa_version_id",
    "last_run_id",
    "stale_flag",
    "stale_reason",
    "s1_uat_status",
    "s2_uat_status",
    "s3_uat_status",
    "s4_uat_status",
    "s5_uat_status",
    "s6_uat_status",
    "s7_uat_status",
    "s8_uat_status",
    "s9_uat_status",
    "final_fa_uat_status",
]


def fetch_company_stage_matrix(root: Path | None = None, *, db_path: Path | None = None) -> list[dict[str, Any]]:
    conn = open_registry(root, db_path=db_path)
    try:
        cols = ", ".join(MATRIX_COLUMNS)
        rows = conn.execute(f"SELECT {cols} FROM v_company_stage_matrix ORDER BY ticker").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def export_company_stage_matrix(
    root: Path | None = None,
    *,
    db_path: Path | None = None,
    write_md: bool = True,
) -> dict[str, Path]:
    """Write views/company_stage_matrix.csv (+ optional .md). Never hand-edit as SoR."""
    rows = fetch_company_stage_matrix(root, db_path=db_path)
    vdir = paths.views_dir(root) if db_path is None else (Path(db_path).parent / "views")
    vdir.mkdir(parents=True, exist_ok=True)
    csv_path = vdir / "company_stage_matrix.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MATRIX_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in MATRIX_COLUMNS})

    out: dict[str, Path] = {"csv": csv_path}
    if write_md:
        md_path = vdir / "company_stage_matrix.md"
        lines = [
            "# Company × Stage matrix (regenerated)",
            "",
            "Source: `v_company_stage_matrix` — do not hand-edit as SoR.",
            "",
            "| " + " | ".join(["ticker", "gate0"] + [f"S{i}" for i in range(1, 10)] + ["FinalFA", "stale"]) + " |",
            "| " + " | ".join(["---"] * 13) + " |",
        ]
        for r in rows:
            outcomes = [str(r.get(f"s{i}_process_outcome") or "") for i in range(1, 10)]
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(r.get("ticker") or ""),
                        str(r.get("gate0_class") or ""),
                        *outcomes,
                        str(r.get("final_fa_final_state") or ""),
                        str(r.get("stale_flag") or 0),
                    ]
                )
                + " |"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out["md"] = md_path
    return out
