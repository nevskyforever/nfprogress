-- C17 D2B0A: durable proof for an applied multi-parent resolution. Sender
-- conflict identity is authenticated but device-scoped; the local group and
-- generation are an independent CAS proof.

DROP TRIGGER cloud_sync_upload_receipts_resolution_sequence_conflict;
DROP TRIGGER cloud_sync_note_resolution_receipts_v1_sequence_conflict;
DROP TRIGGER cloud_sync_note_resolution_receipt_requires_sealed_object;
DROP TRIGGER cloud_sync_note_resolution_outbox_accepted_requires_receipt;

ALTER TABLE cloud_sync_note_resolution_upload_receipts
    RENAME TO cloud_sync_note_resolution_upload_receipts_v22;

CREATE TABLE cloud_sync_note_resolution_upload_receipts (
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    resolution_event_id TEXT PRIMARY KEY NOT NULL
        REFERENCES cloud_sync_note_resolution_outbox(resolution_event_id) ON DELETE RESTRICT,
    device_id TEXT NOT NULL CHECK (length(device_id) = 36),
    server_sequence INTEGER NOT NULL CHECK (
        server_sequence BETWEEN 1 AND 9007199254740991
    ),
    duplicate INTEGER CHECK (duplicate IS NULL OR duplicate IN (0, 1)),
    acceptance_source TEXT NOT NULL DEFAULT 'push_response' CHECK (
        acceptance_source IN ('push_response', 'pull_self_echo')
    ),
    accepted_at TEXT NOT NULL,
    UNIQUE (account_id, server_sequence),
    CHECK (
        (acceptance_source = 'push_response' AND duplicate IN (0, 1))
        OR (acceptance_source = 'pull_self_echo' AND duplicate IS NULL)
    )
);

INSERT INTO cloud_sync_note_resolution_upload_receipts(
    account_id,resolution_event_id,device_id,server_sequence,duplicate,
    acceptance_source,accepted_at
)
SELECT account_id,resolution_event_id,device_id,server_sequence,duplicate,
       'push_response',accepted_at
FROM cloud_sync_note_resolution_upload_receipts_v22;

DROP TABLE cloud_sync_note_resolution_upload_receipts_v22;

CREATE INDEX idx_cloud_sync_note_resolution_upload_receipts_account
    ON cloud_sync_note_resolution_upload_receipts(account_id, resolution_event_id);

CREATE TRIGGER cloud_sync_upload_receipts_resolution_sequence_conflict
BEFORE INSERT ON cloud_sync_upload_receipts
WHEN EXISTS(
    SELECT 1 FROM cloud_sync_note_resolution_upload_receipts AS resolution
    WHERE resolution.account_id = NEW.account_id
      AND resolution.server_sequence = NEW.server_sequence
)
BEGIN SELECT RAISE(ABORT, 'note_sync_receipt_sequence_conflict'); END;

CREATE TRIGGER cloud_sync_note_resolution_receipts_v1_sequence_conflict
BEFORE INSERT ON cloud_sync_note_resolution_upload_receipts
WHEN EXISTS(
    SELECT 1 FROM cloud_sync_upload_receipts AS receipt
    WHERE receipt.account_id = NEW.account_id
      AND receipt.server_sequence = NEW.server_sequence
)
BEGIN SELECT RAISE(ABORT, 'note_sync_receipt_sequence_conflict'); END;

CREATE TRIGGER cloud_sync_note_resolution_receipt_requires_sealed_object
BEFORE INSERT ON cloud_sync_note_resolution_upload_receipts
WHEN NOT EXISTS(
    SELECT 1
    FROM cloud_sync_note_resolution_outbox AS resolution
    JOIN cloud_sync_event_objects AS object
      ON object.account_id = resolution.account_id
     AND object.event_id = resolution.resolution_event_id
    WHERE resolution.resolution_event_id = NEW.resolution_event_id
      AND resolution.account_id = NEW.account_id
      AND resolution.device_id = NEW.device_id
      AND resolution.lifecycle = 'sealed_local'
)
BEGIN SELECT RAISE(ABORT, 'note_resolution_receipt_requires_sealed_object'); END;

