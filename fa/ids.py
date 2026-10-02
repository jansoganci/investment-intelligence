"""Deterministic ids and timestamps for FA."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper()


def period_key_fy(year: int) -> str:
    return f"FY{year}"


def period_key_q(year: int, quarter: int) -> str:
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"invalid quarter: {quarter}")
    return f"{year}Q{quarter}"


def next_version_id(existing: list[str]) -> str:
    """Return next vNNN given existing version ids like v001, v002."""
    max_n = 0
    for v in existing:
        m = re.fullmatch(r"v(\d+)", v or "")
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"v{max_n + 1:03d}"


def sha256_hex(content: bytes | str) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def sec_source_id(accession: str, primary_document: str | None = None) -> str:
    acc = (accession or "").strip()
    if not acc:
        raise ValueError("accession required for SEC source_id")
    if primary_document:
        return f"{acc}::{primary_document}"
    return acc


def ir_source_id(content_hash: str, logical_name: str, as_of_date: str) -> str:
    return f"ir:{content_hash}:{logical_name}:{as_of_date}"
