-- C17 Pass 2D: applied resolution events remain local plaintext until a
-- future protocol-v2 E2EE sealing boundary is implemented. They never enter
-- the protocol-v1 outbox.
CREATE TABLE cloud_sync_note_resolution_outbox (
    resolution_event_id TEXT PRIMARY KEY NOT NULL
        REFERENCES cloud_sync_note_pending_resolutions(resolution_event_id) ON DELETE RESTRICT,
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    clone_entity_id TEXT,
    conflict_group_id TEXT NOT NULL
        REFERENCES cloud_sync_note_conflict_groups(group_id) ON DELETE RESTRICT,
    conflict_generation INTEGER NOT NULL CHECK (conflict_generation >= 1),
    revision INTEGER NOT NULL CHECK (revision >= 2),
    parent_event_ids_json TEXT NOT NULL CHECK (
        json_valid(parent_event_ids_json)
        AND json_type(parent_event_ids_json) = 'array'
        AND json_array_length(parent_event_ids_json) BETWEEN 2 AND 64
    ),
    strategy TEXT NOT NULL CHECK (
        strategy IN ('choose_version', 'manual_merge', 'keep_both', 'delete')
    ),
    result_operation TEXT NOT NULL CHECK (result_operation IN ('upsert', 'delete')),
    canonical_payload BLOB NOT NULL CHECK (length(canonical_payload) BETWEEN 1 AND 8388608),
    lifecycle TEXT NOT NULL CHECK (lifecycle = 'local_pending'),
    applied_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (conflict_group_id),
    CHECK (clone_entity_id IS NULL OR (length(clone_entity_id) BETWEEN 1 AND 512
        AND clone_entity_id != entity_id)),
    CHECK ((strategy = 'keep_both') = (clone_entity_id IS NOT NULL))
);
CREATE INDEX idx_cloud_sync_note_resolution_outbox_scope
    ON cloud_sync_note_resolution_outbox(account_id, project_id, entity_id, lifecycle);

CREATE TABLE cloud_sync_note_resolution_dependencies (
    resolution_event_id TEXT NOT NULL
        REFERENCES cloud_sync_note_resolution_outbox(resolution_event_id) ON DELETE RESTRICT,
    parent_event_id TEXT NOT NULL CHECK (length(parent_event_id) = 36),
    source TEXT NOT NULL CHECK (source IN ('remote', 'remote_applied', 'local_unsealed')),
    server_sequence INTEGER CHECK (server_sequence IS NULL OR server_sequence >= 1),
    local_mutation_generation INTEGER CHECK (
        local_mutation_generation IS NULL OR local_mutation_generation >= 1
    ),
    local_outbox_lifecycle TEXT CHECK (
        local_outbox_lifecycle IS NULL
        OR local_outbox_lifecycle IN ('unsealed', 'sealed', 'accepted')
    ),
    upload_receipt_sequence INTEGER CHECK (
        upload_receipt_sequence IS NULL OR upload_receipt_sequence >= 1
    ),
    snapshot_json TEXT NOT NULL CHECK (
        json_valid(snapshot_json) AND json_type(snapshot_json) = 'object'
    ),
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (resolution_event_id, parent_event_id),
    CHECK (
        (source IN ('remote', 'remote_applied') AND server_sequence IS NOT NULL
            AND local_mutation_generation IS NULL AND local_outbox_lifecycle IS NULL)
        OR
        (source = 'local_unsealed' AND server_sequence IS NULL
            AND local_mutation_generation IS NOT NULL
            AND local_outbox_lifecycle IS NOT NULL)
    )
);

CREATE TRIGGER cloud_sync_note_resolution_outbox_immutable_update
BEFORE UPDATE ON cloud_sync_note_resolution_outbox
BEGIN SELECT RAISE(ABORT, 'note_resolution_outbox_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_outbox_immutable_delete
BEFORE DELETE ON cloud_sync_note_resolution_outbox
BEGIN SELECT RAISE(ABORT, 'note_resolution_outbox_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_dependencies_immutable_update
BEFORE UPDATE ON cloud_sync_note_resolution_dependencies
BEGIN SELECT RAISE(ABORT, 'note_resolution_dependency_is_immutable'); END;
CREATE TRIGGER cloud_sync_note_resolution_dependencies_immutable_delete
BEFORE DELETE ON cloud_sync_note_resolution_dependencies
BEGIN SELECT RAISE(ABORT, 'note_resolution_dependency_is_immutable'); END;

-- A referenced unsealed parent may still be sealed normally, but its event
-- identity/snapshot may no longer be coalesced into different plaintext.
CREATE TRIGGER cloud_sync_note_resolution_freeze_parent_update
BEFORE UPDATE OF mutation_generation, snapshot_json ON cloud_sync_note_intents
WHEN EXISTS (
    SELECT 1 FROM cloud_sync_note_resolution_dependencies AS dependency
    JOIN cloud_sync_note_resolution_outbox AS resolution
      ON resolution.resolution_event_id = dependency.resolution_event_id
    WHERE dependency.parent_event_id = OLD.event_id
      AND dependency.source = 'local_unsealed'
      AND resolution.lifecycle = 'local_pending'
)
BEGIN SELECT RAISE(ABORT, 'note_resolution_parent_is_frozen'); END;

CREATE TRIGGER cloud_sync_note_resolution_freeze_parent_delete
BEFORE DELETE ON cloud_sync_note_intents
WHEN EXISTS (
    SELECT 1 FROM cloud_sync_note_resolution_dependencies AS dependency
    JOIN cloud_sync_note_resolution_outbox AS resolution
      ON resolution.resolution_event_id = dependency.resolution_event_id
    WHERE dependency.parent_event_id = OLD.event_id
      AND dependency.source = 'local_unsealed'
      AND resolution.lifecycle = 'local_pending'
)
AND NOT EXISTS (
    SELECT 1 FROM cloud_sync_event_objects AS object WHERE object.event_id = OLD.event_id
)
BEGIN SELECT RAISE(ABORT, 'note_resolution_parent_cannot_be_removed_unsealed'); END;

-- Until protocol v2 is integrated, neither the resolved Note nor a keep_both
-- clone may silently start a protocol-v1 chain.
CREATE TRIGGER cloud_sync_note_resolution_block_v1_intent
AFTER INSERT ON cloud_sync_note_intents
WHEN EXISTS (
    SELECT 1 FROM cloud_sync_outbox AS event
    JOIN cloud_sync_note_resolution_outbox AS resolution
      ON resolution.account_id = event.account_id
     AND resolution.project_id = event.project_id
     AND (resolution.entity_id = event.entity_id
          OR resolution.clone_entity_id = event.entity_id)
    WHERE event.event_id = NEW.event_id
      AND resolution.lifecycle = 'local_pending'
)
BEGIN SELECT RAISE(ABORT, 'note_resolution_requires_protocol_v2'); END;