CREATE TRIGGER cloud_sync_note_resolution_outbox_accepted_requires_receipt
AFTER UPDATE OF lifecycle ON cloud_sync_note_resolution_outbox
WHEN NEW.lifecycle = 'accepted' AND NOT EXISTS(
    SELECT 1 FROM cloud_sync_note_resolution_upload_receipts AS receipt
    WHERE receipt.account_id = NEW.account_id
      AND receipt.resolution_event_id = NEW.resolution_event_id
      AND receipt.device_id = NEW.device_id
)
BEGIN SELECT RAISE(ABORT, 'note_resolution_accepted_receipt_missing'); END;

CREATE TRIGGER cloud_sync_note_resolution_receipt_immutable_update
BEFORE UPDATE ON cloud_sync_note_resolution_upload_receipts
BEGIN SELECT RAISE(ABORT, 'note_resolution_receipt_is_immutable'); END;

CREATE TRIGGER cloud_sync_note_resolution_receipt_immutable_delete
BEFORE DELETE ON cloud_sync_note_resolution_upload_receipts
BEGIN SELECT RAISE(ABORT, 'note_resolution_receipt_is_immutable'); END;

CREATE TABLE cloud_sync_note_applied_resolutions (
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    resolution_event_id TEXT NOT NULL CHECK (
        length(resolution_event_id) = 36
        AND length(replace(resolution_event_id, '-', '')) = 32
        AND substr(resolution_event_id, 9, 1) = '-'
        AND substr(resolution_event_id, 14, 1) = '-'
        AND substr(resolution_event_id, 19, 1) = '-'
        AND substr(resolution_event_id, 24, 1) = '-'
        AND resolution_event_id NOT GLOB '*[^0-9a-f-]*'
    ),
    source_device_id TEXT NOT NULL CHECK (
        length(source_device_id) = 36
        AND length(replace(source_device_id, '-', '')) = 32
        AND substr(source_device_id, 9, 1) = '-'
        AND substr(source_device_id, 14, 1) = '-'
        AND substr(source_device_id, 19, 1) = '-'
        AND substr(source_device_id, 24, 1) = '-'
        AND source_device_id NOT GLOB '*[^0-9a-f-]*'
    ),
    server_sequence INTEGER NOT NULL CHECK (
        server_sequence BETWEEN 1 AND 9007199254740991
    ),
    project_id TEXT NOT NULL CHECK (length(project_id) BETWEEN 1 AND 512),
    entity_id TEXT NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 512),
    revision INTEGER NOT NULL CHECK (revision BETWEEN 2 AND 9007199254740991),
    event_updated_at TEXT NOT NULL CHECK (length(event_updated_at) BETWEEN 1 AND 64),
    remote_conflict_group_id TEXT NOT NULL CHECK (
        length(remote_conflict_group_id) = 36
        AND length(replace(remote_conflict_group_id, '-', '')) = 32
        AND substr(remote_conflict_group_id, 9, 1) = '-'
        AND substr(remote_conflict_group_id, 14, 1) = '-'
        AND substr(remote_conflict_group_id, 19, 1) = '-'
        AND substr(remote_conflict_group_id, 24, 1) = '-'
        AND remote_conflict_group_id NOT GLOB '*[^0-9a-f-]*'
    ),
    local_conflict_group_id TEXT NOT NULL
        REFERENCES cloud_sync_note_conflict_groups(group_id) ON DELETE RESTRICT,
    remote_conflict_generation INTEGER NOT NULL CHECK (
        remote_conflict_generation BETWEEN 1 AND 9007199254740991
    ),
    local_conflict_generation INTEGER NOT NULL CHECK (
        local_conflict_generation BETWEEN 1 AND 9007199254740991
    ),
    parent_event_ids_json TEXT NOT NULL CHECK (
        json_valid(parent_event_ids_json)
        AND json_type(parent_event_ids_json) = 'array'
        AND json_array_length(parent_event_ids_json) BETWEEN 2 AND 64
    ),
    parent_count INTEGER NOT NULL CHECK (parent_count BETWEEN 2 AND 64),
    strategy TEXT NOT NULL CHECK (
        strategy IN ('choose_version', 'manual_merge', 'keep_both', 'delete')
    ),
    result_operation TEXT NOT NULL CHECK (result_operation IN ('upsert', 'delete')),
    canonical_payload BLOB NOT NULL CHECK (
        typeof(canonical_payload) = 'blob'
        AND length(canonical_payload) BETWEEN 1 AND 8388608
    ),
    result_snapshot_json TEXT NOT NULL CHECK (
        json_valid(result_snapshot_json) AND json_type(result_snapshot_json) = 'object'
    ),
    clone_entity_id TEXT,
    clone_snapshot_json TEXT CHECK (
        clone_snapshot_json IS NULL
        OR (json_valid(clone_snapshot_json) AND json_type(clone_snapshot_json) = 'object')
    ),
    lifecycle TEXT NOT NULL CHECK (lifecycle IN ('applying', 'applied')),
    applied_at TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (account_id, resolution_event_id),
    UNIQUE (resolution_event_id),
    UNIQUE (account_id, server_sequence),
    FOREIGN KEY (account_id, resolution_event_id)
        REFERENCES cloud_sync_inbox(account_id, event_id) ON DELETE RESTRICT,
    CHECK (parent_count = json_array_length(parent_event_ids_json)),
    CHECK (
        (strategy = 'keep_both'
         AND clone_entity_id IS NOT NULL
         AND length(clone_entity_id) BETWEEN 1 AND 512
         AND clone_entity_id != entity_id
         AND clone_snapshot_json IS NOT NULL)
        OR
        (strategy != 'keep_both'
         AND clone_entity_id IS NULL
         AND clone_snapshot_json IS NULL)
    ),
    CHECK (
        strategy = 'choose_version'
        OR (strategy IN ('manual_merge', 'keep_both') AND result_operation = 'upsert')
        OR (strategy = 'delete' AND result_operation = 'delete')
    ),
    CHECK (
        (lifecycle = 'applying' AND applied_at IS NULL)
        OR (lifecycle = 'applied' AND applied_at IS NOT NULL)
    )
);

