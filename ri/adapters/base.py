"""Adapter contract: anything → list[SourceItem]. No auth adapters yet."""
from __future__ import annotations
from typing import Protocol

class Adapter(Protocol):
    def ingest(self, *args, **kwargs) -> list[dict]:
        ...
