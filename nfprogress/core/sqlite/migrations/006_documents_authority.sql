-- F6: Documents are application-owned SQLite records. External files remain
-- user-owned synchronization peers and are never copied or deleted here.
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    scope_key TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    stage_id TEXT REFERENCES stages(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    content_json TEXT NOT NULL,
    content_format TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    extensions_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_stage ON documents(stage_id);

CREATE TABLE IF NOT EXISTS document_bindings (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL UNIQUE REFERENCES documents(id) ON DELETE RESTRICT,
    binding_type TEXT NOT NULL,
    external_path TEXT NOT NULL,
    source_id TEXT,
    last_external_hash TEXT,
    last_synced_revision INTEGER NOT NULL DEFAULT 0 CHECK (last_synced_revision >= 0),
    last_synced_hash TEXT,
    last_synced_at TEXT,
    sync_state TEXT NOT NULL DEFAULT 'unlinked',
    expected_external_hash TEXT,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_document_bindings_path
    ON document_bindings(external_path);

CREATE TABLE IF NOT EXISTS document_metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);

-- Records that cannot be attached to an existing stable Project/Stage remain
-- inspectable recovery data instead of being silently discarded.
CREATE TABLE IF NOT EXISTS document_migration_orphans (
    source_key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    reason TEXT NOT NULL
);