CREATE INDEX idx_cloud_sync_note_applied_resolutions_scope
    ON cloud_sync_note_applied_resolutions(account_id, project_id, entity_id, lifecycle);

CREATE TRIGGER cloud_sync_upload_receipts_applied_resolution_sequence_conflict
BEFORE INSERT ON cloud_sync_upload_receipts
WHEN EXISTS(
    SELECT 1 FROM cloud_sync_note_applied_resolutions AS resolution
    WHERE resolution.account_id = NEW.account_id
      AND resolution.server_sequence = NEW.server_sequence
)
BEGIN SELECT RAISE(ABORT, 'note_sync_receipt_sequence_conflict'); END;

CREATE TRIGGER cloud_sync_note_causal_history_applied_resolution_sequence_conflict
BEFORE INSERT ON cloud_sync_note_causal_history
WHEN EXISTS(
    SELECT 1 FROM cloud_sync_note_applied_resolutions AS resolution
    WHERE resolution.account_id = NEW.account_id
      AND resolution.server_sequence = NEW.server_sequence
)
BEGIN SELECT RAISE(ABORT, 'note_sync_causal_sequence_conflict'); END;

CREATE TRIGGER cloud_sync_note_resolution_receipts_applied_sequence_conflict
BEFORE INSERT ON cloud_sync_note_resolution_upload_receipts
WHEN EXISTS(
    SELECT 1 FROM cloud_sync_note_applied_resolutions AS resolution
    WHERE resolution.account_id = NEW.account_id
      AND resolution.server_sequence = NEW.server_sequence
      AND resolution.resolution_event_id != NEW.resolution_event_id
)
BEGIN SELECT RAISE(ABORT, 'note_sync_receipt_sequence_conflict'); END;

