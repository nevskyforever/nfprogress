-- F1: lossless Projects aggregate substrate.
-- The legacy core tables stay column-compatible with v3.  Auxiliary records
-- preserve fields which cannot yet be normalized without changing the mirror
-- contract, while explicit order/binding tables make them queryable.

CREATE TABLE IF NOT EXISTS project_metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_folders (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    payload_json TEXT NOT NULL,
    UNIQUE(position)
);

CREATE TABLE IF NOT EXISTS project_folder_members (
    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE RESTRICT,
    folder_id TEXT NOT NULL REFERENCES project_folders(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_project_folder_members_folder
    ON project_folder_members(folder_id);

CREATE TABLE IF NOT EXISTS stage_order (
    stage_id TEXT PRIMARY KEY REFERENCES stages(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0),
    UNIQUE(project_id, position)
);

INSERT OR IGNORE INTO stage_order(stage_id, project_id, position)
SELECT id, project_id,
       row_number() OVER (PARTITION BY project_id ORDER BY rowid) - 1
FROM stages;

CREATE TABLE IF NOT EXISTS project_bindings (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    stage_id TEXT REFERENCES stages(id) ON DELETE RESTRICT,
    binding_type TEXT NOT NULL,
    external_path TEXT,
    source_id TEXT,
    content_hash TEXT,
    last_synced_at TEXT,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_bindings_project
    ON project_bindings(project_id);
CREATE INDEX IF NOT EXISTS idx_project_bindings_stage
    ON project_bindings(stage_id);

CREATE TABLE IF NOT EXISTS project_extensions (
    entity_type TEXT NOT NULL CHECK (entity_type IN ('root', 'project', 'stage', 'progress')),
    entity_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY(entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS progress_order (
    entry_id TEXT PRIMARY KEY REFERENCES progress_entries(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0),
    UNIQUE(position)
);

CREATE TABLE IF NOT EXISTS migration_sources (
    name TEXT PRIMARY KEY,
    source_format TEXT NOT NULL,
    source_schema_version TEXT,
    checksum TEXT,
    size_bytes INTEGER,
    captured_at TEXT,
    metadata_json TEXT NOT NULL
);

-- v3's notes used cascading FKs.  Notes are already SQLite-authoritative and
-- project storage primitives must not erase them implicitly, so rebuild the
-- table with RESTRICT semantics.  The copy is transactional with this
-- migration and retains the v3 payload verbatim.
ALTER TABLE notes RENAME TO notes_v3;
CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    stage_id TEXT REFERENCES stages(id) ON DELETE RESTRICT,
    updated_at TEXT,
    payload_json TEXT NOT NULL
);
INSERT INTO notes(id, project_id, stage_id, updated_at, payload_json)
SELECT id, project_id, stage_id, updated_at, payload_json FROM notes_v3;
DROP TABLE notes_v3;
CREATE INDEX IF NOT EXISTS idx_notes_project_id ON notes(project_id);

-- The rowid order is the legacy progress-list order.  It is copied once into
-- an explicit stable order relation so later reads do not depend on storage
-- implementation details.  Re-running the migration is a no-op.
INSERT OR IGNORE INTO progress_order(entry_id, position)
SELECT id, row_number() OVER (ORDER BY rowid) - 1 FROM progress_entries;

UPDATE mirror_state
SET sync_status = CASE
        WHEN sync_status = 'healthy' THEN 'rebuild_required'
        ELSE sync_status
    END,
    last_error = CASE
        WHEN sync_status = 'healthy' THEN 'Projects authority substrate requires a mirror rebuild'
        ELSE last_error
    END
WHERE id = 1;
