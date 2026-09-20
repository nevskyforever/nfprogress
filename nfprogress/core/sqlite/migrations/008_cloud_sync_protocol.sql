-- C9 transport foundation. This is deliberately independent from domain_events:
-- Game events may contain context_json; cloud outbox metadata never may.
CREATE TABLE IF NOT EXISTS cloud_sync_state (
    account_id TEXT PRIMARY KEY NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    pull_cursor INTEGER NOT NULL DEFAULT 0 CHECK (pull_cursor >= 0),
    ack_cursor INTEGER NOT NULL DEFAULT 0 CHECK (ack_cursor >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cloud_sync_outbox (
    event_id TEXT PRIMARY KEY NOT NULL CHECK (length(event_id) = 36),
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    entity_type TEXT NOT NULL CHECK (length(entity_type) BETWEEN 1 AND 128),
    operation TEXT NOT NULL CHECK (operation IN ('upsert', 'delete', 'event')),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    last_error TEXT,
    next_attempt_at TEXT,
    CHECK ((operation = 'delete' AND deleted_at IS NOT NULL) OR (operation != 'delete' AND deleted_at IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_cloud_sync_outbox_pending
    ON cloud_sync_outbox(account_id, device_id, next_attempt_at, created_at, event_id);