CREATE TABLE cloud_sync_note_applied_resolution_parents (
    account_id TEXT NOT NULL CHECK (length(account_id) BETWEEN 1 AND 512),
    resolution_event_id TEXT NOT NULL,
    parent_ordinal INTEGER NOT NULL CHECK (parent_ordinal BETWEEN 0 AND 63),
    parent_event_id TEXT NOT NULL CHECK (
        length(parent_event_id) = 36
        AND length(replace(parent_event_id, '-', '')) = 32
        AND substr(parent_event_id, 9, 1) = '-'
        AND substr(parent_event_id, 14, 1) = '-'
        AND substr(parent_event_id, 19, 1) = '-'
        AND substr(parent_event_id, 24, 1) = '-'
        AND parent_event_id NOT GLOB '*[^0-9a-f-]*'
    ),
    conflict_version_id TEXT NOT NULL
        REFERENCES cloud_sync_note_conflict_versions(version_id) ON DELETE RESTRICT,
    parent_revision INTEGER NOT NULL CHECK (
        parent_revision BETWEEN 1 AND 9007199254740991
    ),
    parent_operation TEXT NOT NULL CHECK (parent_operation IN ('upsert', 'delete')),
    parent_snapshot_json TEXT NOT NULL CHECK (
        json_valid(parent_snapshot_json) AND json_type(parent_snapshot_json) = 'object'
    ),
    publication_source TEXT NOT NULL CHECK (
        publication_source IN ('remote', 'remote_applied', 'local_accepted')
    ),
    server_sequence INTEGER NOT NULL CHECK (
        server_sequence BETWEEN 1 AND 9007199254740991
    ),
    local_mutation_generation INTEGER CHECK (
        local_mutation_generation IS NULL
        OR local_mutation_generation BETWEEN 1 AND 9007199254740991
    ),
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (account_id, resolution_event_id, parent_event_id),
    UNIQUE (account_id, resolution_event_id, parent_ordinal),
    UNIQUE (account_id, resolution_event_id, server_sequence),
    FOREIGN KEY (account_id, resolution_event_id)
        REFERENCES cloud_sync_note_applied_resolutions(account_id, resolution_event_id)
        ON DELETE RESTRICT,
    CHECK (
        (publication_source = 'local_accepted' AND local_mutation_generation IS NOT NULL)
        OR (publication_source != 'local_accepted' AND local_mutation_generation IS NULL)
    )
);

