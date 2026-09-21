-- C15 durable encrypted-sync substrate.  Event objects are deliberately
-- opaque here; codec, cryptography, and sync behavior arrive in later slices.
ALTER TABLE cloud_sync_outbox
    ADD COLUMN parent_event_id TEXT
    CHECK (parent_event_id IS NULL OR (
        length(parent_event_id) = 36
        AND length(replace(parent_event_id, '-', '')) = 32
        AND substr(parent_event_id, 9, 1) = '-'
        AND substr(parent_event_id, 14, 1) = '-'
        AND substr(parent_event_id, 19, 1) = '-'
        AND substr(parent_event_id, 24, 1) = '-'
        AND parent_event_id NOT GLOB '*[^0-9A-Fa-f-]*'
    ));
ALTER TABLE cloud_sync_outbox
    ADD COLUMN local_ordinal INTEGER NOT NULL DEFAULT 0
    CHECK (local_ordinal >= 0);
ALTER TABLE cloud_sync_outbox
    ADD COLUMN lifecycle TEXT NOT NULL DEFAULT 'legacy'
    CHECK (lifecycle IN ('legacy', 'unsealed', 'sealed', 'accepted', 'rejected', 'superseded'));

CREATE INDEX IF NOT EXISTS idx_cloud_sync_outbox_c15_lifecycle
    ON cloud_sync_outbox(account_id, device_id, lifecycle, local_ordinal, event_id);

CREATE TABLE IF NOT EXISTS cloud_sync_event_objects (
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    event_id TEXT NOT NULL CHECK (
        length(event_id) = 36 AND length(replace(event_id, '-', '')) = 32
        AND substr(event_id, 9, 1) = '-' AND substr(event_id, 14, 1) = '-'
        AND substr(event_id, 19, 1) = '-' AND substr(event_id, 24, 1) = '-'
        AND event_id NOT GLOB '*[^0-9A-Fa-f-]*'
    ),
    crypto_version INTEGER NOT NULL CHECK (crypto_version >= 1),
    aad_version INTEGER NOT NULL CHECK (aad_version >= 1),
    nonce BLOB NOT NULL CHECK (typeof(nonce) = 'blob' AND length(nonce) = 24),
    ciphertext BLOB NOT NULL CHECK (typeof(ciphertext) = 'blob' AND length(ciphertext) >= 16),
    stored_at TEXT NOT NULL,
    PRIMARY KEY (account_id, event_id)
);

CREATE TABLE IF NOT EXISTS cloud_sync_inbox (
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    event_id TEXT NOT NULL CHECK (
        length(event_id) = 36 AND length(replace(event_id, '-', '')) = 32
        AND substr(event_id, 9, 1) = '-' AND substr(event_id, 14, 1) = '-'
        AND substr(event_id, 19, 1) = '-' AND substr(event_id, 24, 1) = '-'
        AND event_id NOT GLOB '*[^0-9A-Fa-f-]*'
    ),
    server_sequence INTEGER NOT NULL CHECK (server_sequence >= 1),
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    entity_type TEXT NOT NULL CHECK (length(entity_type) BETWEEN 1 AND 128),
    operation TEXT NOT NULL CHECK (operation IN ('upsert', 'delete', 'event')),
    sync_revision INTEGER NOT NULL CHECK (sync_revision >= 1),
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    state TEXT NOT NULL CHECK (state IN ('received', 'unknown_entity', 'orphan', 'applied', 'conflict', 'rejected')),
    received_at TEXT NOT NULL,
    applied_at TEXT,
    error_code TEXT,
    PRIMARY KEY (account_id, event_id),
    UNIQUE (account_id, server_sequence),
    CHECK ((operation = 'delete' AND deleted_at IS NOT NULL) OR (operation != 'delete' AND deleted_at IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_cloud_sync_inbox_processing
    ON cloud_sync_inbox(account_id, state, server_sequence);

CREATE TABLE IF NOT EXISTS cloud_sync_entities (
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    entity_type TEXT NOT NULL CHECK (length(entity_type) BETWEEN 1 AND 128),
    head_event_id TEXT NOT NULL CHECK (
        length(head_event_id) = 36 AND length(replace(head_event_id, '-', '')) = 32
        AND substr(head_event_id, 9, 1) = '-' AND substr(head_event_id, 14, 1) = '-'
        AND substr(head_event_id, 19, 1) = '-' AND substr(head_event_id, 24, 1) = '-'
        AND head_event_id NOT GLOB '*[^0-9A-Fa-f-]*'
    ),
    head_sync_revision INTEGER NOT NULL CHECK (head_sync_revision >= 1),
    conflict_event_id TEXT CHECK (conflict_event_id IS NULL OR (
        length(conflict_event_id) = 36
        AND length(replace(conflict_event_id, '-', '')) = 32
        AND substr(conflict_event_id, 9, 1) = '-'
        AND substr(conflict_event_id, 14, 1) = '-'
        AND substr(conflict_event_id, 19, 1) = '-'
        AND substr(conflict_event_id, 24, 1) = '-'
        AND conflict_event_id NOT GLOB '*[^0-9A-Fa-f-]*'
    )),
    conflict_state TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (account_id, project_id, entity_id, entity_type),
    CHECK ((conflict_event_id IS NULL AND conflict_state IS NULL) OR (conflict_event_id IS NOT NULL AND conflict_state IS NOT NULL))
);
