"""Stage 3 contract extensions + companyfacts mapping."""
from __future__ import annotations

import json
from pathlib import Path

from fa.contract import ALL_NUMERIC_FIELDS, BS_STAGE3_EXTENSIONS, CF_STAGE3_EXTENSIONS, empty_fields
from fa.map_companyfacts import NULL_FIELD_REASONS, TAG_MAP, map_companyfacts_to_period


STAGE3_FIELDS = [
    "accounts_payable",
    "deferred_revenue_current",
    "deferred_revenue_noncurrent",
    "business_acquisitions_cash",
    "proceeds_from_asset_sales",
]


def test_contract_stage3_fields_nullable():
    f = empty_fields()
    for k in STAGE3_FIELDS:
        assert k in f
        assert f[k] is None
        assert k in ALL_NUMERIC_FIELDS
    for k in BS_STAGE3_EXTENSIONS + CF_STAGE3_EXTENSIONS:
        assert k in ALL_NUMERIC_FIELDS


def test_tag_map_has_defensible_mappings():
    for k in STAGE3_FIELDS:
        assert k in TAG_MAP
        assert TAG_MAP[k]
    assert "accounts_payable" in NULL_FIELD_REASONS


def test_map_clean_accounts_payable():
    facts = {
        "entityName": "Test Co",
        "cik": 1,
        "facts": {
            "us-gaap": {
                "AccountsPayableCurrent": {
                    "units": {
                        "USD": [
                            {
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2025-12-31",
                                "val": 123000,
                                "accn": "0001",
                            }
                        ]
                    }
                }
            }
        },
    }
    doc = map_companyfacts_to_period(
        facts,
        ticker="T",
        period_key="FY2025",
        fiscal_year=2025,
        accession="0001",
        period_end="2025-12-31",
    )
    assert doc["fields"]["accounts_payable"] == 123000
    lin = [x for x in doc["lineage"] if x["field"] == "accounts_payable"]
    assert lin and lin[0]["source_ref"]


def test_map_mixed_ap_accrued_left_null_uncertain():
    facts = {
        "entityName": "Test Co",
        "cik": 1,
        "facts": {
            "us-gaap": {
                "AccountsPayableAndAccruedLiabilitiesCurrent": {
                    "units": {
                        "USD": [
                            {
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2025-12-31",
                                "val": 999000,
                                "accn": "0001",
                            }
                        ]
                    }
                }
            }
        },
    }
    doc = map_companyfacts_to_period(
        facts,
        ticker="T",
        period_key="FY2025",
        fiscal_year=2025,
        accession="0001",
        period_end="2025-12-31",
    )
    assert doc["fields"]["accounts_payable"] is None
    assert "accounts_payable" in doc.get("field_uncertainty", {})
    nr = doc.get("null_reasons", {}).get("accounts_payable")
    assert isinstance(nr, dict)
    assert nr.get("code") == "MAPPING_AMBIGUOUS"


def test_map_acquisitions_and_asset_sales():
    facts = {
        "entityName": "Test Co",
        "cik": 1,
        "facts": {
            "us-gaap": {
                "PaymentsToAcquireBusinessesNetOfCashAcquired": {
                    "units": {
                        "USD": [
                            {
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2025-12-31",
                                "val": 50000,
                                "accn": "0001",
                            }
                        ]
                    }
                },
                "ProceedsFromSaleOfPropertyPlantAndEquipment": {
                    "units": {
                        "USD": [
                            {
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2025-12-31",
                                "val": 8000,
                                "accn": "0001",
                            }
                        ]
                    }
                },
            }
        },
    }
    doc = map_companyfacts_to_period(
        facts,
        ticker="T",
        period_key="FY2025",
        fiscal_year=2025,
        accession="0001",
        period_end="2025-12-31",
    )
    assert doc["fields"]["business_acquisitions_cash"] == 50000
    assert doc["fields"]["proceeds_from_asset_sales"] == 8000


def test_synth_fixture_still_maps(tmp_path):
    stub = Path(
        "/workspace/investment_intelligence/fa_fixtures/synthetic_operating_company/sec_companyfacts_stub.json"
    )
    facts = json.loads(stub.read_text())
    doc = map_companyfacts_to_period(
        facts,
        ticker="SYNTH_OPCO",
        period_key="FY2025",
        fiscal_year=2025,
        accession="0009999991-26-000001",
    )
    assert "fields" in doc
    assert "lineage" in doc
