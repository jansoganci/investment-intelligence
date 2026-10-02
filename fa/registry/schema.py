"""SQLite DDL for Company FA History / Run Registry (Plan §0.D LOCKED columns)."""
from __future__ import annotations

SCHEMA_VERSION = 1

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    entity_name TEXT,
    cik TEXT,
    gate0_class TEXT,
    fa_list_member INTEGER NOT NULL DEFAULT 0,
    fa_list_as_of TEXT,
    current_analysis_run_id TEXT,
    stale_flag INTEGER NOT NULL DEFAULT 0,
    stale_reason TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    actor TEXT,
    trigger TEXT,
    intent TEXT,
    status TEXT NOT NULL,
    stale_reason TEXT,
    parent_run_id TEXT,
    git_sha TEXT,
    code_fingerprint TEXT,
    notes TEXT,
    FOREIGN KEY (ticker) REFERENCES companies(ticker),
    FOREIGN KEY (parent_run_id) REFERENCES analysis_runs(run_id)
);

CREATE TABLE IF NOT EXISTS stage_results (
    stage_result_id TEXT PRIMARY KEY,
    run_id TEXT,
    ticker TEXT NOT NULL,
    stage INTEGER NOT NULL CHECK (stage >= 1 AND stage <= 9),
    version_id TEXT NOT NULL,
    process_outcome TEXT,
    terminates_later_stages INTEGER,
    artifact_json_path TEXT,
    artifact_md_path TEXT,
    saved_at TEXT,
    is_current INTEGER NOT NULL DEFAULT 0,
    supersedes_stage_result_id TEXT,
    superseded_by_stage_result_id TEXT,
    uat_status TEXT NOT NULL DEFAULT 'none',
    uat_pack_path TEXT,
    content_sha256 TEXT,
    UNIQUE (ticker, stage, version_id),
    FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id),
    FOREIGN KEY (ticker) REFERENCES companies(ticker),
    FOREIGN KEY (supersedes_stage_result_id) REFERENCES stage_results(stage_result_id),
    FOREIGN KEY (superseded_by_stage_result_id) REFERENCES stage_results(stage_result_id)
);

CREATE TABLE IF NOT EXISTS final_fa_results (
    final_fa_result_id TEXT PRIMARY KEY,
    run_id TEXT,
    ticker TEXT NOT NULL,
    version_id TEXT NOT NULL,
    final_state TEXT,
    technical_eligible INTEGER,
    artifact_json_path TEXT,
    artifact_md_path TEXT,
    saved_at TEXT,
    is_current INTEGER NOT NULL DEFAULT 0,
    supersedes_final_fa_result_id TEXT,
    superseded_by_final_fa_result_id TEXT,
    stage_result_ids_consumed TEXT,
    uat_status TEXT NOT NULL DEFAULT 'none',
    uat_pack_path TEXT,
    content_sha256 TEXT,
    UNIQUE (ticker, version_id),
    FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id),
    FOREIGN KEY (ticker) REFERENCES companies(ticker),
    FOREIGN KEY (supersedes_final_fa_result_id) REFERENCES final_fa_results(final_fa_result_id),
    FOREIGN KEY (superseded_by_final_fa_result_id) REFERENCES final_fa_results(final_fa_result_id)
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ticker TEXT,
    run_id TEXT,
    payload_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_stage_results_ticker_stage_current
    ON stage_results(ticker, stage, is_current);
CREATE INDEX IF NOT EXISTS idx_stage_results_run_id ON stage_results(run_id);
CREATE INDEX IF NOT EXISTS idx_final_fa_ticker_current
    ON final_fa_results(ticker, is_current);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_ticker ON analysis_runs(ticker);
CREATE INDEX IF NOT EXISTS idx_events_ticker_ts ON events(ticker, ts);

-- At most one CURRENT per (ticker, stage) via partial unique index (SQLite 3.8+)
CREATE UNIQUE INDEX IF NOT EXISTS uq_stage_current
    ON stage_results(ticker, stage) WHERE is_current = 1;
CREATE UNIQUE INDEX IF NOT EXISTS uq_final_fa_current
    ON final_fa_results(ticker) WHERE is_current = 1;