CREATE TRIGGER cloud_sync_note_applied_resolution_insert_guard
BEFORE INSERT ON cloud_sync_note_applied_resolutions
WHEN NEW.lifecycle != 'applying'
  OR NEW.applied_at IS NOT NULL
  OR NOT EXISTS(
      SELECT 1
      FROM cloud_sync_inbox AS inbox
      JOIN cloud_sync_event_objects AS object
        ON object.account_id = inbox.account_id AND object.event_id = inbox.event_id
      WHERE inbox.account_id = NEW.account_id
        AND inbox.event_id = NEW.resolution_event_id
        AND inbox.server_sequence = NEW.server_sequence
        AND inbox.device_id = NEW.source_device_id
        AND inbox.project_id = NEW.project_id
        AND inbox.entity_id = NEW.entity_id
        AND inbox.entity_type = 'note'
        AND inbox.operation = 'resolution'
        AND inbox.sync_revision = NEW.revision
        AND inbox.updated_at = NEW.event_updated_at
        AND inbox.deleted_at IS NULL
        AND inbox.state IN ('received', 'orphan')
  )
  OR NOT EXISTS(
      SELECT 1 FROM cloud_sync_note_conflict_groups AS conflict_group
      WHERE conflict_group.group_id = NEW.local_conflict_group_id
        AND conflict_group.account_id = NEW.account_id
        AND conflict_group.project_id = NEW.project_id
        AND conflict_group.entity_id = NEW.entity_id
        AND conflict_group.entity_type = 'note'
        AND conflict_group.generation = NEW.local_conflict_generation
        AND conflict_group.lifecycle IN ('open', 'resolving')
  )
  OR EXISTS(
      SELECT 1 FROM cloud_sync_note_causal_history AS history
      WHERE history.account_id = NEW.account_id
        AND history.server_sequence = NEW.server_sequence
  )
  OR EXISTS(
      SELECT 1 FROM cloud_sync_upload_receipts AS receipt
      WHERE receipt.account_id = NEW.account_id
        AND receipt.server_sequence = NEW.server_sequence
  )
  OR EXISTS(
      SELECT 1 FROM cloud_sync_note_resolution_upload_receipts AS receipt
      WHERE receipt.account_id = NEW.account_id
        AND receipt.resolution_event_id = NEW.resolution_event_id
        AND receipt.server_sequence != NEW.server_sequence
  )
  OR EXISTS(
      SELECT 1 FROM cloud_sync_note_resolution_upload_receipts AS receipt
      WHERE receipt.account_id = NEW.account_id
        AND receipt.server_sequence = NEW.server_sequence
        AND receipt.resolution_event_id != NEW.resolution_event_id
  )
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_proof_invalid'); END;

CREATE TRIGGER cloud_sync_note_applied_resolution_parent_set_guard
BEFORE INSERT ON cloud_sync_note_applied_resolutions
WHEN EXISTS(
    SELECT 1 FROM json_each(NEW.parent_event_ids_json) AS parent
    WHERE parent.type != 'text'
       OR length(parent.value) != 36
       OR length(replace(parent.value, '-', '')) != 32
       OR substr(parent.value, 9, 1) != '-'
       OR substr(parent.value, 14, 1) != '-'
       OR substr(parent.value, 19, 1) != '-'
       OR substr(parent.value, 24, 1) != '-'
       OR parent.value GLOB '*[^0-9a-f-]*'
       OR parent.value = NEW.resolution_event_id
       OR (CAST(parent.key AS INTEGER) > 0 AND
           json_extract(
               NEW.parent_event_ids_json,
               '$[' || (CAST(parent.key AS INTEGER) - 1) || ']'
           ) >= parent.value)
)
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_parent_set_invalid'); END;

CREATE TRIGGER cloud_sync_note_applied_resolution_immutable_update
BEFORE UPDATE ON cloud_sync_note_applied_resolutions
WHEN NEW.account_id != OLD.account_id
  OR NEW.resolution_event_id != OLD.resolution_event_id
  OR NEW.source_device_id != OLD.source_device_id
  OR NEW.server_sequence != OLD.server_sequence
  OR NEW.project_id != OLD.project_id
  OR NEW.entity_id != OLD.entity_id
  OR NEW.revision != OLD.revision
  OR NEW.event_updated_at != OLD.event_updated_at
  OR NEW.remote_conflict_group_id != OLD.remote_conflict_group_id
  OR NEW.local_conflict_group_id != OLD.local_conflict_group_id
  OR NEW.remote_conflict_generation != OLD.remote_conflict_generation
  OR NEW.local_conflict_generation != OLD.local_conflict_generation
  OR NEW.parent_event_ids_json != OLD.parent_event_ids_json
  OR NEW.parent_count != OLD.parent_count
  OR NEW.strategy != OLD.strategy
  OR NEW.result_operation != OLD.result_operation
  OR NEW.canonical_payload != OLD.canonical_payload
  OR NEW.result_snapshot_json != OLD.result_snapshot_json
  OR NEW.clone_entity_id IS NOT OLD.clone_entity_id
  OR NEW.clone_snapshot_json IS NOT OLD.clone_snapshot_json
  OR NEW.created_at != OLD.created_at
  OR OLD.lifecycle != 'applying'
  OR NEW.lifecycle != 'applied'
  OR OLD.applied_at IS NOT NULL
  OR NEW.applied_at IS NULL
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_is_immutable'); END;

