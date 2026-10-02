"""Registry on-disk paths (Plan §0.C)."""
from __future__ import annotations

from pathlib import Path

from .. import config


def fa_root(root: Path | None = None) -> Path:
    return Path(root) if root is not None else Path(config.FA_ROOT)


def registry_dir(root: Path | None = None) -> Path:
    return fa_root(root) / "registry"


def registry_db_path(root: Path | None = None) -> Path:
    return registry_dir(root) / "fa_run_registry.sqlite"


def views_dir(root: Path | None = None) -> Path:
    return registry_dir(root) / "views"


def backups_dir(root: Path | None = None) -> Path:
    return registry_dir(root) / "backups"


def companies_dir(root: Path | None = None) -> Path:
    return fa_root(root) / "companies"


def uat_dir(root: Path | None = None) -> Path:
    return fa_root(root) / "uat"


def rel_under_fa_data(abs_path: Path, root: Path | None = None) -> str:
    """Return path relative to fa_data/ (Plan §0.C pointer root)."""
    base = fa_root(root).resolve()
    p = Path(abs_path).resolve()
    try:
        return str(p.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(abs_path).replace("\\", "/")
