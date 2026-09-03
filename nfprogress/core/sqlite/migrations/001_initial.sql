CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    goal REAL,
    infinite INTEGER NOT NULL CHECK (infinite IN (0, 1)),
    unit TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    goal REAL,
    infinite INTEGER NOT NULL CHECK (infinite IN (0, 1)),
    unit TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress_entries (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage_id TEXT REFERENCES stages(id) ON DELETE CASCADE,
    created_at TEXT,
    added_symbols REAL,
    added_progress REAL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage_id TEXT REFERENCES stages(id) ON DELETE CASCADE,
    updated_at TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    schema_version INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mirror_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    source_format TEXT NOT NULL,
    source_schema_version TEXT NOT NULL,
    last_full_sync_at TEXT,
    last_successful_sync_at TEXT,
    sync_status TEXT NOT NULL CHECK (sync_status IN ('healthy', 'dirty', 'rebuild_required')),
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_stages_project_id ON stages(project_id);
CREATE INDEX IF NOT EXISTS idx_progress_project_id ON progress_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_progress_stage_id ON progress_entries(stage_id);
CREATE INDEX IF NOT EXISTS idx_notes_project_id ON notes(project_id);
