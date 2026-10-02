from pathlib import Path

# Local = cache/workspace only; Drive mirror under butterbear is canonical for this box sync path
ROOT = Path("/workspace/investment_intelligence")
CACHE = ROOT / "cache"
DRIVE_RI = Path("/workspace/butterbear/drive/transition/01_Research")
DRIVE_DATA = DRIVE_RI / "data"
DRIVE_VIEWS = DRIVE_RI / "views"
DRIVE_FIXTURES = DRIVE_RI / "fixtures"
DRIVE_OPS_LOGS = Path("/workspace/butterbear/drive/transition/07_Operations/logs")
DRIVE_OPS_WEEKLY = Path("/workspace/butterbear/drive/transition/07_Operations/weekly")

# xAI list prices for estimated_cost (API-equivalent) — provisional
PRICE_IN_PER_M = 1.25
PRICE_OUT_PER_M = 2.50

MATERIALITY_RUBRIC = """
HIGH: Could reasonably affect investment thesis or materially influence future revenue, margins, cash flow, CAPEX, balance sheet, capital allocation, regulation, competitive position, guidance, supply/demand economics, or valuation expectations.
MEDIUM: Relevant to company/sector/theme but not yet clearly thesis-changing.
LOW: Routine, repetitive, promotional, weakly relevant, or informational with no clear thesis impact.
REVIEW_REQUIRED: Insufficient evidence to judge materiality.
HIGH ≠ BUY. LOW ≠ ignore forever. Materiality must NOT change RED/ORANGE/GREEN.
"""
