-- F3: Game authority, durable consumer attempts and migration provenance.
-- The broad JSON payload remains forward-compatible; the table is now the
-- canonical aggregate rather than a pickle mirror.
CREATE TABLE IF NOT EXISTS domain_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    project_id TEXT NOT NULL,
    stage_id TEXT,
    progress_id TEXT,
    effective_date TEXT,
    delta_symbols REAL,
    context_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    processed_at TEXT,
    consumer TEXT NOT NULL DEFAULT 'game',
    version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS game_metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);

ALTER TABLE domain_events ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE domain_events ADD COLUMN last_error TEXT;
ALTER TABLE domain_events ADD COLUMN failed_at TEXT;
ALTER TABLE domain_events ADD COLUMN status TEXT NOT NULL DEFAULT 'pending';

DROP INDEX IF EXISTS idx_domain_events_pending;
CREATE INDEX IF NOT EXISTS idx_domain_events_pending
    ON domain_events(consumer, status, processed_at, created_at, event_id);

CREATE INDEX IF NOT EXISTS idx_domain_events_processing
    ON domain_events(consumer, status, processed_at, created_at, event_id);

INSERT OR IGNORE INTO game_metadata(key, value_json)
VALUES ('state_schema_version', '2');
