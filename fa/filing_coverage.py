"""Generic SEC filing coverage for semantic / MD&A scans.

Ensures recent 10-K / 10-Q Source metas + cached HTML for a ticker via
submissions. No ticker hardcodes. Does not invent text. Missing filings →
explicit reasons (not silent cross-ticker cache reuse).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import config, storage
from .ids import normalize_ticker
from .ingest import ingest_sec_filing
from .sec_client import get_filing_document, get_submissions, resolve_cik


def _recent_periodic_from_submissions(
    submissions: dict,
    *,
    forms: tuple[str, ...] = ("10-K", "10-Q", "20-F"),
    max_filings: int = 6,
) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent") or {}
    forms_l = recent.get("form") or []
    accessions = recent.get("accessionNumber") or []
    primary = recent.get("primaryDocument") or []
    filed = recent.get("filingDate") or []
    report_dates = recent.get("reportDate") or []
    out: list[dict[str, Any]] = []
    for i, form in enumerate(forms_l):
        if form not in forms:
            continue
        if i >= len(accessions) or i >= len(primary):
            continue
        acc = accessions[i]
        prim = primary[i]
        if not acc or not prim:
            continue
        out.append(
            {
                "accession": acc,
                "form": form,
                "primary_document": prim,
                "filed_at": filed[i] if i < len(filed) else None,
                "period_end": report_dates[i] if i < len(report_dates) else None,
            }
        )
        if len(out) >= max_filings:
            break
    return out


def ensure_recent_sec_filings(
    ticker: str,
    *,
    root: Path | None = None,
    forms: tuple[str, ...] = ("10-K", "10-Q", "20-F"),
    max_filings: int = 6,
    offline: bool | None = None,
    download_html: bool = True,
) -> dict[str, Any]:
    """
    Resolve CIK → submissions → ingest Source metas for recent periodic filings.
    Optionally download primary HTML into accession-scoped SEC cache.
    Persist CIK on company meta when resolved.
    """
    ticker = normalize_ticker(ticker)
    root = root or config.FA_ROOT
    storage.ensure_company_layout(ticker, root)
    report: dict[str, Any] = {
        "ticker": ticker,
        "created": [],
        "existing": [],
        "downloaded": [],
        "failed": [],
        "cik": None,
    }

    cik = resolve_cik(ticker, offline=offline)
    if not cik:
        report["failed"].append(
            {"reason_code": "CIK_UNRESOLVED", "detail": f"Cannot resolve CIK for {ticker}"}
        )
        return report
    report["cik"] = cik

    meta = storage.load_meta(ticker, root)
    if meta.get("cik") != cik:
        meta["cik"] = cik
        storage.save_meta(ticker, meta, root)

    submissions = get_submissions(cik, offline=offline)
    if not submissions:
        report["failed"].append(
            {
                "reason_code": "SUBMISSIONS_UNAVAILABLE",
                "detail": f"No submissions for CIK {cik}",
            }
        )
        return report

    rows = _recent_periodic_from_submissions(
        submissions, forms=forms, max_filings=max_filings
    )
    if not rows:
        report["failed"].append(
            {
                "reason_code": "NO_PERIODIC_FILINGS",
                "detail": f"No {forms} in recent submissions",
            }
        )
        return report

    for row in rows:
        content = {
            "accession": row["accession"],
            "form": row["form"],
            "filed_at": row.get("filed_at"),
            "primary_document": row["primary_document"],
            "cik": cik,
            "period_end": row.get("period_end"),
            "description": f"Form {row['form']} — auto filing coverage",
        }
        ing = ingest_sec_filing(
            ticker,
            accession=row["accession"],
            form=row["form"],
            filed_at=row.get("filed_at"),
            primary_document=row["primary_document"],
            content=content,
            content_filename=f"{row['form']}_{row['accession']}.json",
            metadata={"cik": cik, "period_end": row.get("period_end")},
            root=root,
        )
        key = f"{row['form']}:{row['accession']}"
        if ing.get("created"):
            report["created"].append(key)
        else:
            report["existing"].append(key)

        if download_html:
            path = get_filing_document(
                cik,
                row["accession"],
                row["primary_document"],
                offline=offline,
            )
            if path is not None and path.exists():
                report["downloaded"].append(str(path.name))
            else:
                report["failed"].append(
                    {
                        "reason_code": "FILING_HTML_UNAVAILABLE",
                        "detail": key,
                        "accession": row["accession"],
                        "primary": row["primary_document"],
                    }
                )

    return report
