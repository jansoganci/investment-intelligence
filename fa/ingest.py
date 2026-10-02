"""Idempotent Source ingest (SEC accession / IR hash)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from . import storage
from .ids import ir_source_id, normalize_ticker, sec_source_id, sha256_hex, utc_now

SourceType = Literal["sec", "ir", "notes"]


def ingest_sec_filing(
    ticker: str,
    *,
    accession: str,
    form: str,
    filed_at: str | None = None,
    primary_document: str | None = None,
    content: str | bytes | None = None,
    content_filename: str | None = None,
    metadata: dict | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Idempotent SEC Source ingest.
    source_id = accession (optionally + primary_document).
    Same source_id → no duplicate Source file; returns existing record with created=False.
    """
    ticker = normalize_ticker(ticker)
    storage.ensure_company_layout(ticker, root)
    sid = sec_source_id(accession, primary_document)

    existing = storage.find_source_by_id(ticker, sid, root)
    if existing:
        return {"created": False, "source": existing, "reason": "same_source_id"}

    # Write content file if provided
    safe_acc = accession.replace("/", "-")
    safe_form = (form or "UNK").replace("/", "-")
    fname = content_filename or f"{safe_form}_{safe_acc}.json"
    dest = storage.company_dir(ticker, root) / "Source" / "filings" / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    if content is not None:
        if dest.exists():
            # different path collision without matching source_id — still skip write if hash matches
            pass
        else:
            if isinstance(content, bytes):
                dest.write_bytes(content)
            else:
                dest.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")

    record = {
        "source_id": sid,
        "source_type": "sec",
        "accession": accession,
        "primary_document": primary_document,
        "form": form,
        "filed_at": filed_at,
        "path": str(dest.relative_to(storage.company_dir(ticker, root))) if dest.exists() or content is not None else None,
        "ingested_at": utc_now(),
        "metadata": metadata or {},
    }
    # Ensure path set even if we only store stub
    if record["path"] is None:
        stub = storage.company_dir(ticker, root) / "Source" / "filings" / fname
        if not stub.exists():
            stub.write_text(
                json.dumps({"accession": accession, "form": form, "stub": True}, indent=2) + "\n",
                encoding="utf-8",
            )
        record["path"] = str(stub.relative_to(storage.company_dir(ticker, root)))

    man = storage.load_source_manifest(ticker, root)
    man.setdefault("sources", []).append(record)
    storage.save_source_manifest(ticker, man, root)
    return {"created": True, "source": record, "reason": "new"}


def ingest_ir_doc(
    ticker: str,
    *,
    logical_name: str,
    as_of_date: str,
    content: str | bytes,
    filename: str | None = None,
    metadata: dict | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Idempotent IR Source ingest.
    source_id = sha256(content) + logical_name + as_of_date.
    Does NOT auto-mutate GAAP Normalized periods.
    """
    ticker = normalize_ticker(ticker)
    storage.ensure_company_layout(ticker, root)
    raw = content if isinstance(content, bytes) else content.encode("utf-8")
    chash = sha256_hex(raw)
    sid = ir_source_id(chash, logical_name, as_of_date)

    existing = storage.find_source_by_id(ticker, sid, root)
    if existing:
        return {"created": False, "source": existing, "reason": "same_source_id"}

    fname = filename or f"{logical_name}_{as_of_date}_{chash[:12]}.txt"
    dest = storage.company_dir(ticker, root) / "Source" / "ir" / fname
    if not dest.exists():
        dest.write_bytes(raw)

    record = {
        "source_id": sid,
        "source_type": "ir",
        "logical_name": logical_name,
        "as_of_date": as_of_date,
        "content_hash": chash,
        "path": str(dest.relative_to(storage.company_dir(ticker, root))),
        "ingested_at": utc_now(),
        "metadata": metadata or {},
        "note": "IR ingest does not auto-mutate GAAP Normalized periods",
    }
    man = storage.load_source_manifest(ticker, root)
    man.setdefault("sources", []).append(record)
    storage.save_source_manifest(ticker, man, root)
    return {"created": True, "source": record, "reason": "new"}


def ingest_note(
    ticker: str,
    *,
    logical_name: str,
    content: str,
    root: Path | None = None,
) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    storage.ensure_company_layout(ticker, root)
    chash = sha256_hex(content)
    sid = f"note:{chash}:{logical_name}"
    existing = storage.find_source_by_id(ticker, sid, root)
    if existing:
        return {"created": False, "source": existing, "reason": "same_source_id"}
    fname = f"{logical_name}_{chash[:12]}.md"
    dest = storage.company_dir(ticker, root) / "Source" / "notes" / fname
    dest.write_text(content, encoding="utf-8")
    record = {
        "source_id": sid,
        "source_type": "notes",
        "logical_name": logical_name,
        "content_hash": chash,
        "path": str(dest.relative_to(storage.company_dir(ticker, root))),
        "ingested_at": utc_now(),
    }
    man = storage.load_source_manifest(ticker, root)
    man.setdefault("sources", []).append(record)
    storage.save_source_manifest(ticker, man, root)
    return {"created": True, "source": record, "reason": "new"}