CREATE TRIGGER cloud_sync_note_applied_resolution_completion_guard
BEFORE UPDATE OF lifecycle ON cloud_sync_note_applied_resolutions
WHEN NEW.lifecycle = 'applied' AND (
    NOT EXISTS(
        SELECT 1 FROM cloud_sync_note_conflict_groups AS conflict_group
        WHERE conflict_group.group_id = NEW.local_conflict_group_id
          AND conflict_group.account_id = NEW.account_id
          AND conflict_group.project_id = NEW.project_id
          AND conflict_group.entity_id = NEW.entity_id
          AND conflict_group.entity_type = 'note'
          AND conflict_group.generation = NEW.local_conflict_generation
          AND conflict_group.lifecycle IN ('open', 'resolving')
    )
    OR NEW.revision != (
        SELECT max(parent.parent_revision) + 1
        FROM cloud_sync_note_applied_resolution_parents AS parent
        WHERE parent.account_id = NEW.account_id
          AND parent.resolution_event_id = NEW.resolution_event_id
    )
    OR
    (SELECT count(*)
     FROM cloud_sync_note_applied_resolution_parents AS parent
     WHERE parent.account_id = NEW.account_id
       AND parent.resolution_event_id = NEW.resolution_event_id) != NEW.parent_count
    OR EXISTS(
        SELECT 1 FROM json_each(NEW.parent_event_ids_json) AS expected
        LEFT JOIN cloud_sync_note_applied_resolution_parents AS parent
          ON parent.account_id = NEW.account_id
         AND parent.resolution_event_id = NEW.resolution_event_id
         AND parent.parent_ordinal = CAST(expected.key AS INTEGER)
         AND parent.parent_event_id = expected.value
        WHERE parent.parent_event_id IS NULL
    )
    OR (SELECT count(*)
        FROM cloud_sync_note_conflict_tips AS tip
        WHERE tip.group_id = NEW.local_conflict_group_id
          AND tip.generation = NEW.local_conflict_generation) != NEW.parent_count
    OR EXISTS(
        SELECT 1 FROM json_each(NEW.parent_event_ids_json) AS expected
        LEFT JOIN cloud_sync_note_applied_resolution_parents AS parent
          ON parent.account_id = NEW.account_id
         AND parent.resolution_event_id = NEW.resolution_event_id
         AND parent.parent_ordinal = CAST(expected.key AS INTEGER)
         AND parent.parent_event_id = expected.value
        LEFT JOIN cloud_sync_note_conflict_tips AS tip
          ON tip.group_id = NEW.local_conflict_group_id
         AND tip.generation = NEW.local_conflict_generation
         AND tip.event_id = expected.value
         AND tip.version_id = parent.conflict_version_id
        WHERE parent.parent_event_id IS NULL OR tip.event_id IS NULL
    )
)
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_parent_proof_incomplete'); END;

CREATE TRIGGER cloud_sync_note_applied_resolution_immutable_delete
BEFORE DELETE ON cloud_sync_note_applied_resolutions
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_is_immutable'); END;

