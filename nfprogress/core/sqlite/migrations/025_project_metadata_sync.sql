-- C18.2 is dormant storage. No trigger captures or publishes project edits.
-- Existing generic outbox, encrypted objects, receipts and inbox keep their
-- immutable event/object identities; these tables hold metadata-only proofs.
CREATE UNIQUE INDEX idx_cloud_sync_project_bindings_scope
    ON cloud_sync_project_bindings(project_id, account_id);
CREATE TABLE cloud_sync_metadata_candidates (
    candidate_id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id) ON DELETE RESTRICT,
    project_id TEXT NOT NULL REFERENCES cloud_sync_project_bindings(project_id) ON DELETE RESTRICT,
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    bootstrap_id TEXT CHECK (bootstrap_id IS NULL OR length(bootstrap_id) = 36),
    generation INTEGER NOT NULL CHECK (generation BETWEEN 1 AND 9007199254740991),
    codec_version INTEGER NOT NULL CHECK (codec_version = 1),
    snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json) AND json_type(snapshot_json) = 'object'),
    unsupported_json TEXT NOT NULL CHECK (json_valid(unsupported_json) AND json_type(unsupported_json) = 'array'),
    source_payload_json TEXT NOT NULL CHECK (json_valid(source_payload_json) AND json_type(source_payload_json) = 'object'),
    source_updated_at TEXT,
    state TEXT NOT NULL CHECK (state IN ('candidate', 'publishing', 'published', 'conflict', 'resolved')),
    created_at TEXT NOT NULL,
    UNIQUE (account_id, project_id, device_id, generation),
    FOREIGN KEY (project_id, account_id) REFERENCES cloud_sync_project_bindings(project_id, account_id)
);
CREATE INDEX idx_cloud_sync_metadata_candidates_scope
    ON cloud_sync_metadata_candidates(account_id, project_id, generation);
CREATE TRIGGER cloud_sync_metadata_candidate_immutable_update
BEFORE UPDATE ON cloud_sync_metadata_candidates
WHEN NEW.candidate_id IS NOT OLD.candidate_id OR NEW.account_id IS NOT OLD.account_id
 OR NEW.project_id IS NOT OLD.project_id OR NEW.device_id IS NOT OLD.device_id
 OR NEW.bootstrap_id IS NOT OLD.bootstrap_id OR NEW.generation IS NOT OLD.generation
 OR NEW.codec_version IS NOT OLD.codec_version OR NEW.snapshot_json IS NOT OLD.snapshot_json
 OR NEW.unsupported_json IS NOT OLD.unsupported_json OR NEW.source_payload_json IS NOT OLD.source_payload_json
 OR NEW.source_updated_at IS NOT OLD.source_updated_at OR NEW.created_at IS NOT OLD.created_at
BEGIN SELECT RAISE(ABORT, 'metadata_candidate_snapshot_is_immutable'); END;
CREATE TRIGGER cloud_sync_metadata_candidate_immutable_delete
BEFORE DELETE ON cloud_sync_metadata_candidates
BEGIN SELECT RAISE(ABORT, 'metadata_candidate_is_immutable'); END;

CREATE TABLE cloud_sync_metadata_events (
    account_id TEXT NOT NULL REFERENCES cloud_sync_state(account_id) ON DELETE RESTRICT,
    event_id TEXT NOT NULL CHECK (length(event_id) = 36),
    project_id TEXT NOT NULL REFERENCES cloud_sync_project_bindings(project_id) ON DELETE RESTRICT,
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    bootstrap_id TEXT NOT NULL CHECK (length(bootstrap_id) = 36),
    candidate_id TEXT REFERENCES cloud_sync_metadata_candidates(candidate_id) ON DELETE RESTRICT,
    parent_event_ids_json TEXT NOT NULL CHECK (json_valid(parent_event_ids_json) AND json_type(parent_event_ids_json) = 'array' AND json_array_length(parent_event_ids_json) <= 64),
    generation INTEGER NOT NULL CHECK (generation BETWEEN 1 AND 9007199254740991),
    revision INTEGER NOT NULL CHECK (revision BETWEEN 1 AND 9007199254740991),
    operation TEXT NOT NULL CHECK (operation IN ('create', 'update', 'delete', 'genesis_resolution', 'resolution')),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json) AND json_type(payload_json) = 'object'),
    deleted_at TEXT,
    state TEXT NOT NULL CHECK (state IN ('unsealed', 'sealed', 'accepted', 'received', 'orphan', 'applied', 'conflict_preserved', 'rejected')),
    server_sequence INTEGER CHECK (server_sequence IS NULL OR server_sequence >= 1),
    created_at TEXT NOT NULL,
    PRIMARY KEY (account_id, event_id),
    UNIQUE (event_id),
    UNIQUE (account_id, server_sequence),
    FOREIGN KEY (project_id, account_id) REFERENCES cloud_sync_project_bindings(project_id, account_id),
    CHECK ((operation = 'delete') = (deleted_at IS NOT NULL)),
    CHECK (operation != 'create' OR (revision = 1 AND generation = 1 AND json_array_length(parent_event_ids_json) = 0)),
    CHECK (operation != 'genesis_resolution' OR (revision >= 2 AND json_array_length(parent_event_ids_json) BETWEEN 2 AND 64)),
    CHECK (operation NOT IN ('update', 'delete') OR json_array_length(parent_event_ids_json) = 1),
    CHECK (operation != 'resolution' OR json_array_length(parent_event_ids_json) BETWEEN 2 AND 64)
);
CREATE INDEX idx_cloud_sync_metadata_events_scope
    ON cloud_sync_metadata_events(account_id, project_id, generation, event_id);
