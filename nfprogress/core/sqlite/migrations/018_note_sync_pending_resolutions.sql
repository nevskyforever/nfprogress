-- C17 Pass 2C: locally prepared Note conflict resolutions. These canonical
-- plaintext bytes are never part of the protocol-v1 outbox or sealing queue.
CREATE TABLE cloud_sync_note_pending_resolutions (
    resolution_event_id TEXT PRIMARY KEY NOT NULL CHECK (
        length(resolution_event_id) = 36
        AND length(replace(resolution_event_id, '-', '')) = 32
        AND substr(resolution_event_id, 9, 1) = '-'
        AND substr(resolution_event_id, 14, 1) = '-'
        AND substr(resolution_event_id, 19, 1) = '-'
        AND substr(resolution_event_id, 24, 1) = '-'
        AND resolution_event_id NOT GLOB '*[^0-9a-f-]*'
    ),
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    conflict_group_id TEXT NOT NULL
        REFERENCES cloud_sync_note_conflict_groups(group_id) ON DELETE RESTRICT,
    expected_conflict_generation INTEGER NOT NULL CHECK (expected_conflict_generation >= 1),
    resolution_revision INTEGER NOT NULL CHECK (resolution_revision >= 2),
    tip_event_ids_json TEXT NOT NULL CHECK (
        json_valid(tip_event_ids_json) AND json_type(tip_event_ids_json) = 'array'
        AND json_array_length(tip_event_ids_json) BETWEEN 2 AND 64
    ),
    strategy TEXT NOT NULL CHECK (
        strategy IN ('choose_version', 'manual_merge', 'keep_both', 'delete')
    ),
    result_operation TEXT NOT NULL CHECK (result_operation IN ('upsert', 'delete')),
    canonical_payload BLOB NOT NULL CHECK (length(canonical_payload) BETWEEN 1 AND 8388608),
    lifecycle TEXT NOT NULL CHECK (lifecycle IN ('prepared', 'consumed', 'superseded')),
    prepared_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_cloud_sync_note_pending_resolutions_active_group
    ON cloud_sync_note_pending_resolutions(conflict_group_id)
    WHERE lifecycle = 'prepared';
CREATE INDEX idx_cloud_sync_note_pending_resolutions_scope
    ON cloud_sync_note_pending_resolutions(account_id, project_id, entity_id, lifecycle);

-- Identity and proof bytes never change. A later pass may only advance the
-- lifecycle after revalidating the group in its own protected transaction.
CREATE TRIGGER cloud_sync_note_pending_resolutions_identity_immutable
BEFORE UPDATE ON cloud_sync_note_pending_resolutions
WHEN NEW.resolution_event_id != OLD.resolution_event_id
  OR NEW.account_id != OLD.account_id
  OR NEW.device_id != OLD.device_id
  OR NEW.project_id != OLD.project_id
  OR NEW.entity_id != OLD.entity_id
  OR NEW.conflict_group_id != OLD.conflict_group_id
  OR NEW.expected_conflict_generation != OLD.expected_conflict_generation
  OR NEW.resolution_revision != OLD.resolution_revision
  OR NEW.tip_event_ids_json != OLD.tip_event_ids_json
  OR NEW.strategy != OLD.strategy
  OR NEW.result_operation != OLD.result_operation
  OR NEW.canonical_payload != OLD.canonical_payload
  OR NEW.prepared_at != OLD.prepared_at
BEGIN SELECT RAISE(ABORT, 'note_pending_resolution_identity_is_immutable'); END;

CREATE TRIGGER cloud_sync_note_pending_resolutions_no_delete
BEFORE DELETE ON cloud_sync_note_pending_resolutions
BEGIN SELECT RAISE(ABORT, 'note_pending_resolution_cannot_be_deleted'); END;