CREATE TRIGGER cloud_sync_note_applied_resolution_parent_insert_guard
BEFORE INSERT ON cloud_sync_note_applied_resolution_parents
WHEN NOT EXISTS(
    SELECT 1
    FROM cloud_sync_note_applied_resolutions AS resolution
    JOIN cloud_sync_note_conflict_versions AS version
      ON version.version_id = NEW.conflict_version_id
     AND version.group_id = resolution.local_conflict_group_id
     AND version.account_id = resolution.account_id
     AND version.project_id = resolution.project_id
     AND version.entity_id = resolution.entity_id
     AND version.entity_type = 'note'
     AND version.event_id = NEW.parent_event_id
     AND version.revision = NEW.parent_revision
     AND version.operation = NEW.parent_operation
     AND version.snapshot_json = NEW.parent_snapshot_json
     AND version.conflict_generation = resolution.local_conflict_generation
     AND version.parent_event_id = (
         SELECT conflict_group.common_parent_event_id
         FROM cloud_sync_note_conflict_groups AS conflict_group
         WHERE conflict_group.group_id = resolution.local_conflict_group_id
     )
    WHERE resolution.account_id = NEW.account_id
      AND resolution.resolution_event_id = NEW.resolution_event_id
      AND resolution.lifecycle = 'applying'
      AND NEW.parent_ordinal < resolution.parent_count
      AND (
          (NEW.publication_source = 'remote'
           AND version.source = 'remote'
           AND version.server_sequence = NEW.server_sequence
           AND EXISTS(
               SELECT 1 FROM cloud_sync_inbox AS inbox
               WHERE inbox.account_id = NEW.account_id
                 AND inbox.event_id = NEW.parent_event_id
                 AND inbox.server_sequence = NEW.server_sequence
                 AND inbox.project_id = resolution.project_id
                 AND inbox.entity_id = resolution.entity_id
                 AND inbox.entity_type = 'note'
                 AND inbox.operation = NEW.parent_operation
                 AND inbox.sync_revision = NEW.parent_revision
                 AND inbox.state = 'conflict_preserved'
                 AND inbox.conflict_group_id = resolution.local_conflict_group_id
           ))
          OR
          (NEW.publication_source = 'remote_applied'
           AND version.source = 'remote_applied'
           AND version.server_sequence = NEW.server_sequence
           AND EXISTS(
               SELECT 1 FROM cloud_sync_note_causal_history AS history
               WHERE history.account_id = NEW.account_id
                 AND history.event_id = NEW.parent_event_id
                 AND history.server_sequence = NEW.server_sequence
                 AND history.project_id = resolution.project_id
                 AND history.entity_id = resolution.entity_id
                 AND history.entity_type = 'note'
                 AND history.revision = NEW.parent_revision
                 AND history.operation = NEW.parent_operation
                 AND history.snapshot_json = NEW.parent_snapshot_json
           ))
          OR
          (NEW.publication_source = 'local_accepted'
           AND version.source = 'local_unsealed'
           AND version.local_mutation_generation = NEW.local_mutation_generation
           AND EXISTS(
               SELECT 1
               FROM cloud_sync_outbox AS outbox
               JOIN cloud_sync_upload_receipts AS receipt
                 ON receipt.account_id = outbox.account_id
                AND receipt.event_id = outbox.event_id
               WHERE outbox.account_id = NEW.account_id
                 AND outbox.event_id = NEW.parent_event_id
                 AND outbox.project_id = resolution.project_id
                 AND outbox.entity_id = resolution.entity_id
                 AND outbox.entity_type = 'note'
                 AND outbox.operation = NEW.parent_operation
                 AND outbox.revision = NEW.parent_revision
                 AND outbox.lifecycle = 'accepted'
                 AND receipt.device_id = outbox.device_id
                 AND receipt.server_sequence = NEW.server_sequence
           ))
      )
)
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_parent_proof_invalid'); END;

CREATE TRIGGER cloud_sync_note_applied_resolution_parent_immutable_update
BEFORE UPDATE ON cloud_sync_note_applied_resolution_parents
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_parent_is_immutable'); END;

CREATE TRIGGER cloud_sync_note_applied_resolution_parent_immutable_delete
BEFORE DELETE ON cloud_sync_note_applied_resolution_parents
BEGIN SELECT RAISE(ABORT, 'note_applied_resolution_parent_is_immutable'); END;