CREATE TRIGGER cloud_sync_metadata_event_immutable_update
BEFORE UPDATE ON cloud_sync_metadata_events
WHEN NEW.account_id IS NOT OLD.account_id OR NEW.event_id IS NOT OLD.event_id
 OR NEW.project_id IS NOT OLD.project_id OR NEW.device_id IS NOT OLD.device_id
 OR NEW.bootstrap_id IS NOT OLD.bootstrap_id OR NEW.candidate_id IS NOT OLD.candidate_id
 OR NEW.parent_event_ids_json IS NOT OLD.parent_event_ids_json
 OR NEW.generation IS NOT OLD.generation OR NEW.revision IS NOT OLD.revision
 OR NEW.operation IS NOT OLD.operation OR NEW.payload_json IS NOT OLD.payload_json
 OR NEW.deleted_at IS NOT OLD.deleted_at OR NEW.created_at IS NOT OLD.created_at
BEGIN SELECT RAISE(ABORT, 'metadata_event_identity_is_immutable'); END;
CREATE TRIGGER cloud_sync_metadata_event_immutable_delete
BEFORE DELETE ON cloud_sync_metadata_events
BEGIN SELECT RAISE(ABORT, 'metadata_event_is_immutable'); END;
CREATE TRIGGER cloud_sync_metadata_outbox_identity_immutable
BEFORE UPDATE ON cloud_sync_outbox
WHEN OLD.entity_type='project_metadata' AND (
 NEW.event_id IS NOT OLD.event_id OR NEW.account_id IS NOT OLD.account_id
 OR NEW.device_id IS NOT OLD.device_id OR NEW.project_id IS NOT OLD.project_id
 OR NEW.entity_id IS NOT OLD.entity_id OR NEW.entity_type IS NOT OLD.entity_type
 OR NEW.operation IS NOT OLD.operation OR NEW.revision IS NOT OLD.revision
 OR NEW.updated_at IS NOT OLD.updated_at OR NEW.deleted_at IS NOT OLD.deleted_at
 OR NEW.parent_event_id IS NOT OLD.parent_event_id OR NEW.local_ordinal IS NOT OLD.local_ordinal
)
BEGIN SELECT RAISE(ABORT, 'metadata_outbox_identity_is_immutable'); END;
CREATE TRIGGER cloud_sync_metadata_object_immutable_update
BEFORE UPDATE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_sync_metadata_events e WHERE e.account_id=OLD.account_id AND e.event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT, 'metadata_encrypted_object_is_immutable'); END;
CREATE TRIGGER cloud_sync_metadata_object_immutable_delete
BEFORE DELETE ON cloud_sync_event_objects
WHEN EXISTS(SELECT 1 FROM cloud_sync_metadata_events e WHERE e.account_id=OLD.account_id AND e.event_id=OLD.event_id)
BEGIN SELECT RAISE(ABORT, 'metadata_encrypted_object_is_immutable'); END;

CREATE TABLE cloud_sync_metadata_tips (
    account_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    PRIMARY KEY (account_id, project_id, event_id),
    FOREIGN KEY (account_id, event_id) REFERENCES cloud_sync_metadata_events(account_id, event_id) ON DELETE RESTRICT
);
-- A dormant authenticated projection; C18.3 decides when to expose it to the
-- visible projects row. Conflicts never overwrite this projection.
CREATE TABLE cloud_sync_metadata_projection (
    account_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    head_event_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json) AND json_type(payload_json) = 'object'),
    deleted_at TEXT,
    PRIMARY KEY (account_id, project_id),
    FOREIGN KEY (account_id, head_event_id) REFERENCES cloud_sync_metadata_events(account_id, event_id) ON DELETE RESTRICT
);
CREATE TABLE cloud_sync_metadata_apply_ledger (
    account_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('applied', 'conflict_preserved')),
    canonical_payload BLOB NOT NULL CHECK (typeof(canonical_payload) = 'blob' AND length(canonical_payload) BETWEEN 1 AND 1048576),
    applied_at TEXT NOT NULL,
    PRIMARY KEY (account_id, event_id),
    FOREIGN KEY (account_id, event_id) REFERENCES cloud_sync_metadata_events(account_id, event_id) ON DELETE RESTRICT
);
