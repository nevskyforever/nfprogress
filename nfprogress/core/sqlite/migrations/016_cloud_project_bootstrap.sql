-- C16 durable, restart-safe cloud-project bootstrap state.  This table is
-- deliberately separate from cloud_sync_project_bindings: the bootstrap token
-- must survive before the server registration and before a binding exists.
CREATE TABLE cloud_sync_project_bootstraps (
    project_id TEXT PRIMARY KEY NOT NULL
        REFERENCES projects(id) ON DELETE RESTRICT,
    account_id TEXT NOT NULL
        REFERENCES cloud_sync_state(account_id) ON DELETE RESTRICT,
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    bootstrap_id TEXT NOT NULL CHECK (
        length(bootstrap_id) = 36
        AND bootstrap_id = lower(bootstrap_id)
        AND substr(bootstrap_id, 15, 1) = '4'
        AND substr(bootstrap_id, 20, 1) IN ('8', '9', 'a', 'b')
    ),
    mode TEXT NOT NULL CHECK (mode IN ('upload_existing', 'import_remote')),
    phase TEXT NOT NULL CHECK (
        phase IN ('prepared', 'registered', 'captured', 'completing', 'ready', 'paused', 'blocked')
    ),
    remote_state TEXT CHECK (remote_state IN ('initializing', 'active')),
    initial_event_count INTEGER NOT NULL DEFAULT 0 CHECK (initial_event_count >= 0),
    initial_local_ordinal_hi INTEGER NOT NULL DEFAULT 0 CHECK (initial_local_ordinal_hi >= 0),
    remote_high_water INTEGER CHECK (remote_high_water IS NULL OR remote_high_water >= 0),
    initial_max_server_sequence INTEGER CHECK (
        initial_max_server_sequence IS NULL OR initial_max_server_sequence >= 0
    ),
    blocked_reason TEXT CHECK (
        blocked_reason IS NULL OR length(blocked_reason) BETWEEN 1 AND 128
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (account_id, bootstrap_id),
    CHECK (phase = 'blocked' OR blocked_reason IS NULL),
    CHECK (phase != 'blocked' OR blocked_reason IS NOT NULL),
    CHECK (phase = 'prepared' OR remote_state IS NOT NULL),
    CHECK (mode != 'import_remote' OR initial_event_count = 0)
);
CREATE INDEX idx_cloud_sync_project_bootstraps_account
    ON cloud_sync_project_bootstraps(account_id, phase, project_id);
