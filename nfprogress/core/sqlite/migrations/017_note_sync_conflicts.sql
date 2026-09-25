-- C17 Pass 1: durable, client-side Note conflict preservation.  Plaintext
-- snapshots live only in the local E2EE client database; the cloud service
-- continues to store opaque immutable objects.
CREATE TABLE cloud_sync_note_causal_history (
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    event_id TEXT NOT NULL CHECK (length(event_id) = 36),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    entity_type TEXT NOT NULL CHECK (entity_type = 'note'),
    parent_event_id TEXT CHECK (parent_event_id IS NULL OR length(parent_event_id) = 36),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    server_sequence INTEGER NOT NULL CHECK (server_sequence >= 1),
    operation TEXT NOT NULL CHECK (operation IN ('upsert', 'delete')),
    snapshot_json TEXT NOT NULL CHECK (
        json_valid(snapshot_json) AND json_type(snapshot_json) = 'object'
    ),
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (account_id, event_id),
    UNIQUE (account_id, server_sequence)
);

CREATE TABLE cloud_sync_note_conflict_groups (
    group_id TEXT PRIMARY KEY NOT NULL CHECK (
        length(group_id) = 36 AND length(replace(group_id, '-', '')) = 32
        AND substr(group_id, 9, 1) = '-' AND substr(group_id, 14, 1) = '-'
        AND substr(group_id, 19, 1) = '-' AND substr(group_id, 24, 1) = '-'
        AND group_id NOT GLOB '*[^0-9a-f-]*'
    ),
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    entity_type TEXT NOT NULL CHECK (entity_type = 'note'),
    common_parent_event_id TEXT NOT NULL CHECK (
        length(common_parent_event_id) = 36
        AND length(replace(common_parent_event_id, '-', '')) = 32
        AND substr(common_parent_event_id, 9, 1) = '-'
        AND substr(common_parent_event_id, 14, 1) = '-'
        AND substr(common_parent_event_id, 19, 1) = '-'
        AND substr(common_parent_event_id, 24, 1) = '-'
        AND common_parent_event_id NOT GLOB '*[^0-9A-Fa-f-]*'
    ),
    tip_revision INTEGER NOT NULL CHECK (tip_revision >= 2),
    generation INTEGER NOT NULL CHECK (generation >= 1),
    lifecycle TEXT NOT NULL CHECK (
        lifecycle IN ('open', 'resolving', 'resolved', 'abandoned')
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (account_id, project_id, entity_id, entity_type, group_id)
);
CREATE UNIQUE INDEX idx_cloud_sync_note_conflict_groups_open
    ON cloud_sync_note_conflict_groups(account_id, project_id, entity_id, entity_type)
    WHERE lifecycle = 'open';

CREATE TABLE cloud_sync_note_conflict_versions (
    version_id TEXT PRIMARY KEY NOT NULL CHECK (length(version_id) BETWEEN 1 AND 768),
    group_id TEXT NOT NULL
        REFERENCES cloud_sync_note_conflict_groups(group_id) ON DELETE RESTRICT,
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    entity_type TEXT NOT NULL CHECK (entity_type = 'note'),
    event_id TEXT NOT NULL CHECK (length(event_id) = 36),
    parent_event_id TEXT NOT NULL CHECK (length(parent_event_id) = 36),
    revision INTEGER NOT NULL CHECK (revision >= 2),
    server_sequence INTEGER CHECK (server_sequence IS NULL OR server_sequence >= 1),
    operation TEXT NOT NULL CHECK (operation IN ('upsert', 'delete')),
    snapshot_json TEXT NOT NULL CHECK (
        json_valid(snapshot_json) AND json_type(snapshot_json) = 'object'
    ),
    source TEXT NOT NULL CHECK (source IN ('remote', 'remote_applied', 'local_unsealed')),
    local_mutation_generation INTEGER CHECK (
        local_mutation_generation IS NULL OR local_mutation_generation >= 1
    ),
    local_outbox_lifecycle TEXT CHECK (
        local_outbox_lifecycle IS NULL OR local_outbox_lifecycle = 'unsealed'
    ),
    conflict_generation INTEGER NOT NULL CHECK (conflict_generation >= 1),
    preserved_at TEXT NOT NULL,
    UNIQUE (group_id, event_id, source, local_mutation_generation),
    CHECK (
        (source IN ('remote', 'remote_applied') AND server_sequence IS NOT NULL
            AND local_mutation_generation IS NULL AND local_outbox_lifecycle IS NULL)
        OR
        (source = 'local_unsealed' AND server_sequence IS NULL
            AND local_mutation_generation IS NOT NULL AND local_outbox_lifecycle = 'unsealed')
    )
);
CREATE INDEX idx_cloud_sync_note_conflict_versions_entity
    ON cloud_sync_note_conflict_versions(account_id, project_id, entity_id, group_id);

CREATE TABLE cloud_sync_note_conflict_tips (
    group_id TEXT NOT NULL
        REFERENCES cloud_sync_note_conflict_groups(group_id) ON DELETE RESTRICT,
    version_id TEXT NOT NULL
        REFERENCES cloud_sync_note_conflict_versions(version_id) ON DELETE RESTRICT,
    event_id TEXT NOT NULL CHECK (length(event_id) = 36),
    generation INTEGER NOT NULL CHECK (generation >= 1),
    PRIMARY KEY (group_id, event_id),
    UNIQUE (group_id, version_id)
);

-- SQLite cannot extend the inbox state CHECK in place.  Rebuild it without
-- changing any legacy row or uniqueness rule, and add the durable proof link.
ALTER TABLE cloud_sync_inbox RENAME TO cloud_sync_inbox_v16;
DROP INDEX idx_cloud_sync_inbox_processing;
CREATE TABLE cloud_sync_inbox (
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
    state TEXT NOT NULL CHECK (state IN (
        'received', 'unknown_entity', 'orphan', 'applied', 'conflict',
        'conflict_preserved', 'rejected'
    )),
    received_at TEXT NOT NULL,
    applied_at TEXT,
    error_code TEXT,
    conflict_group_id TEXT
        REFERENCES cloud_sync_note_conflict_groups(group_id) ON DELETE RESTRICT,
    conflict_preserved_at TEXT,
    PRIMARY KEY (account_id, event_id),
    UNIQUE (account_id, server_sequence),
    CHECK ((operation = 'delete' AND deleted_at IS NOT NULL)
        OR (operation != 'delete' AND deleted_at IS NULL)),
    CHECK (
        (state = 'conflict_preserved' AND conflict_group_id IS NOT NULL
            AND conflict_preserved_at IS NOT NULL)
        OR
        (state != 'conflict_preserved' AND conflict_group_id IS NULL
            AND conflict_preserved_at IS NULL)
    )
);
INSERT INTO cloud_sync_inbox(
    account_id,event_id,server_sequence,device_id,project_id,entity_id,
    entity_type,operation,sync_revision,updated_at,deleted_at,state,
    received_at,applied_at,error_code,conflict_group_id,conflict_preserved_at
)
SELECT account_id,event_id,server_sequence,device_id,project_id,entity_id,
       entity_type,operation,sync_revision,updated_at,deleted_at,state,
       received_at,applied_at,error_code,NULL,NULL
FROM cloud_sync_inbox_v16;
DROP TABLE cloud_sync_inbox_v16;
CREATE INDEX idx_cloud_sync_inbox_processing
    ON cloud_sync_inbox(account_id, state, server_sequence);

-- Conflict versions are evidence, not a cache.  Future resolution may change
-- group lifecycle and append new tips, but preserved version bytes, existing
-- tips, and causal identity cannot be edited or pruned by ordinary SQL.
CREATE TRIGGER cloud_sync_note_conflict_versions_immutable_update
BEFORE UPDATE ON cloud_sync_note_conflict_versions
BEGIN SELECT RAISE(ABORT, 'note_conflict_version_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_conflict_versions_immutable_delete
BEFORE DELETE ON cloud_sync_note_conflict_versions
BEGIN SELECT RAISE(ABORT, 'note_conflict_version_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_causal_history_immutable_update
BEFORE UPDATE ON cloud_sync_note_causal_history
BEGIN SELECT RAISE(ABORT, 'note_causal_history_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_causal_history_immutable_delete
BEFORE DELETE ON cloud_sync_note_causal_history
BEGIN SELECT RAISE(ABORT, 'note_causal_history_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_conflict_tips_immutable_update
BEFORE UPDATE ON cloud_sync_note_conflict_tips
BEGIN SELECT RAISE(ABORT, 'note_conflict_tip_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_conflict_tips_immutable_delete
BEFORE DELETE ON cloud_sync_note_conflict_tips
BEGIN SELECT RAISE(ABORT, 'note_conflict_tip_is_immutable'); END;
