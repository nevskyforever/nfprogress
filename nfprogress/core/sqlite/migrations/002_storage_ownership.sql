CREATE TABLE IF NOT EXISTS storage_ownership (
    subsystem TEXT PRIMARY KEY CHECK (subsystem IN ('projects', 'settings', 'notes', 'game')),
    owner TEXT NOT NULL CHECK (owner IN ('pickle', 'sqlite')),
    schema_version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO storage_ownership(subsystem, owner, schema_version, updated_at)
VALUES
    ('projects', 'pickle', 1, datetime('now')),
    ('settings', 'pickle', 1, datetime('now')),
    ('notes', 'pickle', 1, datetime('now')),
    ('game', 'pickle', 1, datetime('now'));