CREATE TRIGGER cloud_sync_resolution_inbox_applied_insert_guard
BEFORE INSERT ON cloud_sync_inbox
WHEN NEW.operation = 'resolution' AND NEW.state = 'applied'
BEGIN SELECT RAISE(ABORT, 'resolution_inbox_applied_proof_missing'); END;

CREATE TRIGGER cloud_sync_resolution_inbox_applied_update_guard
BEFORE UPDATE OF state ON cloud_sync_inbox
WHEN NEW.operation = 'resolution' AND NEW.state = 'applied' AND OLD.state != 'applied'
 AND NOT EXISTS(
     SELECT 1 FROM cloud_sync_note_applied_resolutions AS resolution
     WHERE resolution.account_id = NEW.account_id
       AND resolution.resolution_event_id = NEW.event_id
       AND resolution.source_device_id = NEW.device_id
       AND resolution.server_sequence = NEW.server_sequence
       AND resolution.project_id = NEW.project_id
       AND resolution.entity_id = NEW.entity_id
       AND resolution.revision = NEW.sync_revision
       AND resolution.event_updated_at = NEW.updated_at
       AND resolution.lifecycle = 'applied'
       AND resolution.applied_at = NEW.applied_at
 )
BEGIN SELECT RAISE(ABORT, 'resolution_inbox_applied_proof_missing'); END;

CREATE TRIGGER cloud_sync_resolution_inbox_applied_is_final
BEFORE UPDATE OF state ON cloud_sync_inbox
WHEN OLD.operation = 'resolution' AND OLD.state = 'applied' AND NEW.state != 'applied'
BEGIN SELECT RAISE(ABORT, 'resolution_inbox_applied_is_final'); END;

DROP TRIGGER cloud_sync_note_resolution_block_v1_intent;
CREATE TRIGGER cloud_sync_note_resolution_block_v1_intent
AFTER INSERT ON cloud_sync_note_intents
WHEN EXISTS(
    SELECT 1
    FROM cloud_sync_outbox AS event
    JOIN cloud_sync_note_resolution_outbox AS resolution
      ON resolution.account_id = event.account_id
     AND resolution.project_id = event.project_id
     AND (resolution.entity_id = event.entity_id OR resolution.clone_entity_id = event.entity_id)
    WHERE event.event_id = NEW.event_id
      AND (
          resolution.lifecycle IN ('local_pending', 'sealed_local')
          OR (
              resolution.lifecycle = 'accepted'
              AND NOT EXISTS(
                  SELECT 1 FROM cloud_sync_note_applied_resolutions AS applied
                  WHERE applied.account_id = resolution.account_id
                    AND applied.resolution_event_id = resolution.resolution_event_id
                    AND applied.source_device_id = resolution.device_id
                    AND applied.project_id = resolution.project_id
                    AND applied.entity_id = resolution.entity_id
                    AND applied.revision = resolution.revision
                    AND applied.remote_conflict_group_id = resolution.conflict_group_id
                    AND applied.local_conflict_group_id = resolution.conflict_group_id
                    AND applied.remote_conflict_generation = resolution.conflict_generation
                    AND applied.local_conflict_generation = resolution.conflict_generation
                    AND applied.parent_event_ids_json = resolution.parent_event_ids_json
                    AND applied.strategy = resolution.strategy
                    AND applied.result_operation = resolution.result_operation
                    AND applied.canonical_payload = resolution.canonical_payload
                    AND applied.clone_entity_id IS resolution.clone_entity_id
                    AND applied.lifecycle = 'applied'
                    AND EXISTS(
                        SELECT 1
                        FROM cloud_sync_note_resolution_upload_receipts AS receipt
                        WHERE receipt.account_id = resolution.account_id
                          AND receipt.resolution_event_id = resolution.resolution_event_id
                          AND receipt.device_id = resolution.device_id
                          AND receipt.server_sequence = applied.server_sequence
                    )
              )
          )
      )
)
BEGIN SELECT RAISE(ABORT, 'note_resolution_requires_protocol_v2'); END;
