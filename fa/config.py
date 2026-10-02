"""FA paths and constants. Local FA_ROOT is cache; Drive 03_Fundamental is conceptual canonical."""
from __future__ import annotations

import os
from pathlib import Path

# Package root (investment_intelligence/)
PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# Default local data root — override with FA_ROOT env (Drive sync later)
_DEFAULT_FA_ROOT = PACKAGE_ROOT / "fa_data"
FA_ROOT = Path(os.environ.get("FA_ROOT", str(_DEFAULT_FA_ROOT))).resolve()

# Conceptual Drive path (documented; not required for dry-run)
DRIVE_FA_CONCEPTUAL = Path("/workspace/butterbear/drive/transition/03_Fundamental")

COMPANIES_DIR = FA_ROOT / "companies"
DATA_DIR = FA_ROOT / "data"
CACHE_DIR = FA_ROOT / "cache"
SEC_CACHE_DIR = CACHE_DIR / "sec"

FA_LIST_FILENAME = "fundamental_analysis_list.json"
RESEARCH_COVERAGE_STUB = "research_coverage_list.json"  # stub only; RI tracked_companies is separate

SEC_USER_AGENT = "InvestmentIntelligence/0.1 (personal research; contact: research@example.com)"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Fixture / offline mode
FIXTURES_DIR = PACKAGE_ROOT / "fa_fixtures"
DEMO_FA_LIST = FIXTURES_DIR / "demo_fa_list.json"
SYNTH_COMPANY_DIR = FIXTURES_DIR / "synthetic_operating_company"

# Env flags
FA_OFFLINE = os.environ.get("FA_OFFLINE", "1").lower() in ("1", "true", "yes")
FA_USE_FIXTURE_LIST = os.environ.get("FA_USE_FIXTURE_LIST", "").lower() in ("1", "true", "yes")
