SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS pipelines (
    id TEXT PRIMARY KEY,
    entry_kind TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    meta_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS stages (
    id TEXT PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    stage_def_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error TEXT,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    stage_id TEXT NOT NULL,
    type TEXT NOT NULL,
    path TEXT,
    content_hash TEXT,
    meta_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id TEXT NOT NULL,
    stage_id TEXT,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    cached INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS kb_deltas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id TEXT NOT NULL,
    stage_id TEXT,
    target TEXT NOT NULL,
    operation TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id TEXT,
    level TEXT NOT NULL DEFAULT 'info',
    type TEXT NOT NULL,
    ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resume_tokens (
    pipeline_id TEXT PRIMARY KEY,
    token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pipelines_status ON pipelines(status);
CREATE INDEX IF NOT EXISTS idx_pipelines_created ON pipelines(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stages_pipeline ON stages(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_pipeline ON artifacts(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_stage ON artifacts(stage_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_pipeline ON llm_calls(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created ON llm_calls(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kb_deltas_fingerprint ON kb_deltas(fingerprint);

CREATE VIEW IF NOT EXISTS v_pipeline_summary AS
SELECT p.id, p.status, p.entry_kind, p.profile_id,
       p.created_at, p.updated_at,
       (SELECT COUNT(*) FROM stages WHERE pipeline_id = p.id) AS stage_count,
       (SELECT COUNT(*) FROM stages WHERE pipeline_id = p.id AND status='SUCCESS') AS done_count,
       (SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE pipeline_id = p.id) AS total_cost
FROM pipelines p;

CREATE VIEW IF NOT EXISTS v_cost_daily AS
SELECT DATE(created_at) AS day,
       model,
       COUNT(*) AS calls,
       SUM(input_tokens) AS in_tok,
       SUM(output_tokens) AS out_tok,
       SUM(cost_usd) AS cost
FROM llm_calls
GROUP BY DATE(created_at), model;
"""

VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"RUNNING", "SKIPPED"},
    "RUNNING": {"SUCCESS", "FAILED"},
    "SUCCESS": set(),
    "FAILED": {"PENDING"},
    "SKIPPED": set(),
    "NEW": {"RUNNING"},
    "PAUSED": {"RUNNING"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}
