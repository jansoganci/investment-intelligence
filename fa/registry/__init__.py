"""Company FA History / Run Registry — indexed metadata; artifacts remain truth.

Lifecycle: DONE / UAT_ACCEPTED (2026-10-01).
Plan: butterbear 00_System/COMPANY_FA_HISTORY_REGISTRY_PLAN_v1.md §0 (Plan wins).
Does not implement Final FA synthesis. Does not change Stages 1–9 analytical logic.
Thin post-artifact write hooks: fa.registry.hooks (Plan §0.F).
"""
from __future__ import annotations

from .backup import backup_registry, restore_registry_from_backup
from .backfill import backfill_registry, scan_company_thesis
from .db import RegistryError, open_registry, registry_session
from .drift import detect_drift, repair_drift_from_disk
from .paths import registry_db_path, registry_dir
from .views_export import export_company_stage_matrix, fetch_company_stage_matrix
from .hooks import (
    RegistryHookError,
    hook_final_fa_after_artifact,
    hook_stage_after_save,
    hooks_enabled,
    register_final_fa_artifact,
)
from .writers import (
    complete_run,
    ensure_company,
    fail_run,
    make_run_id,
    mark_company_stale,
    record_final_fa_result,
    record_stage_after_artifact,
    record_stage_result,
    set_uat_status,
    start_run,
)

__all__ = [
    "RegistryError",
    "RegistryHookError",
    "backup_registry",
    "backfill_registry",
    "complete_run",
    "detect_drift",
    "ensure_company",
    "export_company_stage_matrix",
    "fail_run",
    "fetch_company_stage_matrix",
    "hook_final_fa_after_artifact",
    "hook_stage_after_save",
    "hooks_enabled",
    "make_run_id",
    "mark_company_stale",
    "open_registry",
    "record_final_fa_result",
    "record_stage_after_artifact",
    "record_stage_result",
    "register_final_fa_artifact",
    "registry_db_path",
    "registry_dir",
    "registry_session",
    "repair_drift_from_disk",
    "restore_registry_from_backup",
    "scan_company_thesis",
    "set_uat_status",
    "start_run",
]
