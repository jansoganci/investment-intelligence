"""Stage 4 filing coverage — no cross-ticker semantic contamination."""
from __future__ import annotations

import json
from pathlib import Path

from fa.stage4.semantic import run_stage4_semantic_from_filings


def test_stage4_semantic_refuses_shared_cache_fallback(tmp_path: Path, monkeypatch):
    """When ticker has no Source/filings, do not scan shared SEC cache HTML."""
    from fa import config, storage

    root = tmp_path / "fa_root"
    monkeypatch.setattr(config, "FA_ROOT", root)
    # Shared cache with foreign-issuer HTML only
    cache = tmp_path / "sec_cache" / "filings"
    cache.mkdir(parents=True)
    monkeypatch.setattr(config, "SEC_CACHE_DIR", tmp_path / "sec_cache")
    (cache / "ko-foreign.htm").write_text(
        "<html>Coca-Cola sparkling soft drink concentrate volume growth emerging markets</html>",
        encoding="utf-8",
    )

    storage.ensure_company_layout("ZZZZ", root, entity_name="Empty Co")
    rev = run_stage4_semantic_from_filings("ZZZZ", root=root, persist=False)
    cites = " ".join(f.citation or "" for f in rev.findings)
    excerpts = " ".join(f.excerpt or "" for f in rev.findings)
    assert "ko-foreign" not in cites
    assert "Coca-Cola" not in excerpts
    assert "sparkling" not in excerpts.lower()
    # Expect explicit filing_retrieval escalate, not filled-from-foreign-cache
    assert any(f.topic == "filing_retrieval" for f in rev.findings)
    assert rev.filled is False


def test_filing_metas_with_primary_are_ticker_scoped(tmp_path: Path, monkeypatch):
    from fa import config, storage
    from fa.ingest import ingest_sec_filing

    root = tmp_path / "fa_root"
    monkeypatch.setattr(config, "FA_ROOT", root)
    cache = tmp_path / "sec_cache" / "filings"
    cache.mkdir(parents=True)
    monkeypatch.setattr(config, "SEC_CACHE_DIR", tmp_path / "sec_cache")

    # Foreign cache noise
    (cache / "ko-foreign.htm").write_text("<html>KO beverage concentrate</html>", encoding="utf-8")
    # Ticker-scoped primary
    acc = "0000000000-26-000001"
    primary = "acme-20251231.htm"
    scoped = cache / f"{acc}_{primary}"
    scoped.write_text(
        "<html>Acme completed the acquisition of bolt-on software businesses. "
        "Cash paid for acquisitions was material. Organic revenue growth disclosed.</html>",
        encoding="utf-8",
    )

    storage.ensure_company_layout("ACME", root)
    ingest_sec_filing(
        "ACME",
        accession=acc,
        form="10-K",
        primary_document=primary,
        content={
            "accession": acc,
            "form": "10-K",
            "primary_document": primary,
            "cik": "0000000000",
        },
        content_filename=f"10-K_{acc}.json",
        root=root,
    )
    meta = storage.load_meta("ACME", root)
    meta["cik"] = "0000000000"
    storage.save_meta("ACME", meta, root)

    rev = run_stage4_semantic_from_filings("ACME", root=root, persist=False)
    cites = " ".join(f.citation or "" for f in rev.findings)
    assert "ko-foreign" not in cites
    assert "KO beverage" not in " ".join(f.excerpt or "" for f in rev.findings)
    assert rev.filled is True
