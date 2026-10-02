"""Write-once registry DB snapshots (Plan §0.L)."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import paths
from .db import RegistryError


def backup_registry(root: Path | None = None, *, db_path: Path | None = None) -> Path:
    """
    Copy live DB to backups/fa_run_registry_YYYYMMDDTHHMMSSZ.sqlite (write-once).
    """
    src = Path(db_path) if db_path is not None else paths.registry_db_path(root)
    if not src.is_file():
        raise RegistryError(f"registry DB missing: {src}")
    bdir = paths.backups_dir(root) if db_path is None else (src.parent / "backups")
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = bdir / f"fa_run_registry_{stamp}.sqlite"
    if dest.exists():
        # rare same-second collision
        dest = bdir / f"fa_run_registry_{stamp}_{src.stat().st_size}.sqlite"
    shutil.copy2(src, dest)
    return dest


def restore_registry_from_backup(
    backup_path: Path,
    root: Path | None = None,
    *,
    db_path: Path | None = None,
) -> Path:
    """Replace live DB from a write-once snapshot (explicit rollback aid)."""
    backup_path = Path(backup_path)
    if not backup_path.is_file():
        raise RegistryError(f"backup missing: {backup_path}")
    dest = Path(db_path) if db_path is not None else paths.registry_db_path(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, dest)
    return dest
