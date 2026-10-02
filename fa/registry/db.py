"""SQLite connection + schema init for FA run registry."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from . import paths
from .schema import DDL, SCHEMA_VERSION


class RegistryError(Exception):
    """Base registry error."""


def connect(root: Path | None = None, *, db_path: Path | None = None) -> sqlite3.Connection:
    """Open registry DB (creates parent dirs). Caller should close or use open_registry."""
    path = Path(db_path) if db_path is not None else paths.registry_db_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.parent / "views").mkdir(parents=True, exist_ok=True)
    (path.parent / "backups").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(DDL)
    cur = conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'")
    row = cur.fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
    conn.commit()


def open_registry(root: Path | None = None, *, db_path: Path | None = None) -> sqlite3.Connection:
    """Connect + ensure schema. Returns open connection."""
    conn = connect(root, db_path=db_path)
    init_schema(conn)
    return conn


@contextmanager
def registry_session(root: Path | None = None, *, db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = open_registry(root, db_path=db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
