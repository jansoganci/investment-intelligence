"""Shared fixtures for FA tests — all synthetic, isolated temp FA_ROOT."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Ensure package importable
import sys
ROOT = Path("/workspace/investment_intelligence")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def fa_root(tmp_path, monkeypatch):
    root = tmp_path / "fa_data"
    root.mkdir()
    (root / "data").mkdir()
    (root / "cache" / "sec").mkdir(parents=True)
    (root / "companies").mkdir()
    monkeypatch.setenv("FA_ROOT", str(root))
    monkeypatch.setenv("FA_OFFLINE", "1")
    # reload config paths
    import fa.config as cfg
    monkeypatch.setattr(cfg, "FA_ROOT", root)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", root / "companies")
    monkeypatch.setattr(cfg, "DATA_DIR", root / "data")
    monkeypatch.setattr(cfg, "CACHE_DIR", root / "cache")
    monkeypatch.setattr(cfg, "SEC_CACHE_DIR", root / "cache" / "sec")
    monkeypatch.setattr(cfg, "FA_OFFLINE", True)
    return root


@pytest.fixture()
def demo_list_path():
    return Path("/workspace/investment_intelligence/fa_fixtures/demo_fa_list.json")