CREATE VIEW IF NOT EXISTS v_company_stage_matrix AS
SELECT
    c.ticker AS ticker,
    c.gate0_class AS gate0_class,
    c.stale_flag AS stale_flag,
    c.stale_reason AS stale_reason,
    c.current_analysis_run_id AS last_run_id,
    MAX(CASE WHEN s.stage = 1 THEN s.process_outcome END) AS s1_process_outcome,
    MAX(CASE WHEN s.stage = 1 THEN s.version_id END) AS s1_version_id,
    MAX(CASE WHEN s.stage = 1 THEN s.saved_at END) AS s1_saved_at,
    MAX(CASE WHEN s.stage = 1 THEN s.uat_status END) AS s1_uat_status,
    MAX(CASE WHEN s.stage = 2 THEN s.process_outcome END) AS s2_process_outcome,
    MAX(CASE WHEN s.stage = 2 THEN s.version_id END) AS s2_version_id,
    MAX(CASE WHEN s.stage = 2 THEN s.saved_at END) AS s2_saved_at,
    MAX(CASE WHEN s.stage = 2 THEN s.uat_status END) AS s2_uat_status,
    MAX(CASE WHEN s.stage = 3 THEN s.process_outcome END) AS s3_process_outcome,
    MAX(CASE WHEN s.stage = 3 THEN s.version_id END) AS s3_version_id,
    MAX(CASE WHEN s.stage = 3 THEN s.saved_at END) AS s3_saved_at,
    MAX(CASE WHEN s.stage = 3 THEN s.uat_status END) AS s3_uat_status,
    MAX(CASE WHEN s.stage = 4 THEN s.process_outcome END) AS s4_process_outcome,
    MAX(CASE WHEN s.stage = 4 THEN s.version_id END) AS s4_version_id,
    MAX(CASE WHEN s.stage = 4 THEN s.saved_at END) AS s4_saved_at,
    MAX(CASE WHEN s.stage = 4 THEN s.uat_status END) AS s4_uat_status,
    MAX(CASE WHEN s.stage = 5 THEN s.process_outcome END) AS s5_process_outcome,
    MAX(CASE WHEN s.stage = 5 THEN s.version_id END) AS s5_version_id,
    MAX(CASE WHEN s.stage = 5 THEN s.saved_at END) AS s5_saved_at,
    MAX(CASE WHEN s.stage = 5 THEN s.uat_status END) AS s5_uat_status,
    MAX(CASE WHEN s.stage = 6 THEN s.process_outcome END) AS s6_process_outcome,
    MAX(CASE WHEN s.stage = 6 THEN s.version_id END) AS s6_version_id,
    MAX(CASE WHEN s.stage = 6 THEN s.saved_at END) AS s6_saved_at,
    MAX(CASE WHEN s.stage = 6 THEN s.uat_status END) AS s6_uat_status,
    MAX(CASE WHEN s.stage = 7 THEN s.process_outcome END) AS s7_process_outcome,
    MAX(CASE WHEN s.stage = 7 THEN s.version_id END) AS s7_version_id,
    MAX(CASE WHEN s.stage = 7 THEN s.saved_at END) AS s7_saved_at,
    MAX(CASE WHEN s.stage = 7 THEN s.uat_status END) AS s7_uat_status,
    MAX(CASE WHEN s.stage = 8 THEN s.process_outcome END) AS s8_process_outcome,
    MAX(CASE WHEN s.stage = 8 THEN s.version_id END) AS s8_version_id,
    MAX(CASE WHEN s.stage = 8 THEN s.saved_at END) AS s8_saved_at,
    MAX(CASE WHEN s.stage = 8 THEN s.uat_status END) AS s8_uat_status,
    MAX(CASE WHEN s.stage = 9 THEN s.process_outcome END) AS s9_process_outcome,
    MAX(CASE WHEN s.stage = 9 THEN s.version_id END) AS s9_version_id,
    MAX(CASE WHEN s.stage = 9 THEN s.saved_at END) AS s9_saved_at,
    MAX(CASE WHEN s.stage = 9 THEN s.uat_status END) AS s9_uat_status,
    f.final_state AS final_fa_final_state,
    f.technical_eligible AS final_fa_technical_eligible,
    f.version_id AS final_fa_version_id,
    f.uat_status AS final_fa_uat_status
FROM companies c
LEFT JOIN stage_results s ON s.ticker = c.ticker AND s.is_current = 1
LEFT JOIN final_fa_results f ON f.ticker = c.ticker AND f.is_current = 1
GROUP BY c.ticker;

CREATE VIEW IF NOT EXISTS v_company_current_fa AS
SELECT
    c.ticker,
    c.entity_name,
    c.gate0_class,
    c.stale_flag,
    c.stale_reason,
    c.current_analysis_run_id,
    f.final_fa_result_id,
    f.version_id AS final_fa_version_id,
    f.final_state,
    f.technical_eligible,
    f.artifact_json_path AS final_fa_json_path,
    f.saved_at AS final_fa_saved_at,
    f.uat_status AS final_fa_uat_status
FROM companies c
LEFT JOIN final_fa_results f ON f.ticker = c.ticker AND f.is_current = 1;

CREATE VIEW IF NOT EXISTS v_company_history AS
SELECT
    'stage' AS result_kind,
    sr.ticker,
    sr.stage AS stage_or_null,
    sr.version_id,
    sr.process_outcome AS outcome_or_state,
    sr.saved_at,
    sr.is_current,
    sr.run_id,
    sr.stage_result_id AS result_id,
    sr.artifact_json_path,
    sr.uat_status
FROM stage_results sr
UNION ALL
SELECT
    'final_fa' AS result_kind,
    fr.ticker,
    NULL AS stage_or_null,
    fr.version_id,
    fr.final_state AS outcome_or_state,
    fr.saved_at,
    fr.is_current,
    fr.run_id,
    fr.final_fa_result_id AS result_id,
    fr.artifact_json_path,
    fr.uat_status
FROM final_fa_results fr;

CREATE VIEW IF NOT EXISTS v_stale_analysis AS
SELECT
    c.ticker,
    c.entity_name,
    c.stale_flag,
    c.stale_reason,
    c.current_analysis_run_id,
    c.updated_at,
    r.status AS run_status,
    r.stale_reason AS run_stale_reason,
    r.ended_at AS run_ended_at
FROM companies c
LEFT JOIN analysis_runs r ON r.run_id = c.current_analysis_run_id
WHERE c.stale_flag = 1
   OR (r.stale_reason IS NOT NULL AND r.stale_reason != '');
"""
